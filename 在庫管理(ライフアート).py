import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta, timezone

# 日本標準時（JST）の設定
JST = timezone(timedelta(hours=+9), 'JST')

st.set_page_config(page_title="miratech在庫管理", layout="centered")
st.title('🌅ライフアート 在庫管理')

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
            if row['在庫数'] <= 0:
                st.error(f"❌ **{row['品名']}** が欠品中")
            else:
                st.warning(f"⚠️ **{row['品名']}** 残り {row['在庫数']}個")

st.write("### 📦 現在の在庫状況")
st.dataframe(df_inventory, hide_index=True)
st.write("---")

# セッションステート（記憶）の初期化
if 'staff_name' not in st.session_state:
    st.session_state.staff_name = ""
if 'cart' not in st.session_state:
    st.session_state.cart = {}

st.write("### ✍️ 担当者")
staff_name = st.text_input('あなたのお名前', value=st.session_state.staff_name)
if staff_name != st.session_state.staff_name:
    st.session_state.staff_name = staff_name

st.write("---")
st.write("### 🛒 持ち出し・返却を選ぶ")

item_list = df_inventory['品名'].tolist()

# スマホで押しやすいように1行ずつボタンを配置
for item in item_list:
    c1, c2, c3 = st.columns([2, 1.2, 1.2])
    c1.write(f"**{item}**")
    
    if c2.button("➕ 出す", key=f"add_{item}", use_container_width=True):
        st.session_state.cart[item] = st.session_state.cart.get(item, 0) + 1
        st.rerun()
        
    if c3.button("➖ 戻す", key=f"sub_{item}", use_container_width=True):
        st.session_state.cart[item] = st.session_state.cart.get(item, 0) - 1
        st.rerun()

st.write("---")
st.write("### 🧺 現在の予定（カート）")

# カート内の「0」のアイテムは表示しないように整理
active_cart = {k: v for k, v in st.session_state.cart.items() if v != 0}

if not active_cart:
    st.info("現在選ばれているアイテムはありません。")
else:
    for cart_item, qty in active_cart.items():
        c1, c2 = st.columns([3, 1])
        
        # プラス（持ち出し）とマイナス（返却）で色と文字を変える！
        if qty > 0:
            c1.success(f"📦 {cart_item} ： **{qty} 個** 持ち出し")
        else:
            c1.warning(f"🔄 {cart_item} ： **{abs(qty)} 個** 返却")
            
        if c2.button("取消", key=f"del_{cart_item}"):
            st.session_state.cart[cart_item] = 0
            st.rerun()

    st.write("")
    
    if st.button("✅ 上記の内容で確定する", type="primary", use_container_width=True):
        if not st.session_state.staff_name:
            st.error("☝️ 担当者名を入力してください！")
        else:
            now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S")
            
            take_out_items = []
            return_items = []
            
            # 在庫計算とログ仕分け
            for c_item, c_qty in active_cart.items():
                # 出す(プラス)なら在庫から引き、戻す(マイナス)なら在庫に足す
                df_inventory.loc[df_inventory['品名'] == c_item, '在庫数'] -= c_qty
                
                if c_qty > 0:
                    take_out_items.append(f"{c_item}×{c_qty}")
                elif c_qty < 0:
                    return_items.append(f"{c_item}×{abs(c_qty)}")

            # スプレッドシート更新（在庫）
            conn.update(worksheet=SHEET_MAIN, data=df_inventory)
            
            # ログの作成（持ち出しと返却が混ざっていても、綺麗に2行に分けて記録！）
            log_entries = []
            if take_out_items:
                log_entries.append({
                    "日時": now_str,
                    "担当者": st.session_state.staff_name,
                    "品名": "、".join(take_out_items),
                    "区分": "一括持ち出し",
                    "数量": sum([v for v in active_cart.values() if v > 0])
                })
            if return_items:
                log_entries.append({
                    "日時": now_str,
                    "担当者": st.session_state.staff_name,
                    "品名": "、".join(return_items),
                    "区分": "一括返却・補充",
                    "数量": sum([abs(v) for v in active_cart.values() if v < 0])
                })
            
            if log_entries:
                new_logs_df = pd.DataFrame(log_entries)
                df_logs = conn.read(worksheet=SHEET_LOG)
                df_logs = pd.concat([df_logs, new_logs_df], ignore_index=True)
                conn.update(worksheet=SHEET_LOG, data=df_logs)
            
            # カートを空にしてリセット
            st.session_state.cart = {}
            st.session_state.toast_msg = "✅ 記録を完了しました！"
            st.rerun()
