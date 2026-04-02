import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

# ==========================================
# 💡【新機能】印刷マジック＆ダークモード対策CSS
# ==========================================
st.markdown("""
<style>
/* 画面上の証明書デザイン（ダークモードでも絶対に白背景・黒文字にする） */
.cert-box {
    background-color: #ffffff !important;
    color: #000000 !important;
    padding: 30px;
    border: 1px solid #ddd;
    border-radius: 8px;
}
.cert-box * {
    color: #000000 !important;
}
.cert-box th {
    background-color: #f4f4f4 !important;
}

/* 🖨️ 印刷ボタンを押した時だけ発動する魔法 */
@media print {
    /* Streamlitのヘッダー、サイドバー、余計なメニューを全て消す */
    header, footer, [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="stToolbar"] {
        display: none !important;
    }
    /* タブの切り替えボタンを消す */
    [data-testid="stTabs"] > div:first-child {
        display: none !important;
    }
    /* 機種を選ぶドロップダウン（Selectbox）を消す */
    [data-testid="stSelectbox"] {
        display: none !important;
    }
    /* 画面の余白をゼロにして、A4用紙全体を使う */
    .main .block-container {
        max-width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* 枠線を消して、本物の紙のように見せる */
    .cert-box {
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    /* 色（緑や赤の枠線、グレーの背景）を印刷に反映させる */
    * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
}
</style>
""", unsafe_allow_html=True)

query_params = st.query_params
url_me_no = query_params.get("me_no", "")

st.title("🏥 医療機器点検アプリ (miratech)")

# ==========================================
# 💡 QRダッシュボード
# ==========================================
if url_me_no:
    st.success(f"📱 対象機器を認識しました: **{url_me_no}**")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_all = conn.read(worksheet="シート1", ttl=0).dropna(how="all")
        if "ME No." in df_all.columns:
            df_device = df_all[df_all["ME No."].astype(str) == url_me_no]
            if not df_device.empty:
                latest_data = df_device.iloc[-1]
                dash_tab1, dash_tab2 = st.tabs(["🏥 機器の基本情報", "📝 過去の点検履歴"])
                with dash_tab1:
                    st.write("### 📊 機器マスターデータ")
                    col1, col2 = st.columns(2)
                    col1.metric("ME No.", str(latest_data.get("ME No.", "-")))
                    col2.metric("機種", str(latest_data.get("機種", "-")))
                    col3, col4 = st.columns(2)
                    col3.metric("製造番号 (S/N)", str(latest_data.get("製造番号", "未登録")))
                    col4.metric("これまでの点検回数", f"{len(df_device)} 回")
                with dash_tab2:
                    st.write("### 🩺 最新＆過去の点検ステータス")
                    st.dataframe(df_device.iloc[::-1], use_container_width=True, hide_index=True)
            else:
                st.info("💡 この機器の過去の点検記録はまだありません。（新規登録）")
    except Exception as e:
        st.warning("データの読み込みに失敗しました。")
    st.markdown("---")


# ==========================================
# 💡 アプリ本体
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 点検入力", "📁 マスター", "🔍 全履歴", "📄 レポート出力"])

