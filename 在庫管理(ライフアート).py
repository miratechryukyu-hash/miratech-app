import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 日本標準時（JST）の設定
JST = timezone(timedelta(hours=+9), 'JST')

st.title('🏥ライフアート 在庫管理')

# トースト通知の処理
if 'toast_msg' in st.session_state:
    st.toast(st.session_state.toast_msg)
    del st.session_state['toast_msg']

conn = st.connection("gsheets", type=GSheetsConnection)

SHEET_MAIN = "ライフアート在庫管理"
SHEET_LOG = "logs"

# 1. 現在の在庫データの読み込み
df_inventory = conn.read(worksheet=SHEET_MAIN)
df_inventory = df_inventory.dropna(subset=['品名'])
df_inventory['在庫数'] = pd.to_numeric(df_inventory['在庫数'], errors='coerce').fillna(0).astype(int)

# --- 🔔 追加機能：在庫アラートチェック ---
# 在庫が2個以下のアイテムを抽出
low_stock_items = df_inventory[df_inventory['在庫数'] <= 2]

if not low_stock_items.empty:
    st.write("### 🚨 補充が必要なアイテム")
    for index, row in low_stock_items.iterrows():
        # 在庫数に応じてメッセージを変える
        if row['在庫数'] == 0:
            st.error(f"❌ **{row['品名']}** が **欠品** しています！すぐに補充してください。")
        else:
            st.warning(f"⚠️ **{row['品名']}** の在庫が残り **{row['在庫数']}個** です。")
# ---------------------------------------

st.write("### 📦 現在の在庫状況")
st.dataframe(df_inventory, use_container_width=True)
st.write("---")

# セッションステート（記憶）の初期化
if 'staff_name' not in st.session_state:
    st.session_state.staff_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = {}

st.write("### ✍️ 担当者")
staff_name = st.text_input('あなたのお名前（一度入力すれば記憶されます）', value=st.session_state.staff_name)
if staff_name != st.session_state.staff_name:
    st.session_state.staff_name = staff_name

st.write("---")
st.write("### 🛒 持ち出すものを選ぶ")

item_list = df_inventory['品名'].tolist()
cols = st.columns(2)

for i, item in enumerate(item_list):
    with cols[i % 2]:
        if st.button(f"➕ {item}", key=f"add_{item}", use_container_width=True):
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
            st.rerun()

st.write("---")
st.write("### 🧺 現在の持ち出し予定（カート）")

if not st.session_state.cart:
    st.info("現在選ばれているアイテムはありません。")
else:
    for cart_item, qty in st.session_state.cart.items():
        col_name, col_btn = st.columns([3, 1])
        col_name.write(f"・ {cart_item} ： **{qty} 個**")
        if col_btn.button("取消", key=f"del_{cart_item}"):
            del st.session_state.cart[cart_item]
            st.rerun()

    st.write("")
    
    if st.button("✅ 上記の内容でまとめて持ち出しを確定する", type="primary", use_container_width=True):
        if not st.session_state.staff_name:
            st.error("☝️ 担当者名を入力してください！")
        else:
            # 1. 在庫の引き算
            for c_item, c_qty in st.session_state.cart.items():
                df_inventory.loc[df_inventory['品名'] == c_item, '在庫数'] -= c_qty
            
            conn.update(worksheet=SHEET_MAIN, data=df_inventory)
            
            # 2. ログを1行に集約
            now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
            item_details = "、".join([f"{c_item}×{c_qty}" for c_item, c_qty in st.session_state.cart.items()])
            total_qty = sum(st.session_state.cart.values())
            
            log_entries = [{
                "日時": now_str,
                "担当者": st.session_state.staff_name,
                "品名": item_details,
                "区分": "一括持ち出し",
                "数量": total_qty
            }]
            
            new_logs_df = pd.DataFrame(log_entries)
            df_logs = conn.read(worksheet=SHEET_LOG)
            df_logs = pd.concat([df_logs, new_logs_df], ignore_index=True)
            conn.update(worksheet=SHEET_LOG, data=df_logs)
            
            st.session_state.cart = {}
            st.session_state.toast_msg = "✅ まとめて持ち出しを記録しました！"
            st.rerun()
