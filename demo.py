import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, date
import qrcode
from io import BytesIO
import google.generativeai as genai
import json
import re
from PIL import Image
import base64

# ==========================================
# ⚙️ 設定
# ==========================================
APP_URL = "https://miratechryukyu-hashs-apps-n4w6p52.streamlit.app/"

st.set_page_config(page_title="miratech 医療機器管理システム", layout="centered")

# --- ログ書き込み用共通関数 ---
def write_log(user_name, action):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            df_logs = conn.read(worksheet="アクセスログ", ttl=0).dropna(how="all")
        except:
            df_logs = pd.DataFrame(columns=["日時", "ユーザー名", "アクション"])
        
        new_log = pd.DataFrame([{
            "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ユーザー名": user_name,
            "アクション": action
        }])
        updated_logs = pd.concat([df_logs, new_log], ignore_index=True)
        conn.update(worksheet="アクセスログ", data=updated_logs)
    except Exception as e:
        pass # ログ書き込み失敗でアプリを止めない

# ==========================================
# 🔐 マルチテナント＆個別IDログイン認証
# ==========================================
def check_auth():
    query_params = st.query_params
    fid = query_params.get("fid", "")
    token = query_params.get("key", "")
    
    if "logged_in_facility" not in st.session_state:
        st.session_state["logged_in_facility"] = None
    if "current_user_name" not in st.session_state:
        st.session_state["current_user_name"] = None
    if "is_admin" not in st.session_state:
        st.session_state["is_admin"] = False

    # すでにログイン済みなら通過
    if st.session_state["logged_in_facility"] is not None:
        return True

    # 1. QRコードからの自動ログイン（現場スタッフ用：足跡は「QR経由」として記録）
    for key in st.secrets.keys():
        try:
            sec_data = st.secrets[key]
            if "id_code" in sec_data and "token" in sec_data:
                if fid == sec_data["id_code"] and token == sec_data["token"]:
                    st.session_state["logged_in_facility"] = sec_data["name"]
                    st.session_state["facility_key"] = key
                    st.session_state["is_nurse_mode"] = True
                    st.session_state["current_user_name"] = "現場QRスキャン"
                    write_log("現場スタッフ(QR)", f"{sec_data['name']} のトラブル報告画面へアクセス")
                    return True
        except Exception:
            pass

    # 2. 個別IDでのログイン・申請画面（管理者・エンジニア用）
    st.warning("⚠️ miratech 琉球 医療機器管理システム")
    tab1, tab2 = st.tabs(["🔐 ログイン", "📝 新規利用申請"])

    with tab1:
        with st.form("login_form"):
            input_id = st.text_input("👤 ユーザーID")
            input_pass = st.text_input("🔑 パスワード", type="password")
            if st.form_submit_button("ログイン", use_container_width=True):
                clean_id = input_id.strip()
                clean_pass = input_pass.strip()
                
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_users = conn.read(worksheet="ユーザー", ttl=0).dropna(how="all")
                    
                    # 💡 修正ポイント1：ID検索時に「.0」を消し、空白も削ってから比較する
                    clean_db_ids = df_users["ユーザーID"].astype(str).str.replace(".0", "", regex=False).str.strip()
                    user_row = df_users[clean_db_ids == clean_id]
                    
                    if not user_row.empty:
                        user_info = user_row.iloc[0]
                        
                        # 💡 修正ポイント2：パスワードとステータスも「.0」や「空白」を消して純粋な文字にして比較
                        saved_pass = str(user_info["パスワード"]).replace(".0", "").strip()
                        saved_status = str(user_info["ステータス"]).strip()
                        
                        if saved_pass == clean_pass:
                            if saved_status == "OK":
                                st.session_state["logged_in_facility"] = "miratech 琉球 管理センター"
                                st.session_state["is_nurse_mode"] = False
                                st.session_state["current_user_name"] = str(user_info["名前"]).strip()
                                st.session_state["is_admin"] = (str(user_info.get("権限")).strip() == "admin")
                                
                                write_log(st.session_state["current_user_name"], "ログインしました")
                                st.rerun()
                                return True
                            else:
                                st.warning("⏳ 現在、管理者の承認待ちです。許可が出るまでお待ちください。")
                        else:
                            st.error("❌ パスワードが違います。")
                    else:
                        st.error("❌ ユーザーIDが見つかりません。新規申請を行ってください。")
                except Exception as e:
                    st.error(f"データベース接続エラー: スプレッドシートに「ユーザー」シートがあるか確認してください。({e})")

    with tab2:
        st.write("初めて利用される方は、こちらから利用申請を行ってください。")
        with st.form("register_form"):
            new_id = st.text_input("希望するユーザーID")
            new_name = st.text_input("お名前（フルネーム）")
            new_pass = st.text_input("設定するパスワード", type="password")
            
            if st.form_submit_button("利用申請を送信", use_container_width=True):
                if new_id and new_name and new_pass:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        try:
                            df_users = conn.read(worksheet="ユーザー", ttl=0).dropna(how="all")
                        except:
                            df_users = pd.DataFrame(columns=["ユーザーID", "パスワード", "名前", "ステータス", "権限"])

                        if new_id in df_users["ユーザーID"].astype(str).values:
                            st.error("⚠️ このIDは既に使われています。別のIDを指定してください。")
                        else:
                            new_user = pd.DataFrame([{
                                "ユーザーID": new_id,
                                "パスワード": new_pass,
                                "名前": new_name,
                                "ステータス": "未承認",
                                "権限": "user"
                            }])
                            updated_users = pd.concat([df_users, new_user], ignore_index=True)
                            conn.update(worksheet="ユーザー", data=updated_users)
                            write_log(new_name, f"新規利用申請を行いました (ID: {new_id})")
                            st.success(f"✅ {new_name} さんの申請を受け付けました！管理者の承認をお待ちください。")
                    except Exception as e:
                        st.error(f"登録エラー: {e}")
                else:
                    st.error("すべての項目を入力してください。")

    return False

