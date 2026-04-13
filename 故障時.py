import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import qrcode
from io import BytesIO
import google.generativeai as genai  
from PIL import Image                
import json                          
import re                            

# ページ設定
st.set_page_config(page_title="医療機器連携システム", layout="centered")

# ==========================================
# 💡 URLパラメータの取得（モード判定）
# ==========================================
query_params = st.query_params
url_me_no = query_params.get("me_no", "")
app_mode = query_params.get("mode", "admin") 

categories_list = ["輸液ポンプ", "シリンジポンプ", "保育器", "分娩監視装置", "人工呼吸器", "その他"]

# ==========================================
# 🔐 セキュリティ：パスワード認証ブロック
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"] 
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.warning("⚠️ このシステムはmiratechの専用システムです。")
        st.text_input("🔑 パスワードを入力してください", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 パスワードを入力してください", type="password", on_change=password_entered, key="password")
        st.error("❌ パスワードが違います。")
        return False
    return True

if app_mode != "nurse":
    if not check_password():
        st.stop()

# ==========================================
# 🤖 AI設定（Gemini）
# ==========================================
ai_model = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        ai_model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"APIキーの設定エラー: {e}")

# ==========================================
# 👩‍⚕️ 【ルートA】現場スタッフ（看護師・オペ室）専用モード
# ==========================================
if app_mode == "nurse":
    st.markdown("<h2 style='text-align: center; color: #FF4B4B;'>🚨 機器トラブル報告システム</h2>", unsafe_allow_html=True)
    st.write("不具合を見つけた場合は、以下のフォームから直ちにご報告ください。")
    
    if url_me_no:
        st.success(f"📱 読み込み成功: 対象機器 **{url_me_no}**")
        
        device_name = "不明な機器"
        vendor_name = ""
        vendor_phone = ""
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            # ✨ 「1117.0」問題の修正：URLの文字を綺麗にする
            clean_url_me = str(url_me_no).strip()

            for cat in categories_list:
                try:
                    df_cat = conn.read(worksheet=cat, ttl=0).dropna(how="all")
                    if "ME No." in df_cat.columns:
                        # ✨ 「1117.0」問題の修正：データ側の「.0」を強制削除して比較！
                        clean_db_me = df_cat["ME No."].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                        df_device = df_cat[clean_db_me == clean_url_me]
                        
                        if not df_device.empty:
                            latest_data = df_device.iloc[-1]
                            device_name = str(latest_data.get('機種', '-')).strip()
                            vendor_name = str(latest_data.get('購入元', '')).strip()
                            
                            # 電話番号の「nan」空データ対策
                            v_phone = str(latest_data.get('業者電話番号', '')).strip()
                            vendor_phone = "" if v_phone.lower() == "nan" else v_phone
                            break
                except Exception:
                    continue
        except Exception:
            pass

        with st.form("nurse_report_form"):
            st.info(f"対象機器: {url_me_no} ({device_name})")
            rep_date = st.date_input("発生日", date.today())
            rep_dept = st.selectbox("あなたの部署", ["選択してください", "外来", "一般病棟", "療養病棟", "オペ室", "透析室", "その他"])
            rep_name = st.text_input("報告者名", placeholder="例: 琉球 花子")
            
            st.write("▼ 症状・エラー内容（該当するものをタップ）")
            col_err1, col_err2 = st.columns(2)
            with col_err1:
                err_power = st.checkbox("🔌 電源が入らない")
                err_error = st.checkbox("⚠️ エラー表示が出る")
                err_batt  = st.checkbox("🔋 バッテリー劣化")
            with col_err2:
                err_alarm = st.checkbox("🔔 アラームが止まらない")
                err_drop  = st.checkbox("💥 落下・外装破損")
                err_other = st.checkbox("📝 その他（下に記入）")
            
            rep_detail = st.text_area("詳細（エラーコードなど）", placeholder="例: E-01と表示されている、点滴スタンドから落とした 等")
            
            st.write("※チェックした症状は、業者に電話する際のメモ（カンペ）としてお使いください。")
            submitted_repair = st.form_submit_button("📨 まずは臨床工学技士に送信する", type="primary", use_container_width=True)
            
            if submitted_repair:
                selected_errors = []
                if err_power: selected_errors.append("電源が入らない")
                if err_error: selected_errors.append("エラー表示")
                if err_batt:  selected_errors.append("バッテリー劣化")
                if err_alarm: selected_errors.append("アラーム停止不可")
                if err_drop:  selected_errors.append("落下・破損")
                if err_other: selected_errors.append("その他")
                
                final_symptom = "、".join(selected_errors)
                if rep_detail:
                    final_symptom += f"（詳細: {rep_detail}）"

                if rep_dept == "選択してください" or not rep_name or not final_symptom:
                    st.error("⚠️ 部署、お名前、症状（チェックまたは記入）をすべて入力してください。")
                else:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        target_sheet = "故障報告"
                        try:
                            df_repair = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all")
                        except Exception:
                            df_repair = pd.DataFrame()
                        
                        repair_data = {
                            "報告日": str(date.today()),
                            "発生日": str(rep_date),
                            "ME No.": url_me_no,
                            "機種": device_name,
                            "報告者": rep_name,
                            "部署": rep_dept,
                            "症状": final_symptom,
                            "対応状況": "未対応" 
                        }
                        new_rep_df = pd.DataFrame([repair_data])
                        updated_rep_df = pd.concat([df_repair, new_rep_df], ignore_index=True)
                        conn.update(worksheet=target_sheet, data=updated_rep_df)
                        st.cache_data.clear()
                        st.balloons()
                        st.success("✅ CEへの報告が完了しました！")
                    except Exception as e:
                        st.error(f"送信エラー: スプレッドシートに「故障報告」シートがありません。詳細: {e}")

        # ✨ 電話ボタンを確実に出現させるロジック！
        if vendor_phone != "":
            st.markdown("---")
            st.error("🚨 【至急】業者へ直接連絡する場合")
            st.write(f"この機器は **{vendor_name}** から購入しています。")
            st.link_button(f"📞 {vendor_name} に電話をかける ({vendor_phone})", f"tel:{vendor_phone}", type="primary", use_container_width=True)
        else:
            st.info("※ この機器には業者の連絡先が登録されていません。")

    else:
        st.warning("⚠️ ME No.が認識できません。機器に貼られているQRコードを再度読み込んでください。")
    
    st.stop()

