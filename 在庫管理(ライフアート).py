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

st.write("### 📦 現在の在庫状況")
st.dataframe(df_inventory, use_container_width=True)
st.write("---")

# セッションステート（記憶）の初期化
if 'staff_name' not in st.session_state:
    st.session_state.staff_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = {} # 買い物かごを準備

st.write("### ✍️ 担当者")
staff_name = st.text_input('あなたのお名前（一度入力すれば記憶されます）', value=st.session_state.staff_name)
if staff_name != st.session_state.staff_name:
    st.session_state.staff_name = staff_name

st.write("---")
st.write("### 🛒 持ち出すものを選ぶ")

item_list = df_inventory['品名'].tolist()
cols = st.columns(2)

# アイテムをカートに入れるボタン
for i, item in enumerate(item_list):
    with cols[i % 2]:
        if st.button(f"➕ {item}", key=f"add_{item}", use_container_width=True):
            # 選んだアイテムを買い物かごに入れる
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
            st.rerun()

st.write("---")
st.write("### 🧺 現在の持ち出し予定（カート）")

# カートの中身を表示するエリア
if not st.session_state.cart:
    st.info("現在選ばれているアイテムはありません。上のボタンから追加してください。")
else:
    for cart_item, qty in st.session_state.cart.items():
        col_name, col_btn = st.columns([3, 1])
        col_name.write(f"・ {cart_item} ： **{qty} 個**")
        # 間違えた時の取消ボタン
        if col_btn.button("取消", key=f"del_{cart_item}"):
            del st.session_state.cart[cart_item]
            st.rerun()

    st.write("") # 少し隙間を空ける
    
    # まとめて確定するボタン（目立つように primary カラーに）
    if st.button("✅ 上記の内容でまとめて持ち出しを確定する", type="primary", use_container_width=True):
        if not st.session_state.staff_name:
            st.error("☝️ 担当者名を入力してください！")
        else:
            # 1. 在庫の引き算をまとめて行う
            for c_item, c_qty in st.session_state.cart.items():
                df_inventory.loc[df_inventory['品名'] == c_item, '在庫数'] -= c_qty
            
            # スプレッドシートの在庫を一気に更新（1回だけ通信！）
            conn.update(worksheet=SHEET_MAIN, data=df_inventory)
            
            # 2. ログをまとめて作成する
            log_entries = []
            now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
            for c_item, c_qty in st.session_state.cart.items():
                log_entries.append({
                    "日時": now_str,
                    "担当者": st.session_state.staff_name,
                    "品名": c_item,
                    "区分": "持ち出し",
                    "数量": c_qty
                })
            
            new_logs_df = pd.DataFrame(log_entries)
            df_logs = conn.read(worksheet=SHEET_LOG)
            df_logs = pd.concat([df_logs, new_logs_df], ignore_index=True)
            
            # スプレッドシートのログを一気に更新（1回だけ通信！）
            conn.update(worksheet=SHEET_LOG, data=df_logs)
            
            # カートを空にして通知
            st.session_state.cart = {}
            st.session_state.toast_msg = "✅ まとめて持ち出しを記録しました！"
            st.rerun()
