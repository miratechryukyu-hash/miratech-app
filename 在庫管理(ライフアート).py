import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 日本標準時（JST）の設定
JST = timezone(timedelta(hours=+9), 'JST')

st.set_page_config(page_title="miratech在庫管理", layout="centered")
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

# 🚨 在庫アラートチェック
low_stock_items = df_inventory[df_inventory['在庫数'] <= 2]
if not low_stock_items.empty:
    with st.expander("🚨 補充が必要なアイテムがあります！", expanded=True):
        for index, row in low_stock_items.iterrows():
            if row['在庫数'] == 0:
                st.error(f"❌ **{row['品名']}** が欠品中")
            else:
                st.warning(f"⚠️ **{row['品名']}** 残り {row['在庫数']}個")

st.write("### 📦 現在の在庫状況")
# インデックス（左の数字）を隠して表示
st.dataframe(df_inventory, use_container_width=True, hide_index=True)
st.write("---")

# セッションステート（記憶）の初期化
if 'staff_name' not in st.session_state:
    st.session_state.staff_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = {}

# ✍️ 担当者入力
staff_name = st.text_input('あなたのお名前', value=st.session_state.staff_name)
if staff_name != st.session_state.staff_name:
    st.session_state.staff_name = staff_name

st.write("---")

# 🔄 モード切替
mode = st.radio(
    "操作モードを選択してください",
    ["➖ 持ち出し", "➕ 返却・補充"],
    horizontal=True
)

st.write(f"### 🛒 {mode}するものを選ぶ")

item_list = df_inventory['品名'].tolist()
cols = st.columns(2)

for i, item in enumerate(item_list):
    with cols[i % 2]:
        button_label = f"➕ {item}" if "返却" in mode else f"➖ {item}"
        if st.button(button_label, key=f"btn_{item}", use_container_width=True):
            st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
            st.rerun()

st.write("---")
st.write(f"### 🧺 現在の{mode}予定")

if not st.session_state.cart:
    st.info("アイテムが選ばれていません。")
else:
    for cart_item, qty in st.session_state.cart.items():
        c1, c2 = st.columns([3, 1])
        c1.write(f"・ {cart_item} ： **{qty} 個**")
        if c2.button("取消", key=f"del_{cart_item}"):
            del st.session_state.cart[cart_item]
            st.rerun()

    st.write("")
    
    confirm_label = f"✅ {mode}を確定する"
    if st.button(confirm_label, type="primary", use_container_width=True):
        if not st.session_state.staff_name:
            st.error("☝️ 担当者名を入力してください！")
        else:
            # 在庫計算とログ作成
            now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
            item_details = "、".join([f"{k}×{v}" for k, v in st.session_state.cart.items()])
            total_qty = sum(st.session_state.cart.values())
            
            # モードに応じて足し引きを切り替え
            action_type = "持ち出し" if "持ち出し" in mode else "返却・補充"
            multiplier = -1 if "持ち出し" in mode else 1
            
            for c_item, c_qty in st.session_state.cart.items():
                df_inventory.loc[df_inventory['品名'] == c_item, '在庫数'] += (c_qty * multiplier)
            
            # スプレッドシート更新（在庫）
            conn.update(worksheet=SHEET_MAIN, data=df_inventory)
            
            # ログ作成
            new_log = pd.DataFrame([{
                "日時": now_str,
                "担当者": st.session_state.staff_name,
                "品名": item_details,
                "区分": action_type,
                "数量": total_qty
            }])
            df_logs = conn.read(worksheet=SHEET_LOG)
            df_logs = pd.concat([df_logs, new_log], ignore_index=True)
            conn.update(worksheet=SHEET_LOG, data=df_logs)
            
            st.session_state.cart = {}
            st.session_state.toast_msg = f"✅ {action_type}を記録しました！"
            st.rerun()