# ==========================================
# 👨‍🔧 【ルートB】管理者（CE・安富さん）専用モード
# ==========================================
with st.sidebar:
    st.subheader("💼 デモ設定 (お客様に見せる前に設定)")
    display_name = st.text_input("🏢 提案先の施設名", value="みらいクリニック")
    
    st.markdown("---")
    st.write("🔧 管理者用機能")
    show_sim = st.checkbox("💰 営業用コストシミュレーターを表示")
    
    st.markdown("---")
    st.info("💡 設定後は右上の「✕」を押してこのメニューを隠してください。")

st.title(f"{display_name} 専用")
st.title("医療機器点検アプリ")

# ==========================================
# 💡 QRダッシュボード（管理者用）
# ==========================================
if url_me_no:
    st.success(f"📱 対象機器を認識しました: **{url_me_no}**")
    device_found = False
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        clean_url_me = str(url_me_no).strip()

        for cat in categories_list:
            try:
                df_cat = conn.read(worksheet=cat, ttl=0).dropna(how="all")
                if "ME No." in df_cat.columns:
                    clean_db_me = df_cat["ME No."].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    df_device = df_cat[clean_db_me == clean_url_me]
                    
                    if not df_device.empty:
                        latest_data = df_device.iloc[-1]
                        
                        col_img, col_info = st.columns([1, 1])
                        
                        with col_img:
                            pic_url = latest_data.get("写真URL", "")
                            if pd.notnull(pic_url) and str(pic_url).startswith("http"):
                                st.image(pic_url, caption=f"{url_me_no} の外観", use_container_width=True)
                            else:
                                st.info("📸 写真は未登録です")

                        with col_info:
                            st.write(f"### 📊 基本情報 ({cat})")
                            st.write(f"**機種:** {latest_data.get('機種', '-')}")
                            st.write(f"**S/N:** {latest_data.get('製造番号', '-')}")
                            st.write(f"**製造年:** {latest_data.get('製造年', '-')}")
                            
                            doc_url = latest_data.get("添付文書URL", "")
                            if pd.notnull(doc_url) and str(doc_url).startswith("http"):
                                st.link_button("📖 添付文書・使い方を見る", doc_url, use_container_width=True)
                        
                        st.markdown("---")
                        
                        st.write("### 🚨 現場スタッフ用連絡")
                        with st.expander("この機器の故障・修理を依頼する", expanded=False):
                            with st.form("admin_repair_form"):
                                st.info(f"対象機器: {url_me_no} ({latest_data.get('機種', '-')})")
                                rep_date = st.date_input("発生日", date.today())
                                rep_dept = st.selectbox("報告部署", ["選択してください", "外来", "一般病棟", "療養病棟", "オペ室", "透析室", "その他"])
                                rep_name = st.text_input("報告者名", placeholder="例: 琉球 花子")
                                
                                st.write("▼ 症状・エラー内容")
                                col_err3, col_err4 = st.columns(2)
                                with col_err3:
                                    err_power2 = st.checkbox("🔌 電源が入らない", key="p2")
                                    err_error2 = st.checkbox("⚠️ エラー表示が出る", key="e2")
                                    err_batt2  = st.checkbox("🔋 バッテリー劣化", key="b2")
                                with col_err4:
                                    err_alarm2 = st.checkbox("🔔 アラームが止まらない", key="a2")
                                    err_drop2  = st.checkbox("💥 落下・外装破損", key="d2")
                                    err_other2 = st.checkbox("📝 その他", key="o2")
                                
                                rep_detail = st.text_area("詳細（エラーコードなど）", placeholder="例: E-01と表示されている等")
                                
                                submitted_repair = st.form_submit_button("📨 臨床工学技士に送信する", type="primary")
                                
                                if submitted_repair:
                                    selected_errors2 = []
                                    if err_power2: selected_errors2.append("電源が入らない")
                                    if err_error2: selected_errors2.append("エラー表示")
                                    if err_batt2:  selected_errors2.append("バッテリー劣化")
                                    if err_alarm2: selected_errors2.append("アラーム停止不可")
                                    if err_drop2:  selected_errors2.append("落下・破損")
                                    if err_other2: selected_errors2.append("その他")
                                    
                                    final_symptom2 = "、".join(selected_errors2)
                                    if rep_detail:
                                        final_symptom2 += f"（詳細: {rep_detail}）"

                                    if rep_dept == "選択してください" or not rep_name or not final_symptom2:
                                        st.error("⚠️ 部署、お名前、症状をすべて入力してください。")
                                    else:
                                        try:
                                            target_sheet = "故障報告"
                                            try:
                                                df_repair = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all")
                                            except Exception:
                                                df_repair = pd.DataFrame()
                                            
                                            repair_data = {
                                                "報告日": str(date.today()),
                                                "発生日": str(rep_date),
                                                "ME No.": url_me_no,
                                                "機種": latest_data.get('機種', '-'),
                                                "報告者": rep_name,
                                                "部署": rep_dept,
                                                "症状": final_symptom2,
                                                "対応状況": "未対応" 
                                            }
                                            new_rep_df = pd.DataFrame([repair_data])
                                            updated_rep_df = pd.concat([df_repair, new_rep_df], ignore_index=True)
                                            conn.update(worksheet=target_sheet, data=updated_rep_df)
                                            st.cache_data.clear()
                                            st.success("✅ 報告が完了しました！")
                                        except Exception as e:
                                            st.error(f"送信エラー詳細: {e}")

                        # 管理者側にも電話ボタンを表示
                        vendor_name_admin = str(latest_data.get('購入元', '')).strip()
                        v_phone_admin = str(latest_data.get('業者電話番号', '')).strip()
                        vendor_phone_admin = "" if v_phone_admin.lower() == "nan" else v_phone_admin
                        
                        if vendor_phone_admin != "":
                            st.link_button(f"📞 {vendor_name_admin} に電話をかける ({vendor_phone_admin})", f"tel:{vendor_phone_admin}")

                        st.markdown("---")
                        
                        with st.expander("📝 過去の点検履歴を確認する"):
                            st.dataframe(df_device.iloc[::-1], use_container_width=True, hide_index=True)
                        
                        device_found = True
                        break
            except Exception:
                continue
        
        if not device_found:
            st.info("💡 この機器の過去の点検記録はまだありません。（新規登録）")
            
    except Exception as e:
        st.error(f"🚨 スプレッドシート接続エラー: {e}")
    st.markdown("---")

