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
    device_category = st.selectbox("▼ 点検する機器の種類", ["輸液ポンプ", "シリンジポンプ", "人工呼吸器", "その他"])
    
    if device_category == "輸液ポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-281", "TE-261", "TE-171", "TE-161", "TE-LM830", "OT-707", "OT-818G", "AS-800", "その他"])
    elif device_category == "シリンジポンプ":
        device_model = st.selectbox("▼ 型式", ["TE-381", "TE-371", "TE-351", "TE-331", "その他"])
    else:
        device_model = st.text_input("▼ 型式を入力してください")
    
    st.markdown("---")

    with st.form("check_form"):
        check_date = st.date_input("点検日", date.today())
        me_no = st.text_input("ME No.", placeholder="例: NT-001")
        
        st.write(f"### 📋 【{device_category} : {device_model}】専用チェック")
        
        # ＝＝＝ 輸液ポンプが選ばれた時の画面 ＝＝＝
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

        # ＝＝＝ シリンジポンプが選ばれた時の画面 ＝＝＝
        elif device_category == "シリンジポンプ":
            # 【大進化】シリンジポンプ専用のプロ仕様チェックリスト！
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
            
            # 自動判定ロジック
            ext_all_ok_s = all([chk_es1, chk_es2, chk_es3, chk_es4, chk_es5, chk_es6])
            alm_all_ok_s = all([chk_as1, chk_as2, chk_as3, chk_as4, chk_as5])
            
            exterior_result = "異常なし" if (ext_all_ok_s and alm_all_ok_s) else "異常あり"
            detail_result = f"外観/警報:{'OK' if (ext_all_ok_s and alm_all_ok_s) else 'NG'} | 流量:{flow_acc_s}ml, 閉塞:{occ_press_s}, バッテリ:{battery_s}"

        # ＝＝＝ 人工呼吸器・その他が選ばれた時の画面 ＝＝＝
        else:
            exterior_result = st.radio("外装点検", ["異常なし", "異常あり"], horizontal=True)
            detail_result = st.text
