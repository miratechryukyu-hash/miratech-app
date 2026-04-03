import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import qrcode
from io import BytesIO

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

# ==========================================
# 🔐 セキュリティ：パスワード認証ブロック
# ==========================================
def check_password():
    """正しいパスワードが入力されるまでアプリをロックする"""
    def password_entered():
        # 👇 ここがパスワードです（好きな文字に変更してください）
        if st.session_state["password"] == "4011": 
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

# もしパスワードが間違っていたら、ここでプログラムの動きを完全に止める（絶対に下へ進ませない）
if not check_password():
    st.stop()

# ==========================================
# ここから下は、今までのコード（QRダッシュボードやタブメニューなど）をそのまま残す
# ==========================================

query_params = st.query_params
url_me_no = query_params.get("me_no", "")

st.title("🏥 医療機器点検アプリ (miratech)")
# ...（以下略、今までのコードを続けてください）...
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date
import qrcode
from io import BytesIO

# ページ設定
st.set_page_config(page_title="miratech 点検アプリ", layout="centered")

query_params = st.query_params
url_me_no = query_params.get("me_no", "")

categories_list = ["輸液ポンプ", "シリンジポンプ", "人工呼吸器", "その他"]

# ==========================================
# 💡 QRダッシュボード（スマホのカメラで読み取った時に発動！）
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
                        dash_tab1, dash_tab2 = st.tabs(["🏥 機器の基本情報", "📝 過去の点検履歴"])
                        with dash_tab1:
                            st.write(f"### 📊 機器マスターデータ ({cat})")
                            col1, col2 = st.columns(2)
                            col1.metric("ME No.", str(latest_data.get("ME No.", "-")))
                            col2.metric("機種", str(latest_data.get("機種", "-")))
                            col3, col4 = st.columns(2)
                            col3.metric("製造番号 (S/N)", str(latest_data.get("製造番号", "未登録")))
                            col4.metric("これまでの点検回数", f"{len(df_device)} 回")
                        with dash_tab2:
                            st.write("### 🩺 最新＆過去の点検ステータス")
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
# 💡 アプリ本体メニュー（4タブに進化）
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["📝 点検入力", "📁 マスター", "🔍 全履歴", "🔲 QR発行"])

# ====== タブ1：入力画面 ======
with tab1:
    device_category = st.selectbox("▼ 点検する機器の種類", categories_list)
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
        
        # 変数を初期化
        chk_e1=chk_e2=chk_e3=chk_e4=chk_e5=chk_e6=chk_e7 = False
        chk_a1=chk_a2=chk_a3=chk_a4 = False
        chk_op1=chk_op2=chk_op3 = False
        
        chk_es1=chk_es2=chk_es3=chk_es4=chk_es5=chk_es6 = False
        chk_as1=chk_as2=chk_as3=chk_as4=chk_as5 = False
        chk_sop1=chk_sop2=chk_sop3 = False 
        
        flow_acc=occ_press = 0.0
        bubble_ad_water=bubble_ad_nowater = 0
        
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
                    data_dict = {
                        "点検日": str(check_date),
                        "ME No.": me_no,
                        "製造番号": serial_no,
                        "機種": combined_model,
                        "実施者": inspector,
                        "判定": result,
                        "備考": memo
                    }
                    
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
    
    # URLのベースを手動で取得（Streamlit CloudのURLなど）
    # 例: https://miratech-app.streamlit.app/
    base_url = st.text_input("このアプリのURL（ブラウザの上のアドレス）を貼り付けてください", value="https://xxxx.streamlit.app/")
    
    target_qr_me = st.text_input("🔤 QRコードを作りたい「ME No.」を入力", placeholder="例: TE-381-001")
    
    if st.button("QRコードを作成する"):
        if base_url and target_qr_me:
            # ベースURLの末尾に「/?me_no=〇〇」をくっつける
            if base_url.endswith("/"):
                final_url = f"{base_url}?me_no={target_qr_me}"
            else:
                final_url = f"{base_url}/?me_no={target_qr_me}"
            
            # QRコードの画像を生成
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(final_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # 画像をStreamlit上で表示できるように変換
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.success(f"「{target_qr_me}」専用のQRコードができました！")
            st.image(byte_im, width=200)
            
            # ダウンロードボタン
            st.download_button(
                label="📥 このQRコードを画像として保存",
                data=byte_im,
                file_name=f"QR_{target_qr_me}.png",
                mime="image/png"
            )
        else:
            st.warning("アプリのURLと、ME No.の両方を入力してください。")
