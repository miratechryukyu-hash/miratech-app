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
        try:
            # スプレッドシートに接続
            conn = st.connection("gsheets", type=GSheetsConnection)
            
            # ttl=0 をつけて「常に最新」を読み込み、dropna(how="all") で「空っぽの行」を無視する！
            existing_data = conn.read(worksheet="シート1", ttl=0)
            existing_data = existing_data.dropna(how="all") 
            
            # 新しいデータを作成
            new_data = pd.DataFrame([{
                "点検日": str(check_date),
                "ME No.": me_no,
                "機種": model_type,
                "実施者": inspector,
                "判定": result,
                "備考": memo
            }])
            
            # データを合体させて上書き保存
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            conn.update(worksheet="シート1", data=updated_df)
            
            # アプリの記憶（キャッシュ）をリセットしてスッキリさせる
            st.cache_data.clear()
            
            st.balloons()
            st.success("大成功！スプレッドシートの2行目を確認してください！")
        except Exception as e:
            st.error(f"エラー発生: {e}")
