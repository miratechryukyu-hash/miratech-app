import streamlit as st
from datetime import date

# 1. ページ設定（必ず最初に記述）
st.set_page_config(
    page_title="miratech 点検アプリ",
    page_icon="🔧",
    layout="centered"
)

# カスタムCSSでスマホのボタンを押しやすく調整
st.markdown("""
    <style>
    .stButton>button {
        height: 3em;
        border-radius: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🏥 輸液・シリンジポンプ定期点検")
st.caption("TE-281 / TE-331 対応版")

# --- セクション1: 基本情報 ---
with st.expander("1. 基本情報 [cite: 1, 2, 3, 4, 9]", expanded=True):
    me_no = st.text_input("ME No. [cite: 3]", placeholder="例: CE-001")
    model_type = st.selectbox("機種 [cite: 2, 7]", ["輸液ポンプ TE-281", "シリンジポンプ TE-331", "その他"])
    inspector = st.text_input("点検実施者 [cite: 9]", value="Sho Yasutomi")
    check_date = st.date_input("点検実施日 [cite: 4]", date.today())

# --- セクション2: 外観・作動点検 ---
st.subheader("2. 点検項目 (○:異常なし / ×:要点検) [cite: 5, 10, 11, 26]")
# スマホで押しやすいよう2カラムに分ける
cols = st.columns(2)

with cols[0]:
    st.write("**外観・基本動作**")
    check_visual = st.checkbox("本体の汚れ・破損 [cite: 6]", value=True)
    check_clamp = st.checkbox("ポールクランプネジ穴 [cite: 14]", value=True)
    check_finger = st.checkbox("フィンガー部動作 [cite: 19]", value=True)
    check_acdc = st.checkbox("AC・DC切り替え [cite: 21]", value=True)
    check_led = st.checkbox("表示部LED [cite: 25]", value=True)

with cols[1]:
    st.write("**警報・機能**")
    check_alarm_start = st.checkbox("開始忘れ警報 [cite: 12]", value=True)
    check_alarm_bubble = st.checkbox("気泡検出警報 [cite: 18]", value=True)
    check_alarm_door = st.checkbox("ドアオープン警報 [cite: 20]", value=True)
    check_alarm_flow = st.checkbox("流量設定無し警報 [cite: 15]", value=True)
    check_finish = st.checkbox("輸液完了 [cite: 22]", value=True)

# --- セクション3: 測定データ入力 ---
st.subheader("3. 測定値入力 [cite: 30, 32, 34, 36]")
# 数値入力はスマホのキーボードが数字モードになるよう設定
flow_rate = st.number_input("流量精度 (ml) [許容: 18~22ml] [cite: 31, 41]", value=20.0, step=0.1, format="%.1f")
occlusion_p = st.number_input("下部閉塞圧 (kpa) [許容: 30~90kpa] [cite: 33, 43]", value=60)
battery_val = st.number_input("内蔵バッテリ点検値 [750以上OK] [cite: 36, 46]", value=800)

# --- セクション4: 判定とメモ ---
st.subheader("4. 総合判定 [cite: 55, 58]")
result = st.radio("判定結果 [cite: 58]", ["使用可", "メーカー修理", "廃棄 [cite: 59]"], horizontal=True)
memo = st.text_area("備考・報告欄 [cite: 48]", placeholder="特記事項があれば記入")

# 完了チェック
seal_ok = st.checkbox("定期点検実施シール貼付 [cite: 62]")
db_ok = st.checkbox("データベース入力完了 [cite: 63]")

if st.button("点検データを送信・保存", use_container_width=True):
    # 将来的にここにGoogleスプレッドシート保存処理を追記
    st.balloons()
    st.success(f"ME No.{me_no} の点検データを正常に受け付けました！")

# --- サイドバーに点検のコツを表示 ---
with st.sidebar:
    st.title("💡 点検サポート")
    st.info("""
    **メニュー2への入り方 [cite: 60, 61]**
    電源ON → 何も触らずに「停止・消音」を押しながら「メニュー」を約2秒長押し。
    """)
    st.warning("""
    **気泡検出点検 [cite: 39, 47]**
    「AIR/CHK」が表示されるまでメニューを短押し。
    """)