if not check_auth():
    st.stop()

# --- ログイン後の変数 ---
facility_name = st.session_state["logged_in_facility"]
query_params = st.query_params
url_me_no = query_params.get("me_no", "")
categories_list = ["輸液ポンプ", "シリンジポンプ", "保育器", "分娩監視装置", "人工呼吸器", "透視装置","無影灯"]

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
                symptoms = []
                if err_power: symptoms.append("電源不良")
                if err_error: symptoms.append("エラー表示")
                if err_alarm: symptoms.append("アラーム")
                if err_drop: symptoms.append("落下・破損")
                
                symptom_str = "、".join(symptoms)
                if rep_detail:
                    if symptom_str:
                        symptom_str += f" (詳細: {rep_detail})"
                    else:
                        symptom_str = f"その他 (詳細: {rep_detail})"
                elif not symptom_str:
                    symptom_str = "記載なし"

                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    target_sheet = "故障報告"
                    try:
                        existing_data = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all")
                    except Exception:
                        existing_data = pd.DataFrame(columns=["報告日", "発生日", "ME No.", "機種", "報告者", "部署", "症状", "対応状況"])
                    
                    new_report = pd.DataFrame([{
                        "報告日": str(date.today()),
                        "発生日": str(rep_date),
                        "ME No.": url_me_no,
                        "機種": "不明な機器",
                        "報告者": rep_name,
                        "部署": rep_dept,
                        "症状": symptom_str,
                        "対応状況": "未対応"
                    }])
                    
                    updated_df = pd.concat([existing_data, new_report], ignore_index=True)
                    conn.update(worksheet=target_sheet, data=updated_df)
                    
                    # ログにも記録
                    write_log(f"現場({rep_name})", f"{url_me_no} の故障報告を送信")
                    
                    st.balloons()
                    st.success("✅ 報告を受け付けました。ご協力ありがとうございます。")
                except Exception as e:
                    st.error(f"保存エラー: {e}")

    else:
        st.error("⚠️ 機器情報が読み取れません。QRコードをもう一度スキャンしてください。")
        
    if st.button("管理者用ログインへ"):
        write_log(st.session_state["current_user_name"], "ログアウト(現場モード)")
        st.session_state["logged_in_facility"] = None
        st.session_state["is_nurse_mode"] = False
        st.session_state["current_user_name"] = None
        st.rerun()
    st.stop()

