import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

st.title("🏥 医療機器点検入力 (miratech)")

# 入力フォーム
with st.form("check_form"):
    check_date = st.date_input("点検日", date.today())
    me_no = st.text_input("ME No.", placeholder="例: NT-001")
    model_type = st.selectbox("機種", ["人工呼吸器", "輸液ポンプ", "シリンジポンプ", "その他"])
    inspector = st.text_input("実施者", value="安富")
    result = st.radio("判定", ["合格", "不合格"], horizontal=True)
    memo = st.text_area("備考")
    
    submitted = st.form_submit_button("スプレッドシートに保存")

if submitted:
    # ME No.が空っぽの時のエラー
    if not me_no:
        st.warning("⚠️ ME No.を入力してください")
    else:
        try:
            # スプレッドシートに接続して読み込み
            conn = st.connection("gsheets", type=GSheetsConnection)
            existing_data = conn.read(worksheet="シート1", ttl=0)
            existing_data = existing_data.dropna(how="all") 
            
            # 【新機能】重複チェック（同じ日・同じME No.がないか確認）
            is_duplicate = False
            if "ME No." in existing_data.columns and "点検日" in existing_data.columns:
                # シートの日付と入力された日付、ME No.を比較
                is_duplicate = ((existing_data["ME No."] == me_no) & (existing_data["点検日"].astype(str) == str(check_date))).any()
            
            # 重複していたらエラーを出して「保存させない」
            if is_duplicate:
                st.error(f"🚨 ちょっと待って！「{me_no}」は本日（{check_date}）すでに点検済みです！大丈夫ですか？")
            
            # 重複していなければ、今まで通り保存！
            else:
                new_data = pd.DataFrame([{
                    "点検日": str(check_date),
                    "ME No.": me_no,
                    "機種": model_type,
                    "実施者": inspector,
                    "判定": result,
                    "備考": memo
                }])
                
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet="シート1", data=updated_df)
                
                st.cache_data.clear()
                st.balloons()
                st.success(f"大成功！{me_no} の点検データを記録しました！")
                
        except Exception as e:
            st.error(f"エラー発生: {e}")
