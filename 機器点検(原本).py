import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import qrcode
from io import BytesIO
import google.generativeai as genai
import json
import re
from PIL import Image
import base64

# ==========================================
# ⚙️ 設定：ここを自分のアプリのURLに書き換えてください
# ==========================================
APP_URL = "https://miratech-app-4xydfx4bzmzhqymgpxu8r6.streamlit.app"

# ページ設定
st.set_page_config(page_title="miratech 医療機器管理システム", layout="centered")

# ==========================================
# 🔐 マルチテナント＆QR自動ログイン認証
# ==========================================
def check_auth():
    query_params = st.query_params
    fid = query_params.get("fid", "")
    token = query_params.get("key", "")
    
    if "logged_in_facility" not in st.session_state:
        st.session_state["logged_in_facility"] = None
    if "facility_key" not in st.session_state:
        st.session_state["facility_key"] = None

    if st.session_state["logged_in_facility"] is not None:
        return True

    for key in st.secrets.keys():
        try:
            sec_data = st.secrets[key]
            if "id_code" in sec_data and "token" in sec_data:
                if fid == sec_data["id_code"] and token == sec_data["token"]:
                    st.session_state["logged_in_facility"] = sec_data["name"]
                    st.session_state["facility_key"] = key
                    st.session_state["is_nurse_mode"] = True
                    return True
        except Exception:
            pass

    st.warning("⚠️ miratech 琉球 医療機器管理システム")
    with st.form("login_form"):
        input_id = st.text_input("🏢 施設ID（企業コード）")
        input_pass = st.text_input("🔑 パスワード", type="password")
        if st.form_submit_button("ログイン", use_container_width=True):
            clean_id = input_id.strip()
            clean_pass = input_pass.strip()
            for key in st.secrets.keys():
                try:
                    sec_data = st.secrets[key]
                    if "id" in sec_data and "password" in sec_data:
                        if clean_id == sec_data["id"] and clean_pass == sec_data["password"]:
                            st.session_state["logged_in_facility"] = sec_data["name"]
                            st.session_state["facility_key"] = key
                            st.session_state["is_nurse_mode"] = False
                            st.rerun()
                            return True
                except Exception:
                    pass
            st.error("❌ 施設IDまたはパスワードが違います。")
    return False

if not check_auth():
    st.stop()

# --- ログイン後の変数 ---
facility_name = st.session_state["logged_in_facility"]
query_params = st.query_params
url_me_no = query_params.get("me_no", "")
categories_list = ["輸液ポンプ", "シリンジポンプ", "保育器", "分娩監視装置", "人工呼吸器", "その他"]

# AI設定
ai_model = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        ai_model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        st.error(f"APIキーの設定エラー: {e}")

# ==========================================
# 👩‍⚕️ 【ルートA】現場スタッフモード
# ==========================================
if st.session_state.get("is_nurse_mode"):
    st.markdown(f"<h2 style='text-align: center; color: #FF4B4B;'>🚨 {facility_name}</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>機器トラブル報告システム</h3>", unsafe_allow_html=True)
    if url_me_no:
        st.success(f"📱 対象機器: **{url_me_no}**")
        with st.form("nurse_report_form"):
            rep_date = st.date_input("発生日", date.today())
            rep_dept = st.selectbox("あなたの部署", ["選択してください", "外来", "一般病棟", "療養病棟", "オペ室", "透析室", "その他"])
            rep_name = st.text_input("報告者名")
            c1, c2 = st.columns(2)
            with c1:
                err_power = st.checkbox("🔌 電源不良")
                err_error = st.checkbox("⚠️ エラー表示")
            with c2:
                err_alarm = st.checkbox("🔔 アラーム")
                err_drop = st.checkbox("💥 落下・破損")
            rep_detail = st.text_area("詳細内容")
            if st.form_submit_button("📨 報告を送信する", type="primary", use_container_width=True):
                st.balloons()
                st.success("✅ 報告を受け付けました。ありがとうございます。")
    else:
        st.error("⚠️ 機器情報が読み取れません。")
    if st.button("管理者用ログインへ"):
        st.session_state["logged_in_facility"] = None
        st.session_state["is_nurse_mode"] = False
        st.rerun()
    st.stop()

# ==========================================
# 👨‍🔧 【ルートB】管理者（安富さん）モード
# ==========================================
st.markdown(f"### 🏢 {facility_name}")
st.title("医療機器点検・管理")

tabs = st.tabs(["📝 点検入力", "📁 マスター", "🔍 全履歴", "🔲 QR発行", "📸 AI登録"])