# ==========================================
# 👨‍🔧 【ルートB】管理者・エンジニア モード
# ==========================================
st.sidebar.success(f"👤 ログイン中: {st.session_state.get('current_user_name', '不明')}")
if st.sidebar.button("ログアウト"):
    write_log(st.session_state["current_user_name"], "ログアウトしました")
    st.session_state["logged_in_facility"] = None
    st.session_state["current_user_name"] = None
    st.rerun()

st.markdown(f"### 🏢 {facility_name}")
st.title("医療機器点検・管理")

# 管理者のみ「ユーザー管理」タブを表示
tab_names = ["📝 点検入力", "📁 マスター", "🔍 機器カルテ・実績", "🔲 QR発行", "📸 AI登録"]
if st.session_state.get("is_admin"):
    tab_names.append("👥 ユーザー・ログ管理")

tabs = st.tabs(tab_names)

# ====== タブ1：入力画面 ======
with tabs[0]:
    device_category = st.selectbox("▼ 点検する機器の種類", categories_list)
    scan_model = st.session_state.get("scan_model", "")
    if scan_model:
        st.info(f"💡 AIが読み取った型式: **{scan_model}**")

    if device_category == "輸液ポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-131A"])
    elif device_category == "シリンジポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-381", "TE-371", "TE-351", "TE-331", "その他"])
    elif device_category == "保育器":
        incubator_type = st.radio("▼ 保育器のタイプ", ["閉鎖式", "開放型"])
        device_model = st.selectbox("▼ 型式", ["V-2100G", "V85", "その他"]) if incubator_type == "閉鎖式" else st.selectbox("▼ 型式", ["V-505", "103HE", "その他"])
    else:
        device_model = st.text_input("▼ 型式を入力してください")

    st.markdown("---")
    
    # ★ ここがポイント：フォームの外に点検区分を出すことで、選んだ瞬間に画面が切り替わる
    check_type = st.radio("⚙️ 点検区分", ["院内・ME点検", "メーカー点検", "メーカー修理・校正", "その他外部委託"], horizontal=True)
    
    with st.form("check_form"):
        col_form1, col_form2 = st.columns(2)
        with col_form1: check_date = st.date_input("作業日", date.today())
        with col_form2: me_no = st.text_input("ME No.", value=url_me_no, placeholder="例: Y0001")
        
        default_sn = st.session_state.get("scan_sn", "")
        serial_no = st.text_input("製造番号 (S/N)", value=default_sn, placeholder="例: 12345678")
        
        # エラー防止用の変数初期化
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
        exterior_result = "異常なし"
        detail_result = ""

        # ★ 院内点検の時だけ細かいチェックリストを表示する
        if check_type == "院内・ME点検":
            st.write(f"### 📋 【{device_category} : {device_model}】専用チェック")
            
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
        else:
            # ★ 業者対応の場合はメッセージだけ出して省略する
            st.info("💡 メーカーや外部業者の対応です。細かいチェック入力は省略されます。一番下の「備考・報告欄」に対応内容や報告書No.を記載してください。")

        st.markdown("---")
        
        # 実施者名も、業者対応なら業者名を入れてもらえるように案内
        inspector_label = "実施者（自社名、またはメーカー・業者名）" if check_type != "院内・ME点検" else "実施者"
        inspector = st.text_input(inspector_label, value=st.session_state.get("current_user_name", ""))
        result = st.radio("総合評価", ["使用可", "メーカー修理", "廃棄"], horizontal=True) 
        memo = st.text_area("備考・報告欄", placeholder="メーカーの作業報告書No.や、交換部品、対応内容などを記載してください")
        
        submitted = st.form_submit_button("スプレッドシートに保存")

    if submitted:
        if not me_no:
            st.warning("⚠️ ME No.を入力してください")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                target_sheet = "点検履歴"
                try:
                    existing_data = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all")
                except Exception:
                    existing_data = pd.DataFrame(columns=["点検日", "ME No.", "カテゴリ", "製造番号", "製造年", "機種", "実施者", "判定", "詳細データ", "備考"])
                
                details_list = [f"【{check_type}】"]
                
                # ★ 保存時も院内点検の時だけ詳細テキストを組む
                if check_type == "院内・ME点検":
                    if device_category == "輸液ポンプ":
                        details_list.append(f"汚れ破損:{'〇' if chk_e1 else '×'}, クランプ動作:{'〇' if chk_e3 else '×'}, 流量精度:{flow_acc}ml, 閉塞圧:{occ_press}kpa")
                    elif device_category == "シリンジポンプ":
                        details_list.append(f"汚れ破損:{'〇' if chk_es1 else '×'}, クランプ動作:{'〇' if chk_es3 else '×'}, 流量精度:{flow_acc}ml, 閉塞圧:{occ_press}kpa")
                    elif device_category == "保育器":
                        if "閉鎖式" in incubator_type:
                            c_chk_str = ", ".join([f"{k}:{'〇' if v else '×'}" for k, v in inc_c_checks.items()])
                            details_list.append(f"閉鎖式 [{c_chk_str}, 表示温度:{inc_temp_disp}℃, 測定温度:{inc_temp_meas}℃]")
                        else:
                            o_chk_str = ", ".join([f"{k}:{'〇' if v else '×'}" for k, v in inc_o_checks.items()])
                            details_list.append(f"開放型 [{o_chk_str}]")
                    else:
                        details_list.append(f"外装:{exterior_result}, 精度:{detail_result}")
                else:
                    details_list.append("詳細は備考欄またはメーカー報告書を参照")
                
                detail_text = " / ".join(details_list)

                data_dict = {
                    "点検日": str(check_date), 
                    "ME No.": me_no, 
                    "カテゴリ": device_category,
                    "製造番号": serial_no, 
                    "製造年": st.session_state.get("scan_year", ""), 
                    "機種": f"{device_category}({device_model})", 
                    "実施者": inspector, 
                    "判定": result, 
                    "詳細データ": detail_text,
                    "備考": memo
                }

                new_data = pd.DataFrame([data_dict])
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet=target_sheet, data=updated_df)
                
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
                    "最終判定": f"{result}({check_type})",
                    "最終実施者": inspector
                }])

                if not master_df.empty and "ME No." in master_df.columns:
                    master_df = master_df[master_df["ME No."].astype(str) != str(me_no)]
                
                updated_master_df = pd.concat([master_df, new_master_entry], ignore_index=True)
                conn.update(worksheet=master_sheet, data=updated_master_df)
                
                write_log(inspector, f"{me_no} の点検データを統合保存({check_type})")
                
                st.balloons()
                st.success(f"✅ {me_no} の点検記録と、機器マスター台帳の更新が完了しました！")

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
                
                b64 = base64.b64encode(byte_im).decode()
                html_img = f'''
                <a href="data:image/png;base64,{b64}" download="QR_{me_no}.png">
                    <img src="data:image/png;base64,{b64}" width="150" style="border: 2px solid #eee; padding: 10px; border-radius: 10px; background-color: white;">
                </a>
                <br>
                <p style="font-size: 14px; color: gray;">👆 QRコードを<b>タップ（クリック）</b>すると直接ダウンロードされます。<br>スマホの場合は<b>長押しして「画像を保存」</b>も可能です。</p>
                '''
                st.markdown(html_img, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"エラー: {e}")

