import streamlit as st
import pandas as pd
import os

# データを保存するCSVファイルの名前
CSV_FILE = 'inventory.csv'

# 初期データの作成（ファイルがまだない場合のみ実行されます）
def init_data():
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame({
            '品名': ['手袋', '消毒液', 'テープ類', 'ガーゼ類', 'マスク'],
            '在庫数': [100, 10, 30, 200, 150] # 仮の初期在庫
        })
        df.to_csv(CSV_FILE, index=False)

# CSVから在庫データを読み込む
def load_data():
    return pd.read_csv(CSV_FILE)

# CSVへ在庫データを保存する
def save_data(df):
    df.to_csv(CSV_FILE, index=False)

# メイン画面の構築
def main():
    st.title('🏥 訪問看護ステーション 在庫管理')
    st.caption('プロトタイプ版（CSV保存）')
    
    # データの初期化と読み込み
    init_data()
    df = load_data()

    # 1. 現在の在庫状況の表示
    st.write("### 📦 現在の在庫状況")
    # DataFrameを見やすく表示（コンテナ幅に合わせる）
    st.dataframe(df, use_container_width=True)

    st.write("---")
    
    # 2. 持ち出し・補充の入力エリア
    st.write("### ✍️ 持ち出し・補充の入力")
    
    # 品名の選択（ドロップダウン）
    item_list = df['品名'].tolist()
    selected_item = st.selectbox('品名を選んでください', item_list)
    
    # 数量の入力（マイナスにはならないようにmin_value=1を設定）
    amount = st.number_input('数量', min_value=1, value=1, step=1)
    
    # ボタンを横に2つ並べる
    col1, col2 = st.columns(2)
    
    with col1:
        # 持ち出しボタン
        if st.button('➖ 持ち出し（出庫）', use_container_width=True):
            # 選んだ品名の在庫数を減らす
            df.loc[df['品名'] == selected_item, '在庫数'] -= amount
            save_data(df)
            st.success(f'{selected_item}を {amount} 個、持ち出しました。')
            st.rerun() # 画面をリロードして最新の在庫を反映
            
    with col2:
        # 補充ボタン
        if st.button('➕ 補充（入庫）', use_container_width=True):
            # 選んだ品名の在庫数を増やす
            df.loc[df['品名'] == selected_item, '在庫数'] += amount
            save_data(df)
            st.success(f'{selected_item}を {amount} 個、補充しました。')
            st.rerun() # 画面をリロード

if __name__ == '__main__':
    main()