# ====== タブ1：入力画面 ======
with tab1:
    device_category = st.selectbox("▼ 点検する機器の種類", ["輸液ポンプ", "シリンジポンプ", "人工呼吸器", "その他"])
    if device_category == "輸液ポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-281", "TE-261", "TE-171", "TE-161", "TE-LM830", "OT-707", "OT-818G", "AS-800", "その他"])
    elif device_category == "シリンジポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-381", "TE-371", "TE-351", "TE-331", "その他"])
    else:
        device_model = st.text_input("▼ 型式を入力してください")
    
    st.markdown("---")

    with st.form("check_form"):
        col_form1, col_form2 = st.columns(2)
        with col_form1:
            check_date = st.date_input("点検日", date.today())
        with col_form2:
            me_no = st.text_input("ME No.", value=url_me_no, placeholder="例: NT-001")
        
        serial_no = st.text_input("製造番号 (S/N)", placeholder="例: 12345678")
        st.write(f"### 📋 【{device_category} : {device_model}】専用チェック")
        
        if device_category == "輸液ポンプ":
            with st.expander("🔍 ① 外観・作動・警報の詳細チェック（タップで開く）", expanded=True):
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
            with col_num2:
                occ_press = st.number_input("閉塞検出圧 (kpa/mmHg)", value=50.0, step=1.0)
            battery = st.number_input("内蔵バッテリ (内部数値など)", value=800, step=10)
            ext_all_ok = all([chk_e1, chk_e2, chk_e3, chk_e4, chk_e5, chk_e6, chk_e7])
            alm_all_ok = all([chk_a1, chk_a2, chk_a3, chk_a4])
            exterior_result = "異常なし" if (ext_all_ok and alm_all_ok) else "異常あり"
            detail_result = f"外観/警報:{'OK' if (ext_all_ok and alm_all_ok) else 'NG'} | 流量:{flow_acc}ml, 閉塞:{occ_press}, バッテリ:{battery}"

        elif device_category == "シリンジポンプ":
            with st.expander("🔍 ① 外観・作動・警報の詳細チェック（タップで開く）", expanded=True):
                st.write("**【外観・作動点検】**")
                col1, col2 = st.columns(2)
                with col1:
                    chk_es1 = st.checkbox("本体の汚れ・破損なし", value=True)
                    chk_es2 = st.checkbox("ポールクランプ用ネジ穴", value=True)
                    chk_es3 = st.checkbox("シリンジクランプの動作", value=True)
                with col2:
                    chk_es4 = st.checkbox("スライダー・クラッチ動作", value=True)
                    chk_es5 = st.checkbox("AC・DC切り替え", value=True)
                    chk_es6 = st.checkbox("セルフチェック・LED", value=True)

                st.write("**【各種警報点検】**")
                col3, col4 = st.columns(2)
                with col3:
                    chk_as1 = st.checkbox("シリンジ外れ・サイズ認識", value=True)
                    chk_as2 = st.checkbox("押し子外れ / クラッチ外れ", value=True)
                    chk_as3 = st.checkbox("残量 / 閉塞警報 / バッテリ", value=True)
                with col4:
                    chk_as4 = st.checkbox("開始忘れ / 流量設定無し", value=True)
                    chk_as5 = st.checkbox("消音 / 再警報", value=True)
            
            st.write("**② 数値・精度チェック**")
            col_num1_s, col_num2_s = st.columns(2)
            with col_num1_s:
                flow_acc_s = st.number_input("流量精度チェック (ml)", value=10.0, step=0.1)
            with col_num2_s:
                occ_press_s = st.number_input("閉塞検出圧 (kpa/mmHg)", value=80.0, step=1.0)
            battery_s = st.number_input("内蔵バッテリ (内部数値など)", value=0.0, step=0.1)
            ext_all_ok_s = all([chk_es1, chk_es2, chk_es3, chk_es4, chk_es5, chk_es6])
            alm_all_ok_s = all([chk_as1, chk_as2, chk_as3, chk_as4, chk_as5])
            exterior_result = "異常なし" if (ext_all_ok_s and alm_all_ok_s) else "異常あり"
            detail_result = f"外観/警報:{'OK' if (ext_all_ok_s and alm_all_ok_s) else 'NG'} | 流量:{flow_acc_s}ml, 閉塞:{occ_press_s}, バッテリ:{battery_s}"

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
                existing_data = conn.read(worksheet="シート1", ttl=0).dropna(how="all") 
                is_duplicate = False
                if "ME No." in existing_data.columns and "点検日" in existing_data.columns:
                    is_duplicate = ((existing_data["ME No."] == me_no) & (existing_data["点検日"].astype(str) == str(check_date))).any()
                if is_duplicate:
                    st.error(f"🚨 ちょっと待って！「{me_no}」は本日（{check_date}）すでに点検済みです！大丈夫ですか？")
                else:
                    combined_model = f"{device_category} ({device_model})"
                    new_data = pd.DataFrame([{
                        "点検日": str(check_date),
                        "ME No.": me_no,
                        "機種": combined_model,
                        "製造番号": serial_no,
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

# ====== タブ2：機器マスター一覧 ======
with tab2:
    st.subheader("🏥 機器カテゴリ別の一覧")
    if st.button("🔄 台帳を更新する", key="master_update"):
        st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="シート1", ttl=0).dropna(how="all")
        if df.empty or "ME No." not in df.columns:
            st.info("まだ機器の登録データがありません。")
        else:
            df_master = df.drop_duplicates(subset=["ME No."], keep="last")
            categories = df_master["機種"].unique()
            for cat in categories:
                with st.expander(f"📁 {cat} の登録一覧", expanded=True):
                    df_cat = df_master[df_master["機種"] == cat]
                    display_cols = ["ME No.", "製造番号", "点検日", "判定"]
                    existing_cols = [col for col in display_cols if col in df_cat.columns]
                    st.dataframe(df_cat[existing_cols].rename(columns={"点検日": "最終点検日"}), hide_index=True, use_container_width=True)
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")

# ====== タブ3：全履歴確認画面 ======
with tab3:
    st.subheader("📊 すべての点検履歴データ")
    if st.button("🔄 最新のデータを読み込む", key="history_update"):
        st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="シート1", ttl=0).dropna(how="all")
        if df.empty:
            st.info("まだ点検記録がありません。")
        else:
            search_query = st.text_input("🔍 探したい「ME No.」を入力してください", value=url_me_no)
            if search_query:
                df = df[df["ME No."].astype(str).fillna("").str.contains(search_query, case=False)]
                st.write(f"「{search_query}」の検索結果: {len(df)} 件")
            st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"データの読み込みに失敗しました: {e}")