# ====== タブ1：入力画面 ======
with tabs[0]:
    device_category = st.selectbox("▼ 点検する機器の種類", categories_list)
    scan_model = st.session_state.get("scan_model", "")
    if scan_model:
        st.info(f"💡 AIが読み取った型式: **{scan_model}**")

    if device_category == "輸液ポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-281", "TE-261", "TE-171", "TE-161", "TE-LM830", "OT-707", "OT-818G", "AS-800", "その他"])
    elif device_category == "シリンジポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-381", "TE-371", "TE-351", "TE-331", "その他"])
    elif device_category == "保育器":
        incubator_type = st.radio("▼ 保育器のタイプ", ["閉鎖式", "開放型"])
        device_model = st.selectbox("▼ 型式", ["V-2100G", "V85", "その他"]) if incubator_type == "閉鎖式" else st.selectbox("▼ 型式", ["V-505", "103HE", "その他"])
    else:
        device_model = st.text_input("▼ 型式を入力してください")

    st.markdown("---")
    with st.form("check_form"):
        col_form1, col_form2 = st.columns(2)
        with col_form1: check_date = st.date_input("点検日", date.today())
        with col_form2: me_no = st.text_input("ME No.", value=url_me_no, placeholder="例: Y0001")
        
        default_sn = st.session_state.get("scan_sn", "")
        serial_no = st.text_input("製造番号 (S/N)", value=default_sn, placeholder="例: 12345678")
        
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
                
                # --- ① 履歴シートへの保存 ---
                target_sheet = device_category
                try:
                    existing_data = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all")
                except Exception:
                    existing_data = pd.DataFrame()
                
                data_dict = {
                    "点検日": str(check_date), 
                    "ME No.": me_no, 
                    "製造番号": serial_no, 
                    "製造年": st.session_state.get("scan_year", ""), 
                    "機種": f"{device_category}({device_model})", 
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
                
                # --- ② 機器マスター台帳の自動更新 ---
                master_sheet = "機器マスター"
                try:
                    master_df = conn.read(worksheet=master_sheet, ttl=0).dropna(how="all")
                except Exception:
                    master_df = pd.DataFrame(columns=["ME No.", "カテゴリ", "機種", "製造番号", "製造年", "最終点検日", "最終判定", "最終実施者"])

                new_master_entry = pd.DataFrame([{
                    "ME No.": me_no,
                    "カテゴリ": device_category,
                    "機種": f"{device_category}({device_model})",
                    "製造番号": serial_no,
                    "製造年": st.session_state.get("scan_year", ""),
                    "最終点検日": str(check_date),
                    "最終判定": result,
                    "最終実施者": inspector
                }])

                if not master_df.empty and "ME No." in master_df.columns:
                    master_df = master_df[master_df["ME No."].astype(str) != str(me_no)]
                
                updated_master_df = pd.concat([master_df, new_master_entry], ignore_index=True)
                conn.update(worksheet=master_sheet, data=updated_master_df)
                
                # 保存完了アクション
                st.balloons()
                st.success(f"✅ {me_no} の点検記録と、機器マスター台帳の更新が完了しました！")

                # --- QRコード自動生成 ---
                st.markdown("---")
                st.subheader(f"🔲 {me_no} 専用QRコード")
                
                f_key = st.session_state.get("facility_key")
                if f_key and f_key in st.secrets:
                    fid_code = st.secrets[f_key].get("id_code", "")
                    tok = st.secrets[f_key].get("token", "")
                else:
                    fid_code, tok = "", ""

                final_url = f"{APP_URL}/?fid={fid_code}&key={tok}&me_no={me_no}"
                
                qr = qrcode.QRCode(version=1, box_size=10, border=4)
                qr.add_data(final_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buf = BytesIO()
                img.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                # ✨ 新しいQRコード表示（エラー回避＆ツールチップなし）
                b64 = base64.b64encode(byte_im).decode()
                html_img = f'''
                <a href="data:image/png;base64,{b64}" download="QR_{me_no}.png">
                    <img src="data:image/png;base64,{b64}" width="150" style="border: 2px solid #eee; padding: 10px; border-radius: 10px; background-color: white;">
                </a>
                <br>
                <p style="font-size: 14px; color: gray;">👆 QRコードを<b>タップ（クリック）</b>すると直接ダウンロードされます。<br>スマホの場合は<b>長押しして「画像を保存」</b>も可能です。</p>
                '''
                st.markdown(html_img, unsafe_allow_html=True)

            except Exception as e: # ← こいつが消えてた犯人です！
                st.error(f"エラー: {e}")

# ====== タブ2：マスター ======
with tabs[1]:
    st.subheader("🏥 機器マスター")
    view_cat_master = st.selectbox("📂 読み込むシートを選択", ["機器マスター"] + categories_list + ["故障報告"], key="master_cat")
    if st.button("🔄 台帳を更新する"):
        st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=view_cat_master, ttl=0).dropna(how="all")
        if df.empty or ("ME No." not in df.columns and view_cat_master != "故障報告"):
            st.info(f"「{view_cat_master}」シートにはまだデータがありません。")
        else:
            if view_cat_master == "故障報告":
                st.dataframe(df.iloc[::-1], hide_index=True, use_container_width=True)
            elif view_cat_master == "機器マスター":
                # ✨ 監査用の自動集計ダッシュボード
                st.write("### 📊 施設内 機器保有サマリー")
                col_sum1, col_sum2 = st.columns([1, 2])
                
                with col_sum1:
                    if "カテゴリ" in df.columns:
                        summary_df = df["カテゴリ"].value_counts().reset_index()
                        summary_df.columns = ["機器の種類", "保有台数"]
                        st.dataframe(summary_df, hide_index=True, use_container_width=True)
                        st.info(f"🏥 総保有台数: **{len(df)}** 台")
                
                with col_sum2:
                    st.write("▼ 全機器リスト")
                    st.dataframe(df, hide_index=True, use_container_width=True)
            else:
                df_master = df.drop_duplicates(subset=["ME No."], keep="last")
                display_cols = ["ME No.", "製造番号", "点検日", "判定"]
                existing_cols = [col for col in display_cols if col in df_master.columns]
                st.dataframe(df_master[existing_cols].rename(columns={"点検日": "最終点検日"}), hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"🚨 接続エラー: {e}")

# ====== タブ3：全履歴 ======
with tabs[2]:
    st.subheader("📊 点検履歴データ")
    view_cat_history = st.selectbox("📂 読み込むシートを選択", categories_list, key="hist_cat")
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
                df = df[df["ME No."].astype(str).fillna("").str.contains(search_query, case=False)]
                st.write(f"「{search_query}」の検索結果: {len(df)} 件")
            st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"🚨 接続エラー: {e}")