# ==========================================
# 💡 アプリ本体メニュー
# ==========================================
tab_names = ["📝 点検入力", "📁 統合マスター", "🔍 全履歴", "🔲 QR発行", "📸 AI登録"]
if show_sim:
    tab_names.append("💰 コストシミュ")

tabs = st.tabs(tab_names)
tab1, tab2, tab3, tab4, tab5 = tabs[:5]

# ====== タブ1：入力画面 ======
with tab1:
    device_category = st.selectbox("▼ 点検する機器の種類", categories_list)
    
    scan_model = st.session_state.get("scan_model", "")
    if scan_model:
        st.info(f"💡 AIが読み取った型式: **{scan_model}** （合っているか確認し、下で選択してください）")

    if device_category == "輸液ポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-281", "TE-261", "TE-171", "TE-161", "TE-LM830", "OT-707", "OT-818G", "AS-800", "その他"])
    elif device_category == "シリンジポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-381", "TE-371", "TE-351", "TE-331", "その他"])
    elif device_category == "保育器":
        incubator_type = st.radio("▼ 保育器のタイプ", ["閉鎖式 (V-2100G・V85など)", "開放型 (V-505・103HEなど)"])
        if "閉鎖式" in incubator_type:
            device_model = st.selectbox("▼ 型式", ["V-2100G", "V85", "その他"])
        else:
            device_model = st.selectbox("▼ 型式", ["V-505", "103HE", "その他"])
    else:
        device_model = st.text_input("▼ 型式を入力してください")
    
    st.markdown("---")

    with st.form("check_form"):
        col_form1, col_form2 = st.columns(2)
        with col_form1:
            check_date = st.date_input("点検日", date.today())
        with col_form2:
            me_no = st.text_input("ME No.", value=url_me_no, placeholder="例: NT-001")
        
        default_sn = st.session_state.get("scan_sn", "")
        serial_no = st.text_input("製造番号 (S/N)", value=default_sn, placeholder="例: 12345678")
        
        with st.expander("🏢 事務・業者データ（新規登録・更新時のみ）", expanded=False):
            vendor = st.text_input("購入元・販売業者", placeholder="例: 〇〇医療器械株式会社")
            vendor_phone = st.text_input("業者電話番号（ハイフンあり推奨）", placeholder="例: 098-123-4567")
            purchased_date = st.date_input("購入年月日（不明な場合は本日のまま）", date.today())
            st.info("※ ここに電話番号を入れると、QR読み込み時に「電話をかける」ボタンが出現します。")

        st.write(f"### 📋 【{device_category} : {device_model}】専用チェック")
        
        chk_e1=chk_e2=chk_e3=chk_e4=chk_e5=chk_e6=chk_e7 = False
        chk_a1=chk_a2=chk_a3=chk_a4 = False
        chk_op1=chk_op2=chk_op3 = False
        chk_es1=chk_es2=chk_es3=chk_es4=chk_es5=chk_es6 = False
        chk_as1=chk_as2=chk_as3=chk_as4=chk_as5 = False
        chk_sop1=chk_sop2=chk_sop3 = False 
        flow_acc=occ_press = 0.0
        bubble_ad_water=bubble_ad_nowater = 0
        inc_c_checks = {}
        inc_o_checks = {}
        inc_temp_disp = inc_temp_meas = 36.0

        if device_category == "輸液ポンプ":
            with st.expander("🔍 ① 外観・作動・警報の詳細チェック", expanded=True):
                st.write("**【外観・作動点検】**")
                col1, col2 = st.columns(2)
                with col1:
                    chk_e1 = st.checkbox("本体の汚れ・破損なし", value=True)
                    chk_e2 = st.checkbox("ポールクランプ用ネジ穴", value=True)
                    chk_e3 = st.checkbox("チューブクランプ動作", value=True)
                    chk_e4 = st.checkbox("フィンガー部動作", value=True)
                with col2:
                    chk_e5 = st.checkbox("AC・DC切り替え", value=True)
                    chk_e6 = st.checkbox("セルフチェック機能", value=True)
                    chk_e7 = st.checkbox("表示部LED", value=True)
                
                st.write("**【その他の作動点検】**")
                col5, col6 = st.columns(2)
                with col5:
                    chk_op1 = st.checkbox("積算クリア機能", value=True)
                    chk_op2 = st.checkbox("流量設定", value=True)
                with col6:
                    chk_op3 = st.checkbox("日付・時刻設定", value=True)

                st.write("**【各種警報点検】**")
                col3, col4 = st.columns(2)
                with col3:
                    chk_a1 = st.checkbox("開始忘れ / 流量設定無し", value=True)
                    chk_a2 = st.checkbox("気泡検出 / ドアオープン", value=True)
                with col4:
                    chk_a3 = st.checkbox("輸液完了 / 再警報", value=True)
                    chk_a4 = st.checkbox("消音機能", value=True)
            
            st.write("**② 数値・精度チェック**")
            col_num1, col_num2 = st.columns(2)
            with col_num1:
                flow_acc = st.number_input("流量精度 (ml)", value=20.0, step=0.1)
                bubble_ad_water = st.number_input("気泡センサーAD値 (水入り)", value=120)
            with col_num2:
                occ_press = st.number_input("閉塞検出圧 (kpa/mmHg)", value=50.0, step=1.0)
                bubble_ad_nowater = st.number_input("気泡センサーAD値 (水無し)", value=5)

        elif device_category == "シリンジポンプ":
            with st.expander("🔍 ① 外観・作動・警報の詳細チェック", expanded=True):
                st.write("**【外観・作動点検】**")
                col1, col2 = st.columns(2)
                with col1:
                    chk_es1 = st.checkbox("本体の汚れ・破損なし", value=True)
                    chk_es2 = st.checkbox("ポールクランプ用ネジ穴", value=True)
                    chk_es3 = st.checkbox("シリンジクランプ動作", value=True)
                with col2:
                    chk_es4 = st.checkbox("スライダー・クラッチ動作", value=True)
                    chk_es5 = st.checkbox("AC・DC切り替え", value=True)
                    chk_es6 = st.checkbox("セルフチェック・LED", value=True)
                
                st.write("**【その他の作動点検】**")
                col7, col8 = st.columns(2)
                with col7:
                    chk_sop1 = st.checkbox("積算クリア機能", value=True)
                    chk_sop2 = st.checkbox("流量設定", value=True)
                with col8:
                    chk_sop3 = st.checkbox("日付・時刻設定", value=True)

                st.write("**【各種警報点検】**")
                col3, col4 = st.columns(2)
                with col3:
                    chk_as1 = st.checkbox("シリンジ外れ・サイズ認識", value=True)
                    chk_as2 = st.checkbox("押し子外れ / クラッチ外れ", value=True)
                    chk_as3 = st.checkbox("残量 / 閉塞警報", value=True)
                with col4:
                    chk_as4 = st.checkbox("開始忘れ / 流量設定無し", value=True)
                    chk_as5 = st.checkbox("消音 / 再警報", value=True)
            
            st.write("**② 数値・精度チェック**")
            col_num1_s, col_num2_s = st.columns(2)
            with col_num1_s:
                flow_acc = st.number_input("流量精度チェック (ml)", value=10.0, step=0.1)
            with col_num2_s:
                occ_press = st.number_input("閉塞検出圧 (kpa)", value=80.0, step=1.0)

        elif device_category == "保育器":
            if "閉鎖式" in incubator_type:
                with st.expander("🔍 閉鎖式保育器 点検項目", expanded=True):
                    st.write("**① 外観点検**")
                    c1, c2 = st.columns(2)
                    with c1:
                        inc_c_checks["本体・フード破損なし"] = st.checkbox("本体・パネル・フード等に破損なし", value=True)
                        inc_c_checks["キャスター動作"] = st.checkbox("キャスター・ストッパー動作", value=True)
                        inc_c_checks["手入れ窓パッキン"] = st.checkbox("手入れ窓・パッキン破損なし", value=True)
                        inc_c_checks["ホース破損なし"] = st.checkbox("ホースアッセンブリ破損なし", value=True)
                    with c2:
                        inc_c_checks["フィルター状態"] = st.checkbox("フィルター汚れなし・期限内", value=True)
                        inc_c_checks["電源コード・プラグ"] = st.checkbox("電源・プラグ・アースピン破損なし", value=True)
                        inc_c_checks["センサー破損なし"] = st.checkbox("各種センサー・接続部破損なし", value=True)

                    st.write("**② 作動・機能点検**")
                    c3, c4 = st.columns(2)
                    with c3:
                        inc_c_checks["傾斜装置"] = st.checkbox("傾斜装置スムーズ動作", value=True)
                        inc_c_checks["ファン作動"] = st.checkbox("ファン確実作動・破損なし", value=True)
                    with c4:
                        inc_c_checks["加湿警報"] = st.checkbox("低水位・水槽外れ警報作動", value=True)
                        inc_c_checks["SpO2表示"] = st.checkbox("SpO2表示・測定(対応機のみ)", value=True)

                    st.write("**③ 温度制御 (設定 36.0±1℃)**")
                    c5, c6 = st.columns(2)
                    with c5:
                        inc_temp_disp = st.number_input("表示値 (℃)", value=36.0, step=0.1)
                    with c6:
                        inc_temp_meas = st.number_input("測定値 (℃)", value=36.0, step=0.1)

            else:
                with st.expander("🔍 開放型保育器 点検項目", expanded=True):
                    st.write("**① コントロール・作動・表示点検**")
                    o1, o2 = st.columns(2)
                    with o1:
                        inc_o_checks["電源・照明スイッチ"] = st.checkbox("電源・照明灯スイッチ異常なし", value=True)
                        inc_o_checks["表示・キー操作"] = st.checkbox("表示部・キー操作異常なし", value=True)
                        inc_o_checks["温度制御(マニュアル)"] = st.checkbox("マニュアルコントロール動作", value=True)
                        inc_o_checks["温度制御(サーボ)"] = st.checkbox("体温プローブ・サーボ動作", value=True)
                    with o2:
                        inc_o_checks["SpO2表示"] = st.checkbox("SpO2・HR表示測定が可能か", value=True)
                        inc_o_checks["タイマー表示"] = st.checkbox("タイマー機能・表示動作", value=True)

                    st.write("**② 各種警報機能**")
                    o3, o4 = st.columns(2)
                    with o3:
                        inc_o_checks["チェックスイッチ"] = st.checkbox("チェックスイッチ作動", value=True)
                        inc_o_checks["設定温度警報(マニュアル)"] = st.checkbox("設定温度警報(マニュアル)", value=True)
                        inc_o_checks["設定温度警報(皮膚温)"] = st.checkbox("設定温度警報(皮膚温)", value=True)
                    with o4:
                        inc_o_checks["プローブ警報"] = st.checkbox("プローブ警報作動", value=True)
                        inc_o_checks["停電警報"] = st.checkbox("停電警報作動", value=True)
                        inc_o_checks["キャノピ傾斜"] = st.checkbox("キャノピ傾斜動作", value=True)

                    st.write("**③ 蘇生装置・酸素・外装**")
                    o5, o6 = st.columns(2)
                    with o5:
                        inc_o_checks["蘇生装置"] = st.checkbox("蘇生装置の機能点検・異常なし", value=True)
                        inc_o_checks["酸素ブレンダ作動"] = st.checkbox("酸素ブレンダ作動確認", value=True)
                        inc_o_checks["供給ガス警報"] = st.checkbox("供給ガス警報が発生するか", value=True)
                    with o6:
                        inc_o_checks["吸引・流量計"] = st.checkbox("吸引ユニット・酸素流量計正常", value=True)
                        inc_o_checks["外装・キャノピ・ネジ類"] = st.checkbox("支柱・キャノピ・反射板・ネジ等", value=True)
                        inc_o_checks["電源・ジャック・ガード"] = st.checkbox("電源コード・各種ジャック・ガード", value=True)

        else:
            exterior_result = st.radio("外装点検", ["異常なし", "異常あり"], horizontal=True)
            detail_result = st.text_input("精度チェック（測定値など）", placeholder="例: 換気量 500ml")

        st.markdown("---")
        inspector = st.text_input("実施者", value="安富 翔")
        result = st.radio("総合評価", ["使用可", "メーカー修理", "廃棄"], horizontal=True) 
        memo = st.text_area("備考・報告欄")
        
        submitted = st.form_submit_button("スプレッドシートに保存")

    if submitted:
        if not me_no:
            st.warning("⚠️ ME No.を入力してください")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                target_sheet = device_category
                
                try:
                    existing_data = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all") 
                except Exception:
                    existing_data = pd.DataFrame()
                
                is_duplicate = False
                if not existing_data.empty and "ME No." in existing_data.columns and "点検日" in existing_data.columns:
                    clean_db_me_check = existing_data["ME No."].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    is_duplicate = ((clean_db_me_check == str(me_no).strip()) & (existing_data["点検日"].astype(str) == str(check_date))).any()
                
                if is_duplicate:
                    st.error(f"🚨 ちょっと待って！「{me_no}」は本日（{check_date}）すでに点検済みです！")
                else:
                    combined_model = f"{device_category} ({device_model})"
                    data_dict = {
                        "カテゴリ": device_category,
                        "点検日": str(check_date),
                        "ME No.": str(me_no).strip(),
                        "製造番号": serial_no,
                        "製造年": st.session_state.get("scan_year", ""),
                        "機種": combined_model,
                        "購入元": vendor,                     
                        "業者電話番号": vendor_phone,         
                        "購入年月日": str(purchased_date),   
                        "実施者": inspector,
                        "判定": result,
                        "備考": memo
                    }
                    
                    if device_category == "輸液ポンプ":
                        data_dict.update({
                            "本体の汚れ・破損": "〇" if chk_e1 else "×",
                            "ポールクランプ用ネジ穴": "〇" if chk_e2 else "×",
                            "チューブクランプ動作": "〇" if chk_e3 else "×",
                            "フィンガー部動作": "〇" if chk_e4 else "×",
                            "AC・DC切り替え": "〇" if chk_e5 else "×",
                            "セルフチェック機能": "〇" if chk_e6 else "×",
                            "表示部LED": "〇" if chk_e7 else "×",
                            "開始忘れ_流量設定無し": "〇" if chk_a1 else "×",
                            "気泡検出_ドアオープン": "〇" if chk_a2 else "×",
                            "輸液完了_再警報": "〇" if chk_a3 else "×",
                            "消音機能": "〇" if chk_a4 else "×",
                            "積算クリア機能": "〇" if chk_op1 else "×",
                            "流量設定": "〇" if chk_op2 else "×",
                            "日付・時刻設定": "〇" if chk_op3 else "×",
                            "流量精度値": flow_acc,
                            "閉塞検出圧値": occ_press,
                            "気泡センサーAD値_水入り": bubble_ad_water,
                            "気泡センサーAD値_水無し": bubble_ad_nowater
                        })
                    elif device_category == "シリンジポンプ":
                        data_dict.update({
                            "本体の汚れ・破損": "〇" if chk_es1 else "×",
                            "ポールクランプ用ネジ穴": "〇" if chk_es2 else "×",
                            "シリンジクランプ動作": "〇" if chk_es3 else "×",
                            "スライダー_クラッチ動作": "〇" if chk_es4 else "×",
                            "AC・DC切り替え": "〇" if chk_es5 else "×",
                            "セルフチェック機能": "〇" if chk_es6 else "×",
                            "外れ_サイズ認識": "〇" if chk_as1 else "×",
                            "押し子_クラッチ外れ": "〇" if chk_as2 else "×",
                            "残量_閉塞警報": "〇" if chk_as3 else "×",
                            "開始忘れ_流量設定無し": "〇" if chk_as4 else "×",
                            "消音機能_再警報": "〇" if chk_as5 else "×",
                            "積算クリア機能": "〇" if chk_sop1 else "×",
                            "流量設定": "〇" if chk_sop2 else "×",
                            "日付・時刻設定": "〇" if chk_sop3 else "×",
                            "流量精度値": flow_acc,
                            "閉塞検出圧値": occ_press
                        })
                    elif device_category == "保育器":
                        if "閉鎖式" in incubator_type:
                            for k, v in inc_c_checks.items():
                                data_dict[k] = "〇" if v else "×"
                            data_dict["表示値(℃)"] = inc_temp_disp
                            data_dict["測定値(℃)"] = inc_temp_meas
                        else:
                            for k, v in inc_o_checks.items():
                                data_dict[k] = "〇" if v else "×"

                    new_data = pd.DataFrame([data_dict])
                    updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                    
                    conn.update(worksheet=target_sheet, data=updated_df)
                    st.cache_data.clear()
                    st.balloons()
                    st.success(f"大成功！{me_no} のデータを「{target_sheet}」シートに記録しました！")
            except Exception as e:
                st.error(f"エラー発生: スプレッドシート確認エラー。詳細: {e}")