# ==========================================
# 💡【完成版】タブ4：そのまま印刷できる証明書画面
# ==========================================
with tab4:
    st.subheader("📄 保守点検済証 の発行")
    st.info("💡 **印刷方法:** 下に証明書が表示されたら、iPhone画面下の **「共有（↑）」ボタンから「プリント」** を選んでください。余計なメニューが自動で消えて、綺麗に印刷されます！")
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="シート1", ttl=0).dropna(how="all")
        
        if not df.empty and "ME No." in df.columns:
            target_me = st.selectbox("📝 出力する「ME No.」を選んでください", df["ME No."].unique())
            
            if target_me:
                df_target = df[df["ME No."] == target_me]
                latest_record = df_target.iloc[-1]
                
                result_text = latest_record.get('判定', '-')
                result_color = "#28a745" if result_text == "使用可" else "#dc3545"
                exterior_text = latest_record.get('外装点検', '-')
                exterior_color = "#28a745" if "異常なし" in exterior_text else "#dc3545"
                
                # ▼ ダークモードの影響を受けない「真っ白」な証明書デザイン ▼
                st.markdown(f"""
                <div class="cert-box">
                    <div style="text-align: right; font-size: 14px; margin-bottom: 20px; line-height: 1.6;">
                        発行日： {date.today().strftime('%Y年%m月%d日')}<br>
                        点検実施： <b>miratech Ryukyu</b><br>
                        臨床工学技士： <b>{latest_record.get('実施者', '安富 翔')}</b>
                    </div>
                    
                    <h2 style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 30px; letter-spacing: 2px; border-bottom: 2px solid #000; padding-bottom: 10px;">
                        医療機器 保守点検済証
                    </h2>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 15px;">
                        <tr>
                            <th style="border: 1px solid #999; padding: 10px; width: 20%; text-align: left;">管理番号 (ME No.)</th>
                            <td style="border: 1px solid #999; padding: 10px; width: 30%;"><b>{latest_record.get('ME No.', '-')}</b></td>
                            <th style="border: 1px solid #999; padding: 10px; width: 20%; text-align: left;">点検日</th>
                            <td style="border: 1px solid #999; padding: 10px; width: 30%;">{latest_record.get('点検日', '-')}</td>
                        </tr>
                        <tr>
                            <th style="border: 1px solid #999; padding: 10px; text-align: left;">機種名</th>
                            <td style="border: 1px solid #999; padding: 10px;">{latest_record.get('機種', '-')}</td>
                            <th style="border: 1px solid #999; padding: 10px; text-align: left;">製造番号 (S/N)</th>
                            <td style="border: 1px solid #999; padding: 10px;">{latest_record.get('製造番号', '未登録')}</td>
                        </tr>
                    </table>

                    <h3 style="font-size: 18px; border-left: 5px solid #0056b3; padding-left: 10px; margin-bottom: 15px;">■ 点検結果詳細</h3>
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px;">
                        <tr>
                            <th style="border: 1px solid #999; padding: 10px; text-align: left; width: 30%;">点検項目</th>
                            <th style="border: 1px solid #999; padding: 10px; text-align: center; width: 35%;">判定 / 測定値</th>
                            <th style="border: 1px solid #999; padding: 10px; text-align: left; width: 35%;">許容値・基準</th>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #999; padding: 10px;"><b>外観・作動・各種警報</b></td>
                            <td style="border: 1px solid #999; padding: 10px; text-align: center; font-weight: bold; color: {exterior_color} !important;">{exterior_text}</td>
                            <td style="border: 1px solid #999; padding: 10px; font-size: 12px;">汚れ・破損なきこと<br>警報が正常に作動すること</td>
                        </tr>
                        <tr>
                            <td style="border: 1px solid #999; padding: 10px;"><b>精度・数値チェック</b></td>
                            <td style="border: 1px solid #999; padding: 10px; line-height: 1.6;">{latest_record.get('精度チェック', '-')}</td>
                            <td style="border: 1px solid #999; padding: 10px; font-size: 12px;">※当該機種のメーカー規定<br>および許容範囲内であること</td>
                        </tr>
                    </table>

                    <h3 style="font-size: 18px; border-left: 5px solid #0056b3; padding-left: 10px; margin-bottom: 15px;">■ 総合評価</h3>
                    <div style="border: 2px solid {result_color}; padding: 15px; text-align: center; font-size: 22px; font-weight: bold; border-radius: 5px; color: {result_color} !important; letter-spacing: 5px;">
                        {result_text}
                    </div>
                    
                    <div style="margin-top: 30px; font-size: 14px;">
                        <b>特記事項・備考：</b><br>
                        <div style="border: 1px solid #999; padding: 15px; min-height: 80px; margin-top: 5px; white-space: pre-wrap;">{latest_record.get('備考', '特になし')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
        else:
            st.info("まだデータがありません。")
    except Exception as e:
        st.error("データの読み込みに失敗しました。")
