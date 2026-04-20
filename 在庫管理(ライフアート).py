import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.title('🏥ライフアート 在庫管理')

conn = st.connection("gsheets", type=GSheetsConnection)

# --- シート名を変数にして統一 ---
SHEET_MAIN = "ライフアート在庫管理"
SHEET_LOG = "logs"

# 1. 現在の在庫データの読み込み
df_inventory = conn.read(worksheet=SHEET_MAIN)

# --- エラーを防ぐ魔法の2行（空白行の無視と数字への確実な変換） ---
df_inventory = df_inventory.dropna(subset=['品名'])
df_inventory['在庫数'] = pd.to_numeric(df_inventory['在庫数'], errors='coerce').fillna(0).astype(int)
# -------------------------------------------------------------

st.write("### 📦 現在の在庫状況")
st.dataframe(df_inventory, use_container_width=True)

st.write("---")

# 担当者名の記憶（セッションステートの活用）
if 'staff_name' not in st.session_state:
    st.session_state.staff_name = ""

st.write("### ✍️ 担当者")
# 一度入力すれば、次からは自動で入力された状態になります
staff_name = st.text_input('あなたのお名前（一度入力すれば記憶されます）', value=st.session_state.staff_name)
if staff_name != st.session_state.staff_name:
    st.session_state.staff_name = staff_name

st.write("---")
st.write("### 🚀 ワンクリック持ち出し（各1個）")

# 共通の記録処理関数
def record_action(item, qty, action_type, staff):
    if action_type == "持ち出し":
        df_inventory.loc[df_inventory['品名'] == item, '在庫数'] -= qty
    else:
        df_inventory.loc[df_inventory['品名'] == item, '在庫数'] += qty
    
    conn.update(worksheet=SHEET_MAIN, data=df_inventory)
    
    new_log = pd.DataFrame([{
        "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "担当者": staff,
        "品名": item,
        "区分": action_type,
        "数量": qty
    }])
    
    df_logs = conn.read(worksheet=SHEET_LOG)
    df_logs = pd.concat([df_logs, new_log], ignore_index=True)
    conn.update(worksheet=SHEET_LOG, data=df_logs)

# 持ち出し用のボタンをアイテムごとに並べる（スマホで見やすいように2列）
item_list = df_inventory['品名'].tolist()
cols = st.columns(2)

for i, item in enumerate(item_list):
    # 余りが0なら左の列、1なら右の列にボタンを配置
    with cols[i % 2]:
        # 品名ごとにボタンを作成
        if st.button(f"➖ {item} を1つ持ち出す", key=f"out_{item}", use_container_width=True):
            if st.session_state.staff_name:
                record_action(item, 1, "持ち出し", st.session_state.staff_name)
                # 画面を邪魔しない「トースト通知」でサクッと知らせる
                st.toast(f"✅ {item}を1つ持ち出しました！")
                st.rerun()
            else:
                st.error("☝️ 上の欄に担当者名を入力してください")
