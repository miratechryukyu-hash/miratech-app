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
st.set_page_config(page_title="miratech 医療機器管理システム", layout="centered")

# ==========================================
# 🔐 マルチテナント＆QR自動ログイン認証（金庫対応版）
# ==========================================
def check_auth():
    # 1. URLパラメータの取得（QRスキャン時など）
    query_params = st.query_params
    fid = query_params.get("fid", "")     # 施設コード（例: UMR）
    token = query_params.get("key", "")   # 秘密鍵（例: abc123xyz）
    url_me_no = query_params.get("me_no", "") # 機器番号

    # セッション状態の初期化
    if "logged_in_facility" not in st.session_state:
        st.session_state["logged_in_facility"] = None
    if "facility_key" not in st.session_state:
        st.session_state["facility_key"] = None

    # すでにログイン済みなら通過
    if st.session_state["logged_in_facility"] is not None:
        return True

    # 2. QRコード（URL）からの自動ログイン判定
    # 金庫(st.secrets)をスキャンして一致する施設を探す
    for key in st.secrets:
        # 施設データ（[uemura]など）かチェック
        if isinstance(st.secrets[key], dict) and "token" in st.secrets[key]:
            # URLのIDとトークンが一致した場合
            if fid == st.secrets[key].get("id_code") and token == st.secrets[key]["token"]:
                st.session_state["logged_in_facility"] = st.secrets[key]["name"]
                st.session_state["facility_key"] = key
                st.session_state["is_nurse_mode"] = True # QRからは自動的に現場モード
                return True

    # 3. 通常のログイン画面（手入力）
    st.warning("⚠️ miratech 琉球 医療機器管理システム")
    with st.form("login_form"):
        input_id = st.text_input("🏢 施設ID（企業コード）")
        input_pass = st.text_input("🔑 パスワード", type="password")
        submitted = st.form_submit_button("ログイン", use_container_width=True)
        
        if submitted:
            # 金庫の中を探索
            for key in st.secrets:
                if isinstance(st.secrets[key], dict) and "password" in st.secrets[key]:
                    if input_id == st.secrets[key].get("id") and input_pass == st.secrets[key]["password"]:
                        st.session_state["logged_in_facility"] = st.secrets[key]["name"]
                        st.session_state["facility_key"] = key
                        st.session_state["is_nurse_mode"] = False
                        st.rerun()
            st.error("❌ 施設IDまたはパスワードが違います。")
    return False

# 認証を通らなければここでストップ
if not check_auth():
    st.stop()

# --- ログイン成功後の変数準備 ---
facility_name = st.session_state["logged_in_facility"]
# URLから取得したME No.をセッションに保持
query_params = st.query_params
url_me_no = query_params.get("me_no", "")

# ==========================================
# 🤖 AI設定（Gemini）
# ==========================================
ai_model = None
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        ai_model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"APIキーの設定エラー: {e}")

# ==========================================
# 👩‍⚕️ 【ルートA】現場スタッフ（看護師）専用モード
# ==========================================
# QRからのアクセス、または意図的に切り替えた場合
if st.session_state.get("is_nurse_mode"):
    st.markdown(f"<h2 style='text-align: center; color: #FF4B4B;'>🚨 {facility_name}</h2>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center;'>機器トラブル報告システム</h3>", unsafe_allow_html=True)
    
    if url_me_no:
        st.success(f"📱 対象機器: **{url_me_no}**")
        
        with st.form("nurse_report_form"):
            rep_date = st.date_input("発生日", date.today())
            rep_dept = st.selectbox("あなたの部署", ["選択してください", "外来", "一般病棟", "療養病棟", "オペ室", "透析室", "その他"])
            rep_name = st.text_input("報告者名")
            
            st.write("▼ 症状（該当をチェック）")
            c1, c2 = st.columns(2)
            with c1:
                err_power = st.checkbox("🔌 電源不良")
                err_error = st.checkbox("⚠️ エラー表示")
            with c2:
                err_alarm = st.checkbox("🔔 アラーム")
                err_drop = st.checkbox("💥 落下・破損")
            
            rep_detail = st.text_area("詳細内容")
            
            if st.form_submit_button("📨 報告を送信する", type="primary", use_container_width=True):
                # ここにスプレッドシートへの保存処理（既存コードのロジック）を記述
                st.balloons()
                st.success("✅ 報告を受け付けました。ありがとうございます。")
    else:
        st.error("⚠️ 機器情報が読み取れません。QRコードを再度スキャンしてください。")
    
    if st.button("管理者用ログインへ"):
        st.session_state["logged_in_facility"] = None
        st.rerun()
    st.stop()

# ==========================================
# 👨‍🔧 【ルートB】管理者（安富さん）専用モード
# ==========================================
st.sidebar.title(f"🏢 {facility_name}")
show_sim = st.sidebar.checkbox("💰 営業用シミュレーターを表示")

st.title("医療機器点検・管理ダッシュボード")

# ここに以前の「タブ機能」や「スプレッドシート連携」をすべて配置します
# (タブのコードや各機能は以前のものと全く同じものが使えます)

tabs = st.tabs(["📝 点検入力", "📁 マスター", "🔍 全履歴", "🔲 QR発行", "📸 AI登録", "💰 コストシミュ"] if show_sim else ["📝 点検入力", "📁 マスター", "🔍 全履歴", "🔲 QR発行", "📸 AI登録"])

with tabs[0]:
    st.write(f"### {facility_name} の点検入力")
    # 以下、点検入力のフォーム...
