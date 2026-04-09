import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import qrcode
from io import BytesIO
import google.generativeai as genai  # ✨AI用に追加
from PIL import Image                # ✨画像処理用に追加
import json                          # ✨データ処理用に追加
import re                            # ✨データ抽出用に追加

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

# ==========================================
# 🔐 セキュリティ：パスワード認証ブロック
# ==========================================
def check_password():
    """正しいパスワードが入力されるまでアプリをロックする"""
    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 安全のため入力した文字をメモリから消去
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.warning("⚠️ このシステムはmiratech琉球の専用システムです。")
        st.text_input("🔑 パスワードを入力してください", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔑 パスワードを入力してください", type="password", on_change=password_entered, key="password")
        st.error("❌ パスワードが違います。不正アクセスのログを記録しました。")
        return False
    return True

# もしパスワードが間違っていたら、ここでプログラムの動きを完全に止める
if not check_password():
    st.stop()

# ==========================================
# 🤖 AI設定（Gemini）
# ==========================================
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

# ==========================================
# 💡 アプリ本体
# ==========================================
query_params = st.query_params
url_me_no = query_params.get("me_no", "")

st.title("うえむら病院専用")
st.title("医療機器点検アプリ")
categories_list = ["輸液ポンプ", "シリンジポンプ", "保育器", "分娩監視装置", "人工呼吸器", "その他"]

# ==========================================
# 💡 QRダッシュボード（画像・マニュアル表示対応版）
# ==========================================
if url_me_no:
    st.success(f"📱 対象機器を認識しました: **{url_me_no}**")
    device_found = False
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        for cat in categories_list:
            try:
                df_cat = conn.read(worksheet=cat, ttl=0).dropna(how="all")
                if "ME No." in df_cat.columns:
                    df_device = df_cat[df_cat["ME No."].astype(str) == url_me_no]
                    if not df_device.empty:
                        latest_data = df_device.iloc[-1]
                        
                        # ✨【新機能】写真と添付文書の表示
                        col_img, col_info = st.columns([1, 1])
                        
                        with col_img:
                            # スプレッドシートに「写真URL」列があり、値が入っている場合
                            pic_url = latest_data.get("写真URL", "")
                            if pd.notnull(pic_url) and str(pic_url).startswith("http"):
                                st.image(pic_url, caption=f"{url_me_no} の外観", use_container_width=True)
                            else:
                                st.info("📸 写真は未登録です")

                        with col_info:
                            st.write(f"### 📊 基本情報 ({cat})")
                            st.write(f"**機種:** {latest_data.get('機種', '-')}")
                            st.write(f"**S/N:** {latest_data.get('製造番号', '-')}")
                            st.write(f"**製造年:** {latest_data.get('製造年', '-')}") # ✨表示追加
                            
                            # ✨【新機能】添付文書ボタン
                            doc_url = latest_data.get("添付文書URL", "")
                            if pd.notnull(doc_url) and str(doc_url).startswith("http"):
                                st.link_button("📖 添付文書・使い方を見る", doc_url, use_container_width=True)
                        
                        st.markdown("---")
                        
                        # 過去履歴の表示
                        with st.expander("📝 過去の点検履歴を確認する"):
                            st.dataframe(df_device.iloc[::-1], use_container_width=True, hide_index=True)
                        
                        device_found = True
                        break
            except Exception:
                continue
        
        if not device_found:
            st.info("💡 この機器の過去の点検記録はまだありません。（新規登録）")
            
    except Exception as e:
        st.warning("データの読み込みに失敗しました。")
    st.markdown("---")

# ==========================================
# 💡 アプリ本体メニュー（4タブ）
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 点検入力", "📁 マスター", "🔍 全履歴", "🔲 QR発行"])

# ====== タブ1：入力画面 ======
with tab1:
    # ✨【新機能】AI銘板スキャナー
    st.subheader("📸 AI銘板スキャナー")
    with st.expander("カメラを起動して製造番号を読み取る", expanded=False):
        img_file = st.camera_input("機器の銘板（シール）を撮影してください")
        
        if img_file and ai_model:
            with st.spinner("AIが文字を解析しています..."):
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
                    # JSON部分だけを抽出
                    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                        st.session_state["scan_sn"] = data.get("serial_number", "")
                        st.session_state["scan_model"] = data.get("model", "")
                        st.session_state["scan_year"] = data.get("manufacture_year", "")
                        st.success("✅ 読み取り成功！下の入力欄に反映しました。")
                    else:
                        st.warning("情報が見つかりませんでした。少し近づいて撮り直してみてください。")
                except Exception as e:
                    st.error(f"AI解析エラー: {e}")
        elif not ai_model:
            st.warning("APIキーが設定されていないため、AI機能は使えません。")

    st.markdown("---")
    
    device_category = st.selectbox("▼ 点検する機器の種類", categories_list)
    
    # ✨ AIが読み取った型式があれば表示する
    scan_model = st.session_state.get("scan_model", "")
    if scan_model:
        st.info(f"💡 AIが読み取った型式: **{scan_model}** （合っているか確認し、下で選択してください）")

    # 💡 機器ごとの型式選択
    if device_category == "輸液ポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-281", "TE-261", "TE-171", "TE-161", "TE-LM830", "OT-707", "OT-818G", "AS-800", "その他"])
    elif device_category == "シリンジポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-381", "TE-371", "TE-351", "TE-331", "その他"])
    elif device_category == "保育器":
        incubator_type = st.radio("▼ 保育器のタイプ", ["閉鎖式 (V-2100G・V85など)", "開放型 (V-505・103HEなど)"])
        if "閉鎖式" in incubator_type:
            device_model = st.selectbox("▼ 型式", ["V-2100G", "V85", "その他"])
        else:
            device_model = st.selectbox("▼ 型式", ["V-505", "103HE", "その他"])
    else:
        device_model = st.text_input("▼ 型式を入力してください")
    
    st.markdown("---")

    with st.form("check_form"):
        col_form1, col_form2 = st.columns(2)
        with col_form1:
            check_date = st.date_input("点検日", date.today())
        with col_form2:
            me_no = st.text_input("ME No.", value=url_me_no, placeholder="例: NT-001")
        
        # ✨ 読み取ったS/Nを初期値としてセット
        default_sn = st.session_state.get("scan_sn", "")
        serial_no = st.text_input("製造番号 (S/N)", value=default_sn, placeholder="例: 12345678")
        st.write(f"### 📋 【{device_category} : {device_model}】専用チェック")
        
        # 変数を初期化（既存機器用）
        chk_e1=chk_e2=chk_e3=chk_e4=chk_e5=chk_e6=chk_e7 = False
        chk_a1=chk_a2=chk_a3=chk_a4 = False
        chk_op1=chk_op2=chk_op3 = False
        chk_es1=chk_es2=chk_es3=chk_es4=chk_es5=chk_es6 = False
        chk_as1=chk_as2=chk_as3=chk_as4=chk_as5 = False
        chk_sop1=chk_sop2=chk_sop3 = False 
        flow_acc=occ_press = 0.0
        bubble_ad_water=bubble_ad_nowater = 0
        
        # 変数を初期化（保育器用）
        inc_c_checks = {}
        inc_o_checks = {}
        inc_temp_disp = inc_temp_meas = 36.0

        # ==================================
        # 💡 各機器のチェック項目表示
        # ==================================
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

            else: # 開放型 (インファントウォーマ)
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

    # ==================================
    # 💾 データ保存の処理
    # ==================================
    if submitted:
        if not me_no:
            st.warning("⚠️ ME No.を入力してください")
        else:
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                target_sheet = device_category
                
                try:
                    existing_data = conn.read(worksheet=target_sheet, ttl=0).dropna(how="all") 
                except Exception:
                    existing_data = pd.DataFrame()
                
                is_duplicate = False
                if not existing_data.empty and "ME No." in existing_data.columns and "点検日" in existing_data.columns:
                    is_duplicate = ((existing_data["ME No."] == me_no) & (existing_data["点検日"].astype(str) == str(check_date))).any()
                
                if is_duplicate:
                    st.error(f"🚨 ちょっと待って！「{me_no}」は本日（{check_date}）すでに点検済みです！")
                else:
                    combined_model = f"{device_category} ({device_model})"
                    # 基本データ
                    data_dict = {
                        "点検日": str(check_date),
                        "ME No.": me_no,
                        "製造番号": serial_no,
                        "製造年": st.session_state.get("scan_year", ""), # ✨AIで読み取った製造年を保存！
                        "機種": combined_model,
                        "実施者": inspector,
                        "判定": result,
                        "備考": memo
                    }
                    
                    # 機器別データの結合
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
                    st.cache_data.clear()
                    st.balloons()
                    st.success(f"大成功！{me_no} のデータを「{target_sheet}」シートに記録しました！")
            except Exception as e:
                st.error(f"エラー発生: スプレッドシートに「{target_sheet}」という名前のシートが作られているか確認してください。詳細: {e}")