# ====== タブ2：マスター ======
with tabs[1]:
    st.subheader("🏥 機器マスター")
    view_cat_master = st.selectbox("📂 読み込むシートを選択", ["機器マスター", "点検履歴", "故障報告"], key="master_cat")
    if st.button("🔄 台帳を更新する"):
        st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=view_cat_master, ttl=0).dropna(how="all")
        if df.empty:
            st.info(f"「{view_cat_master}」シートにはまだデータがありません。")
        else:
            st.dataframe(df, hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"🚨 接続エラー: {e}")

# ====== タブ3：機器カルテ・実績 ======
with tabs[2]:
    st.subheader("🔍 機器カルテ照合 ＆ 日次実績")
    
    if st.button("🔄 最新のデータを読み込む", key="refresh_history_tab"):
        st.cache_data.clear()
        
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        try:
            df_master = conn.read(worksheet="機器マスター", ttl=0).dropna(how="all")
        except Exception:
            df_master = pd.DataFrame()
            
        try:
            df_history = conn.read(worksheet="点検履歴", ttl=0).dropna(how="all")
        except Exception:
            df_history = pd.DataFrame()

        sub_tab1, sub_tab2 = st.tabs(["📋 機器カルテ（ワンタッチ照合）", "📈 日次点検実績（グラフ）"])

        with sub_tab1:
            st.write("👇 下の一覧表から、詳細を見たい機器の行をタップ（クリック）してください")
            if not df_master.empty:
                selection_event = st.dataframe(
                    df_master,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )
                
                if len(selection_event.selection.rows) > 0:
                    idx = selection_event.selection.rows[0]
                    target_me = str(df_master.iloc[idx].get("ME No.", ""))
                    model_name = df_master.iloc[idx].get("機種", "不明な機器")
                    
                    st.markdown("---")
                    st.markdown(f"<h3 style='color: #2e86de;'>📱 {model_name} (ME No: {target_me}) のカルテ</h3>", unsafe_allow_html=True)
                    
                    if not df_history.empty and "ME No." in df_history.columns:
                        hist_df = df_history[df_history["ME No."].astype(str) == target_me].iloc[::-1]
                        
                        if not hist_df.empty:
                            st.write("#### 📝 過去の点検・修理履歴")
                            st.dataframe(hist_df, use_container_width=True, hide_index=True)
                            
                            last_date = hist_df.iloc[0].get("点検日", "-")
                            last_result = hist_df.iloc[0].get("判定", "-")
                            st.success(f"📌 最新の点検日: {last_date} ／ 判定: {last_result}")
                        else:
                            st.info("この機器の点検・修理履歴はありません。")
                    else:
                        st.info("点検履歴データがありません。")
            else:
                st.info("💡 機器マスターにまだデータがありません。")

        with sub_tab2:
            if not df_history.empty and "点検日" in df_history.columns:
                df_history["点検日"] = df_history["点検日"].astype(str)
                st.markdown("#### 📈 日別点検件数の推移")
                
                daily_counts = df_history["点検日"].value_counts().reset_index()
                daily_counts.columns = ["点検日", "点検件数（台）"]
                daily_counts = daily_counts.sort_values("点検日")
                
                col_graph, col_table = st.columns([2, 1])
                
                with col_graph:
                    st.write("▼ 日別の点検台数グラフ")
                    st.bar_chart(daily_counts, x="点検日", y="点検件数（台）", color="#2e86de")
                    
                with col_table:
                    st.write("▼ 日付ごとの合計台数")
                    st.dataframe(daily_counts.iloc[::-1], use_container_width=True, hide_index=True)

                st.markdown("##### 📅 特定の日の点検内訳を確認する")
                target_date = st.date_input("確認したい日付を選択", date.today())
                
                day_detail_df = df_history[df_history["点検日"] == str(target_date)]
                if not day_detail_df.empty:
                    st.success(f"📌 {target_date} は 合計 **{len(day_detail_df)} 台** の点検が完了しています。")
                    st.dataframe(day_detail_df, use_container_width=True, hide_index=True)
                else:
                    st.info(f"選択された日付（{target_date}）の点検データはありません。")
            else:
                st.info("💡 集計できる点検履歴データがまだありません。")

    except Exception as e:
        st.error(f"🚨 システムエラー: スプレッドシートの設定等を確認してください。詳細: {e}")

