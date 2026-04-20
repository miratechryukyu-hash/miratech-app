import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
# ▼▼ 変更点1：日本時間を扱うためのツールを追加 ▼▼
from datetime import datetime, timedelta, timezone

# 日本標準時（JST）の設定
JST = timezone(timedelta(hours=+9), 'JST')
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

st.title('🏥ライフアート 在庫管理')

# ▼▼ 変更点2：画面が更新された直後にバルーンを出す仕組み ▼▼
if 'toast_msg' in st.session_state:
    st.toast(st.session_state.toast_msg)
    del st.session_state['toast_msg'] # 出したら記憶を消す
# ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

conn = st.connection("gsheets", type=GSheetsConnection)

SHEET_MAIN = "ライフアート在庫管理"
SHEET_LOG = "logs"

# 1. 現在の在庫データの読み込み
df_inventory = conn.read(worksheet=SHEET_MAIN)
df_inventory = df_inventory.dropna(subset=['品名'])
df_inventory['在庫数'] = pd.to_numeric(df_inventory['在庫数'], errors='coerce').fillna(0).astype(int)

st.write("### 📦 現在の在庫状況")
st.dataframe(df_inventory, use_container_width=True)

st.write("---")

if 'staff_name' not in st.session_state:
    st.session_state.staff_name = ""

st.write("### ✍️ 担当者")
staff_name = st.text_input('あなたのお名前（一度入力すれば記憶されます）', value=st.session_state.staff_name)
if staff_name != st.session_state.staff_name:
    st.session_state.staff_name = staff_name

st.write("---")
st.write("### 🚀 ワンクリック持ち出し（各1個）")

def record_action(item, qty, action_type, staff):
    if action_type == "持ち出し":
        df_inventory.loc[df_inventory['品名'] == item, '在庫数'] -= qty
    else:
        df_inventory.loc[df_inventory['品名'] == item, '在庫数'] += qty
    
    conn.update(worksheet=SHEET_MAIN, data=df_inventory)
    
    new_log = pd.DataFrame([{
        # ▼▼ 変更点3：記録する時間を日本時間（JST）に変更 ▼▼
        "日時": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S"),
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
        "担当者": staff,
        "品名": item,
        "区分": action_type,
        "数量": qty
    }])
    
    df_logs = conn.read(worksheet=SHEET_LOG)
    df_logs = pd.concat([df_logs, new_log], ignore_index=True)
    conn.update(worksheet=SHEET_LOG, data=df_logs)

item_list = df_inventory['品名'].tolist()
cols = st.columns(2)

for i, item in enumerate(item_list):
    with cols[i % 2]:
        if st.button(f"➖ {item} を1つ持ち出す", key=f"out_{item}", use_container_width=True):
            if st.session_state.staff_name:
                record_action(item, 1, "持ち出し", st.session_state.staff_name)
                # ▼▼ 変更点4：すぐバルーンを出さずに、記憶させてからリロード ▼▼
                st.session_state.toast_msg = f"✅ {item}を1つ持ち出しました！"
                st.rerun()
                # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
            else:
                st.error("☝️ 上の欄に担当者名を入力してください")