# ====== タブ2：マスター ======
with tab2:
    st.subheader("🏥 機器マスター")
    view_cat_master = st.selectbox("📂 読み込むシートを選択", categories_list, key="master_cat")
    
    if st.button("🔄 台帳を更新する"):
        st.cache_data.clear()
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=view_cat_master, ttl=0).dropna(how="all")
        if df.empty or "ME No." not in df.columns:
            st.info(f"「{view_cat_master}」シートにはまだデータがありません。")
        else:
            df_master = df.drop_duplicates(subset=["ME No."], keep="last")
            display_cols = ["ME No.", "製造番号", "点検日", "判定"]
            existing_cols = [col for col in display_cols if col in df_master.columns]
            st.dataframe(df_master[existing_cols].rename(columns={"点検日": "最終点検日"}), hide_index=True, use_container_width=True)
    except Exception as e:
        st.info(f"スプレッドシートに「{view_cat_master}」シートを作成してください。")

# ====== タブ3：全履歴 ======
with tab3:
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
        st.info(f"スプレッドシートに「{view_cat_history}」シートを作成してください。")

# ==========================================
# 💡 タブ4：QRコード発行機能
# ==========================================
with tab4:
    st.subheader("🔲 機器用QRコードの作成")
    st.write("対象の「ME No.」を入力すると、機器に貼り付ける用のQRコードが作成されます。")
    
    base_url = st.text_input("このアプリのURL（ブラウザの上のアドレス）を貼り付けてください", value="https://miratechryukyu-hash-miratech-app-kiki-nnm67c.streamlit.app")
    target_qr_me = st.text_input("🔤 QRコードを作りたい「ME No.」を入力", placeholder="例: TE-381-001")
    
    if st.button("QRコードを作成する"):
        if base_url and target_qr_me:
            if base_url.endswith("/"):
                final_url = f"{base_url}?me_no={target_qr_me}"
            else:
                final_url = f"{base_url}/?me_no={target_qr_me}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(final_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.success(f"「{target_qr_me}」専用のQRコードができました！")
            st.image(byte_im, width=200)
            
            st.download_button(
                label="📥 このQRコードを画像として保存",
                data=byte_im,
                file_name=f"QR_{target_qr_me}.png",
                mime="image/png"
            )
        else:
            st.warning("アプリのURLと、ME No.の両方を入力してください。")
