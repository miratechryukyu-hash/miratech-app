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

# ==========================================
# ⚙️ 設定：ここを自分のアプリのURLに書き換えてください
# ==========================================
APP_URL = "https://あなたの実際のアプリのURL.streamlit.app"

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
st.title("医療機器点検・管理ダッシュボード")

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
        with col_form2: me_no = st.text_input("ME No.", value=url_me_no, placeholder="例: NT-001")
        
        default_sn = st.session_state.get("scan_sn", "")
        serial_no = st.text_input("製造番号 (S/N)", value=default_sn, placeholder="例: 12345678")
        
        st.write(f"### 📋 【{device_category} : {device_model}】専用チェック")
        
        chk_e1 = st.checkbox("外観・作動に異常なし", value=True)
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
                
                data_dict = {"点検日": str(check_date), "ME No.": me_no, "製造番号": serial_no, "製造年": st.session_state.get("scan_year", ""), "機種": f"{device_category}({device_model})", "実施者": inspector, "判定": result, "備考": memo}
                new_data = pd.DataFrame([data_dict])
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet=target_sheet, data=updated_df)
                
                # --- ② ✨機器マスター台帳の自動更新 ---
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
                    # すでに同じME No.があれば削除（上書きのため）
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
                
                col_qr1, col_qr2 = st.columns([1, 2])
                with col_qr1:
                    st.image(byte_im, width=150)
                with col_qr2:
                    st.write("テプラ等に印刷するためのQRコードが作成されました。")
                    st.download_button(label="📥 QRコードを保存", data=byte_im, file_name=f"QR_{me_no}.png", mime="image/png")

            except Exception as e:
                st.error(f"エラー: スプレッドシートに「機器マスター」というシートを作成してください。詳細: {e}")

# ====== タブ2：マスター ======
with tabs[1]:
    st.subheader("🏥 機器マスター")
    # ✨「機器マスター」シートを優先して読み込めるように修正
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
                # 機器マスターはそのまま表示（重複なしの最新リストとして）
                st.dataframe(df, hide_index=True, use_container_width=True)
            else:
                # 過去の履歴シートの場合は重複を弾いて表示
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
            st.image(byte_im, width=200)
            st.download_button(label="📥 このQRコードを画像として保存", data=byte_im, file_name=f"QR_{target_qr_me}.png", mime="image/png")
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
