import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.title('🏥ライフアート 在庫管理')

# スプレッドシートへの接続設定
conn = st.connection("gsheets", type=GSheetsConnection)

# 1. 現在の在庫データの読み込み
# (スプレッドシートのURLを指定するか、secrets.tomlに設定します)
df_inventory = conn.read(worksheet="ライフアート在庫管理")

st.write("### 📦 現在の在庫状況")
st.dataframe(df_inventory, use_container_width=True)

st.write("---")

# 2. 入出力フォーム
st.write("### ✍️ 持ち出し・補充の記録")

item_list = df_inventory['品名'].tolist()
selected_item = st.selectbox('品名を選択', item_list)
amount = st.number_input('数量', min_value=1, step=1)
staff_name = st.text_input('担当者名（新人も入力しやすく）')

col1, col2 = st.columns(2)

# 共通の記録処理関数
def record_action(item, qty, action_type, staff):
    # --- 在庫数の更新 ---
    if action_type == "持ち出し":
        df_inventory.loc[df_inventory['品名'] == item, '在庫数'] -= qty
    else:
        df_inventory.loc[df_inventory['品名'] == item, '在庫数'] += qty
    
    # 在庫シートを更新
    conn.update(worksheet="inventory", data=df_inventory)
    
    # --- 履歴（ログ）の追記 ---
    new_log = pd.DataFrame([{
        "日時": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "担当者": staff,
        "品名": item,
        "区分": action_type,
        "数量": qty
    }])
    
    # 既存のログを読み込んで追記
    df_logs = conn.read(worksheet="logs")
    df_logs = pd.concat([df_logs, new_log], ignore_index=True)
    conn.update(worksheet="logs", data=df_logs)

if col1.button('➖ 持ち出し記録', use_container_width=True):
    if staff_name:
        record_action(selected_item, amount, "持ち出し", staff_name)
        st.success(f'{staff_name}さんが {selected_item} を持ち出しました')
        st.rerun()
    else:
        st.error("担当者名を入力してください")

if col2.button('➕ 補充記録', use_container_width=True):
    if staff_name:
        record_action(selected_item, amount, "補充", staff_name)
        st.success(f'{selected_item} を補充しました')
        st.rerun()
    else:
        st.error("担当者名を入力してください")