# ====== タブ2：マスター ======
with tab2:
    st.subheader("🏥 統合機器マスター（監査・事務用ダッシュボード）")
    st.write("スプレッドシートの**全シートのデータを自動で一つに集約**しています。")
    
    if st.button("🔄 全データを最新化する"):
        st.cache_data.clear()

    with st.spinner("全データを集約中..."):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            all_devices = pd.DataFrame()
            
            for cat in categories_list:
                try:
                    df = conn.read(worksheet=cat, ttl=0).dropna(how="all")
                    if not df.empty and "ME No." in df.columns:
                        # ME No.を綺麗にして重複を弾く
                        df["ME_Clean"] = df["ME No."].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                        df_master = df.drop_duplicates(subset=["ME_Clean"], keep="last")
                        if "カテゴリ" not in df_master.columns:
                            df_master["カテゴリ"] = cat
                        all_devices = pd.concat([all_devices, df_master], ignore_index=True)
                except Exception:
                    pass 
                    
            if all_devices.empty:
                st.info("登録されているデータがありません。")
            else:
                sub_tab1, sub_tab2 = st.tabs(["📋 監査用 (一覧・台数)", "🏢 事務用 (詳細検索・購入元)"])
                
                with sub_tab1:
                    st.metric("✅ 病院全体の総登録台数", f"{len(all_devices)} 台")
                    st.write("▼ 監査用シンプルリスト")
                    audit_cols = ["カテゴリ", "機種", "ME No.", "製造番号", "点検日", "判定"]
                    display_audit = all_devices[[c for c in audit_cols if c in all_devices.columns]]
                    st.dataframe(display_audit.rename(columns={"点検日": "最終点検日"}), hide_index=True, use_container_width=True)
                
                with sub_tab2:
                    st.write("特定の機器の購入元や詳細を調べたい場合は、ここでME No.を検索してください。")
                    # 検索用の綺麗なリストを作る
                    clean_me_list = all_devices["ME_Clean"].tolist()
                    search_me = st.selectbox("🔍 詳細を見たいME No.を選択", clean_me_list)
                    
                    if search_me:
                        target_data = all_devices[all_devices["ME_Clean"] == search_me].iloc[0]
                        
                        st.markdown("### 🏢 事務・台帳情報")
                        col_j1, col_j2 = st.columns(2)
                        with col_j1:
                            st.write(f"**ME No.:** {target_data.get('ME_Clean', '-')}")
                            st.write(f"**機種:** {target_data.get('機種', '-')}")
                            st.write(f"**製造番号:** {target_data.get('製造番号', '-')}")
                        with col_j2:
                            vendor_val = str(target_data.get("購入元", "")).strip()
                            phone_val = str(target_data.get("業者電話番号", "")).strip()
                            date_val = str(target_data.get("購入年月日", "")).strip()
                            
                            st.write(f"**購入元・販売業者:** {vendor_val if vendor_val and vendor_val != 'nan' else '未登録'}")
                            st.write(f"**業者電話番号:** {phone_val if phone_val and phone_val != 'nan' else '未登録'}")
                            st.write(f"**購入年月日:** {date_val if date_val and date_val != 'nan' else '未登録'}")
                            st.write(f"**最終点検日:** {target_data.get('点検日', '-')}")
                            
        except Exception as e:
            st.error(f"🚨 データ集約エラー: {e}")

