# 2. アプリ本体の作成
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ページ設定（ブラウザのタブ名やアイコン）
st.set_page_config(page_title="経営診断", page_icon="🏥", layout="wide")

# タイトルと自己紹介
st.markdown("<h1 style='color: #007BFF;'>医療機器資産・寿命最大化診断</h1>", unsafe_allow_html=True)
st.info("現場の『もったいない』を可視化し、経営変化のシミュレーターです。")

# --- サイドバー：入力エリア ---
with st.sidebar:
    st.header("📊 病院データ入力")
    pump_total = st.number_input("ポンプ総保有台数", value=100, step=10)
    nurse_wage = st.number_input("看護師時給 (円)", value=2500, step=100)
    
    st.markdown("---")
    st.write("🔍 **現場の『あるある』率（推定）**")
    stuck_rate = st.slider("スライド固着を『故障』と誤認する割合 (%)", 0, 50, 15)
    battery_waste = st.slider("バッテリー不安で『早期廃棄』する割合 (%)", 0, 50, 10)
    
    st.markdown("---")
    email = st.text_input("診断結果の送付先（メールアドレス）")

# --- 計算ロジック ---
# 1. 死蔵資産の復活（購入回避）
recovered_count = int(pump_total * (stuck_rate / 100))
saved_purchase = recovered_count * 200000  # ポンプ1台20万計算

# 2. 買い替えサイクルの適正化（5年→7年への延長を想定）
current_annual_cost = (pump_total * 200000) / 5
new_annual_cost = (pump_total * 200000) / 7
life_extension_saving = current_annual_cost - new_annual_cost

# 3. 看護師の管理工数削減（月30分×12ヶ月）
nurse_time_saving_hours = pump_total * 0.5 * 12
nurse_time_saving_value = nurse_time_saving_hours * nurse_wage

# 合計インパクト
total_impact = saved_purchase + life_extension_saving + nurse_time_saving_value

# --- メイン表示エリア ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("死蔵資産の復活", f"{recovered_count} 台", delta="復活可能")
    st.caption("清拭・注油で現役復帰できる台数")

with col2:
    st.metric("初年度の経営改善期待額", f"¥{int(total_impact/10000):,}万円", delta="利益創出")
    st.caption("購入回避・寿命延長・人件費の合計")

with col3:
    st.metric("看護現場への還元時間", f"{int(nurse_time_saving_hours)} 時間/年", delta="負担軽減")
    st.caption("看護師が本来の業務に集中できる時間")

st.markdown("---")

# 比較グラフの作成
fig = go.Figure(data=[
    go.Bar(name='現状 (対策なし)', x=['年間運用コスト'], y=[current_annual_cost + nurse_time_saving_value], marker_color='#ef5350'),
    go.Bar(name='miratech導入後', x=['年間運用コスト'], y=[new_annual_cost], marker_color='#66bb6a')
])
fig.update_layout(barmode='group', title='運用コストの劇的変化（シミュレーション）', height=400)
st.plotly_chart(fig, use_container_width=True)

# 事務長への決め台詞
st.success(f"""
### 💡 診断結果に基づく提言
事務長、貴院では年間で **約{int(total_impact/10000):,}万円** の価値が、機器の「汚れ」や「管理不足」によって失われている可能性があります。
miratech Ryukyuは、修理ではなく**『コンディショニング（清拭・注油・精度確認）』**によって、この損失を利益に変えるお手伝いをいたします。
""")

if st.button("この診断結果でレポートを予約する"):
    if email:
        st.write(f"✅ ありがとうございます。{email} 宛に詳細なプランをお送りします。")
    else:
        st.warning("メールアドレスを入力してください。")
