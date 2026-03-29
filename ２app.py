import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

st.title("🏥 医療機器点検アプリ (miratech)")

tab1, tab2 = st.tabs(["📝 点検の入力", "🔍 過去の履歴確認"])

# ====== タブ1：入力画面 ======
with tab1:
    model_type = st.selectbox("▼ 点検する機種を選択してください", ["輸液ポンプ", "シリンジポンプ", "人工呼吸器", "その他"])
    
    st.markdown("---")

    with st.form("check_form"):
        check_date = st.date_input("点検日", date.today())
        me_no = st.text_input("ME No.", placeholder="例: NT-001")
        
        st.write(f"### 📋 【{model_type}】専用チェック項目")
        
        # ＝＝＝ 輸液ポンプが選ばれた時の画面 ＝＝＝
        if model_type == "輸液ポンプ":
            st.write("**① 外観・作動・警報チェック**")
            col1, col2, col3 = st.columns(3)
            with col1: chk_app = st.checkbox("外観点検 OK", value=True)
            with col2: chk_op = st.checkbox("作動点検 OK", value=True)
            with col3: chk_alm = st.checkbox("各種警報 OK", value=True)
            
            st.write("**② 数値・精度チェック (TE-281等)**")
            col_num1, col_num2 = st.columns(2)
            with col_num1:
                flow_acc = st.number_input("流量精度 (18~22ml)", value=20.0, step=0.1)
            with col_num2:
                occ_press = st.number_input("下部閉塞検出 (30~90kpa)", value=50.0, step=1.0)
            
            battery = st.number_input("内蔵バッテリ (750以上)", value=800, step=10)
            
            exterior_result = "異常なし" if (chk_app and chk_op and chk_alm) else "異常あり"
            detail_result = f"外観:{'OK' if chk_app else 'NG'}, 作動:{'OK' if chk_op else 'NG'}, 警報:{'OK' if chk_alm else 'NG'} | 流量:{flow_acc}ml, 閉塞:{occ_press}kpa, バッテリ:{battery}"

        # ＝＝＝ シリンジポンプが選ばれた時の画面 ＝＝＝
        elif model_type == "シリンジポンプ":
            st.write("**① 外観・作動・警報チェック**")
            col1, col2 = st.columns(2)
            with col1: chk_app_s = st.checkbox("外観・プランジャ動作 OK", value=True)
            with col2: chk_alm_s = st.checkbox("シリンジ外れ・残量警報 OK", value=True)
            
            st.write("**② 数値・精度チェック**")
            flow_acc_s = st.number_input("流量精度チェック (ml)", value=10.0, step=0.1)
            
            exterior_result = "異常なし" if (chk_app_s and chk_alm_s) else "異常あり"
            detail_result = f"外観/動作:{'OK' if chk_app_s else 'NG'}, 警報:{'OK' if chk_alm_s else 'NG'} | 流量:{flow_acc_s}ml"

        # ＝＝＝ 人工呼吸器・その他が選ばれた時の画面 ＝＝＝
        else:
            exterior_result = st.radio("外装点検", ["異常なし", "異常あり"], horizontal=True)
            detail_result = st.text_input("精度チェック（測定値など）", placeholder="例: 換気量 500ml")

        st.markdown("---")
        inspector = st.text_input("実施者", value="安富")
        result = st.radio("総合評価", ["使用可", "メーカー修理", "廃棄"], horizontal=True) 
        memo = st.text_area("備考・報告欄")
        
        submitted = st.form_submit_button("スプレッドシートに保存")

    # ＝＝＝ 保存処理 ＝＝＝
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
                        "外装点検": exterior_result,    
                        "精度チェック": detail_result, 
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
    
    if st.button("🔄 最新のデータを読み込む"):
        st.cache_data.clear()
        
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="シート1", ttl=0).dropna(how="all")
        
        if df.empty:
            st.info("まだ点検記録がありません。")
        else:
            search_query = st.text_input("🔍 探したい「ME No.」を入力してください")
            if search_query:
                df = df[df["ME No."].astype(str).fillna("").str.contains(search_query, case=False)]
                st.write(f"「{search_query}」の検索結果: {len(df)} 件")
            
            st.dataframe(df.iloc[::-1], use_container_width=True)
            
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")