# ====== タブ4：QRコード発行機能 ======
with tabs[3]:
    st.subheader("🔲 機器用QRコードの作成")
    st.write("対象の「ME No.」を入力すると、機器に貼り付ける用のQRコードが作成されます。")
    facility_key = st.session_state.get("facility_key")
    if facility_key and facility_key in st.secrets:
        sec_data = st.secrets[facility_key]
        auto_fid = sec_data.get("id_code", "")
        auto_token = sec_data.get("token", "")
    else:
        auto_fid = ""
        auto_token = ""
    
    target_qr_me = st.text_input("🔤 QRコードを作りたい「ME No.」を入力", placeholder="例: TE-381-001")
    
    if st.button("QRコードを作成する"):
        if APP_URL and target_qr_me and auto_fid and auto_token:
            if APP_URL.endswith("/"):
                final_url = f"{APP_URL}?fid={auto_fid}&key={auto_token}&me_no={target_qr_me}"
            else:
                final_url = f"{APP_URL}/?fid={auto_fid}&key={auto_token}&me_no={target_qr_me}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(final_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.success(f"「{target_qr_me}」専用のQRコードができました！")
            
            # ✨ 新しいQRコード表示（エラー回避＆ツールチップなし）
            b64 = base64.b64encode(byte_im).decode()
            html_img = f'''
            <a href="data:image/png;base64,{b64}" download="QR_{target_qr_me}.png">
                <img src="data:image/png;base64,{b64}" width="200" style="border: 2px solid #eee; padding: 10px; border-radius: 10px; background-color: white;">
            </a>
            <br>
            <p style="font-size: 14px; color: gray;">👆 QRコードを<b>タップ（クリック）</b>すると直接ダウンロードされます。<br>スマホの場合は<b>長押しして「画像を保存」</b>も可能です。</p>
            '''
            st.markdown(html_img, unsafe_allow_html=True)
        else:
            st.warning("ME No.を入力してください。")

# ====== タブ5：AI新規登録ダッシュボード ======
with tabs[4]:
    st.subheader("📸 AI銘板スキャナー (新規登録用)")
    st.write("新しい機器の銘板を撮影すると、情報を読み取って「点検入力」タブに自動転送します。")
    
    if ai_model is None:
        st.error("❌ APIキーが設定されていないか、ライブラリのバージョンが古いです。")
    else:
        img_file = st.camera_input("銘板（シール）を撮影してください", key="ai_camera")
        
        if img_file:
            current_image_bytes = img_file.getvalue()
            if st.session_state.get("last_scanned_image") != current_image_bytes:
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
                            
                            st.session_state["scan_model"] = data.get("model", "")
                            st.session_state["scan_sn"] = data.get("serial_number", "")
                            st.session_state["scan_year"] = data.get("manufacture_year", "")
                            
                            st.session_state["last_scanned_image"] = current_image_bytes
                            st.rerun() 
                        else:
                            st.warning("文字が見つかりませんでした。ブレていないか確認してもう一度撮影してください。")
                    except Exception as e:
                        st.error(f"🚨 システムエラー: {e}")
            else:
                st.success("✅ 読み取り成功！")
                st.write(f"**型式:** {st.session_state.get('scan_model', '')}")
                st.write(f"**製造番号:** {st.session_state.get('scan_sn', '')}")
                st.write(f"**製造年:** {st.session_state.get('scan_year', '')}")
                st.info("💡 このデータは一番左の「📝 点検入力」タブの入力欄に自動でセットされました！そのまま点検に進めます。")
