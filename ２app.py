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
        if not me_no:
            st.error("ME No.を入力してください")
        else:
            try:
                # スプレッドシート接続
                conn = st.connection("gsheets", type=GSheetsConnection)
                
                # 新しいデータ作成
                new_data = pd.DataFrame([{
                    "点検日": str(check_date),
                    "ME No.": me_no,
                    "機種": model_type,
                    "実施者": inspector,
                    "判定": result,
                    "備考": memo
                }])
                
                # 既存のデータを取得して追記
                existing_data = conn.read(worksheet="シート1", usecols=[0,1,2,3,4,5], ttl=0)
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                
                # 保存実行
                conn.update(worksheet="シート1", data=updated_df)
                
                st.balloons()
                st.success("スプレッドシートに書き込みました！")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
