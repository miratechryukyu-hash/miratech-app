import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

st.title("🏥 医療機器点検アプリ (miratech)")

# 【新機能】タブを作成して画面を2つに分けます
tab1, tab2 = st.tabs(["📝 点検の入力", "🔍 過去の履歴確認"])

# ====== タブ1：入力画面 ======
with tab1:
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
            st.warning("⚠️ ME No.を入力してください")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                existing_data = conn.read(worksheet="シート1", ttl=0).dropna(how="all") 
                
                is_duplicate = False
                if "ME No." in existing_data.columns and "点検日" in existing_data.columns:
                    is_duplicate = ((existing_data["ME No."] == me_no) & (existing_data["点検日"].astype(str) == str(check_date))).any()
                
                if is_duplicate:
                    st.error(f"🚨 ちょっと待って！「{me_no}」は本日（{check_date}）すでに点検済みです！大丈夫ですか？")
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

# ====== タブ2：履歴確認画面 ======
with tab2:
    st.subheader("📊 スプレッドシートのデータを確認")
    
    # データを読み込むボタン（常に最新を見るため）
    if st.button("🔄 最新のデータを読み込む"):
        st.cache_data.clear()
        
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # データを取得
        df = conn.read(worksheet="シート1", ttl=0).dropna(how="all")
        
        if df.empty:
            st.info("まだ点検記録がありません。")
        else:
            # 【新機能】ME No. での検索バー
            search_query = st.text_input("🔍 探したい「ME No.」を入力してください")
            
            # 検索文字が入力されていたら、その文字を含む行だけを絞り込む
            if search_query:
                # fillna("") は空欄でエラーになるのを防ぐ処理です
                df = df[df["ME No."].astype(str).fillna("").str.contains(search_query, case=False)]
                st.write(f"「{search_query}」の検索結果: {len(df)} 件")
            
            # データ表を表示する（最新のものが上に来るように逆順にする）
            st.dataframe(df.iloc[::-1], use_container_width=True)
            
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