# ====== タブ3：全履歴 ======
with tab3:
    st.subheader("📊 過去の点検履歴検索")
    view_cat_history = st.selectbox("📂 読み込むシートを選択", categories_list + ["故障報告"], key="hist_cat")
    
    if st.button("🔄 最新のデータを読み込む"):
        st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=view_cat_history, ttl=0).dropna(how="all")
        if df.empty:
            st.info(f"「{view_cat_history}」シートにはまだデータがありません。")
        else:
            search_query = st.text_input("🔍 探したい「ME No.」を入力してください", value=url_me_no)
            if search_query:
                # 検索時も.0を無視してマッチングしやすくする
                clean_df_me = df["ME No."].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                df = df[clean_df_me.str.contains(str(search_query).strip(), case=False)]
                st.write(f"「{search_query}」の検索結果: {len(df)} 件")
            st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"🚨 接続エラー: {e}")

# ====== タブ4：QRコード発行機能 ======
with tab4:
    st.subheader("🔲 機器用QRコードの作成")
    st.write("対象の「ME No.」を入力すると、機器に貼り付ける用のQRコードが作成されます。")
    
    base_url = st.text_input("このアプリのURL（ブラウザの上のアドレス）を貼り付けてください", value="ここにアプリのURLを貼り付けてください")
    target_qr_me = st.text_input("🔤 QRコードを作りたい「ME No.」を入力", placeholder="例: TE-381-001")
    
    if st.button("QRコードを作成する"):
        if base_url and target_qr_me:
            if "?" in base_url:
                 final_url = f"{base_url}&me_no={target_qr_me}&mode=nurse"
            elif base_url.endswith("/"):
                final_url = f"{base_url}?me_no={target_qr_me}&mode=nurse"
            else:
                final_url = f"{base_url}/?me_no={target_qr_me}&mode=nurse"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(final_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.success(f"「{target_qr_me}」専用のQRコードができました！")
            st.write("※このQRコードを読むと「看護師モード（報告専用画面）」が開きます。")
            st.image(byte_im, width=200)
            
            st.download_button(
                label="📥 このQRコードを画像として保存",
                data=byte_im,
                file_name=f"QR_{target_qr_me}.png",
                mime="image/png"
            )
        else:
            st.warning("アプリのURLと、ME No.の両方を入力してください。")

# ====== タブ5：AI新規登録ダッシュボード ======
with tab5:
    st.subheader("📸 AI銘板スキャナー (新規登録用)")
    st.write("新しい機器の銘板を撮影すると、情報を読み取って「点検入力」タブに自動転送します。")
    
    if ai_model is None:
        st.error("❌ APIキーが設定されていないか、ライブラリのバージョンが古いです。")
    else:
        img_file = st.camera_input("銘板（シール）を撮影してください", key="ai_camera")
        
        if img_file:
            with st.spinner("AIが文字を解析しています（約10秒）..."):
                try:
                    img = Image.open(img_file)
                    
                    prompt = """
                    この医療機器の銘板写真から以下の情報を抜き出して、JSON形式で回答してください。
                    キーは以下のようにしてください:
                    - model (型式)
                    - serial_number (製造番号/SN)
                    - manufacture_year (製造年。例: 2018)
                    """
                    
                    response = ai_model.generate_content([prompt, img])
                    
                    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        
                        st.success("✅ 読み取り成功！")
                        st.write(f"**型式:** {data.get('model', '見つかりませんでした')}")
                        st.write(f"**製造番号:** {data.get('serial_number', '見つかりませんでした')}")
                        st.write(f"**製造年:** {data.get('manufacture_year', '見つかりませんでした')}")
                        
                        st.session_state["scan_model"] = data.get("model", "")
                        st.session_state["scan_sn"] = data.get("serial_number", "")
                        st.session_state["scan_year"] = data.get("manufacture_year", "")
                        
                        st.info("💡 このデータは一番左の「📝 点検入力」タブの入力欄に自動でセットされました！そのまま点検に進めます。")
                    else:
                        st.warning("文字が見つかりませんでした。ブレていないか確認してもう一度撮影してください。")
                        
                except Exception as e:
                    st.error(f"🚨 システムエラー: {e}")

# ==========================================
# ✨ タブ6：コスト削減シミュレーター（チェックが入った時のみ出現！）
# ==========================================
if show_sim:
    with tabs[5]:
        st.subheader("💰 コスト削減シミュレーター")
        st.write("軽微な修理（バッテリー交換やパッキン交換など）をメーカーではなくmiratechにお任せいただいた場合の、**年間のコスト削減効果**を試算します。")

        col_sim1, col_sim2 = st.columns(2)
        
        with col_sim1:
            st.write("#### ▼ 条件を入力してください")
            maker_cost = st.slider("🏢 メーカー修理代 / 1回 (万円)", min_value=1, max_value=30, value=10)
            miratech_cost = st.slider("🔧 miratech 修理代 / 1回 (万円)", min_value=1, max_value=30, value=5)
            repair_count = slider_val = st.slider("📅 年間の想定修理件数 (件)", min_value=1, max_value=100, value=12)

        maker_total = maker_cost * repair_count
        miratech_total = miratech_cost * repair_count
        savings = maker_total - miratech_total

        with col_sim2:
            st.write("#### ▼ 予想される削減効果")
            st.info(f"💡 1回あたりの削減額: **{maker_cost - miratech_cost} 万円**")
            st.success("✨ 年間コスト削減額 ✨")
            st.markdown(f"<h1 style='text-align: center; color: #ff4b4b; font-size: 3.5rem;'>{savings} 万円</h1>", unsafe_allow_html=True)

        st.markdown("---")
        st.write("### 📊 年間予想コスト比較表")

        df_chart = pd.DataFrame({
            "プラン": ["メーカーに依頼した場合", "miratechに依頼した場合"],
            "年間コスト (万円)": [maker_total, miratech_total]
        }).set_index("プラン")

        st.bar_chart(df_chart, use_container_width=True)

        st.write("▼ 詳細データ")
        df_table = pd.DataFrame({
            "項目": ["1回あたりのコスト", "想定年間件数", "年間トータルコスト"],
            "メーカー依頼": [f"{maker_cost} 万円", f"{repair_count} 件", f"{maker_total} 万円"],
            "miratech": [f"{miratech_cost} 万円", f"{repair_count} 件", f"{miratech_total} 万円"]
        })
        st.dataframe(df_table, hide_index=True, use_container_width=True)