# ====== タブ4：QRコード発行機能 ======
with tabs[3]:
    st.subheader("🔲 機器用QRコードの作成")
    st.write("対象の「ME No.」を入力すると、機器に貼り付ける用のQRコードが作成されます。")
    
    # 修正ポイント：secretsに登録されている一番最初の施設情報を強制的に取得する
    auto_fid = ""
    auto_token = ""
    for key in st.secrets.keys():
        if isinstance(st.secrets[key], dict) and "id_code" in st.secrets[key]:
            auto_fid = st.secrets[key]["id_code"]
            auto_token = st.secrets[key]["token"]
            break # 1つ見つけたらループ終了

    target_qr_me = st.text_input("🔤 QRコードを作りたい「ME No.」を入力", placeholder="例: Y0001")
    
    if st.button("QRコードを作成する"):
        if not target_qr_me:
            st.warning("⚠️ ME No.を入力してください。")
        elif not auto_fid or not auto_token:
            st.error("⚠️ システムエラー：secretsファイルに施設の認証情報（id_code, token）が見つかりません。")
        else:
            # URLの組み立て
            if APP_URL.endswith("/"):
                final_url = f"{APP_URL}?fid={auto_fid}&key={auto_token}&me_no={target_qr_me}"
            else:
                final_url = f"{APP_URL}/?fid={auto_fid}&key={auto_token}&me_no={target_qr_me}"
            
            # QRコード生成
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(final_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.success(f"「{target_qr_me}」専用のQRコードができました！")
            
            b64 = base64.b64encode(byte_im).decode()
            html_img = f'''
            <a href="data:image/png;base64,{b64}" download="QR_{target_qr_me}.png">
                <img src="data:image/png;base64,{b64}" width="200" style="border: 2px solid #eee; padding: 10px; border-radius: 10px; background-color: white;">
            </a>
            <br>
            <p style="font-size: 14px; color: gray;">👆 QRコードを<b>タップ（クリック）</b>すると直接ダウンロードされます。<br>スマホの場合は<b>長押しして「画像を保存」</b>も可能です。</p>
            '''
            st.markdown(html_img, unsafe_allow_html=True)
            
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

# ====== 追加：タブ6：ユーザー・ログ管理（管理者のみ） ======
if st.session_state.get("is_admin"):
    with tabs[5]:
        st.subheader("⚙️ ユーザー承認・アクセスログ管理")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_users = conn.read(worksheet="ユーザー", ttl=0).dropna(how="all")
            
            st.markdown("#### 👤 承認待ちユーザー")
            pending_users = df_users[df_users["ステータス"] == "未承認"]
            if pending_users.empty:
                st.write("現在、承認待ちのユーザーはいません。")
            else:
                for index, row in pending_users.iterrows():
                    col_u1, col_u2 = st.columns([3, 1])
                    with col_u1:
                        st.write(f"申請者: **{row['名前']}** (ID: {row['ユーザーID']})")
                    with col_u2:
                        if st.button("✅ 承認する", key=f"approve_{row['ユーザーID']}"):
                            df_users.at[index, "ステータス"] = "OK"
                            conn.update(worksheet="ユーザー", data=df_users)
                            write_log("管理者", f"{row['名前']} のアカウントを承認")
                            st.success(f"{row['名前']} さんを承認（OK）しました！")
                            st.rerun()

            st.markdown("---")
            st.markdown("#### 📋 アクセス履歴（最新順）")
            if st.button("🔄 ログを更新"):
                st.cache_data.clear()
            
            try:
                df_logs = conn.read(worksheet="アクセスログ", ttl=0).dropna(how="all")
                if not df_logs.empty:
                    st.dataframe(df_logs.iloc[::-1], use_container_width=True, hide_index=True)
                else:
                    st.write("ログはまだありません。")
            except:
                st.write("ログシートがまだ作成されていません。")
                
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
