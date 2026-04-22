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
# ==========================================
# ✨ タブ6：経営改善シミュレーター
# ==========================================
with tab6:
    st.subheader("📊 経営改善シミュレーター")
    st.write("ミラテック琉球の介入による「直接的なコスト削減」と、現場スタッフの「業務時間削減（時間創出）」を試算します。")

    st.markdown("### 💰 1. 直接コストの削減（修理代・保守代）")
    col_sim1, col_sim2 = st.columns(2)
    
    with col_sim1:
        st.write("▼ 条件を入力してください")
        maker_cost = st.slider("🏢 メーカー修理代 / 1回 (万円)", min_value=1, max_value=30, value=10, key="sim_maker")
        miratech_cost = st.slider("🔧 ミラテック 修理代 / 1回 (万円)", min_value=1, max_value=30, value=5, key="sim_mira")
        repair_count = st.slider("📅 年間の想定修理件数 (件)", min_value=1, max_value=100, value=12, key="sim_count")

    maker_total = maker_cost * repair_count
    miratech_total = miratech_cost * repair_count
    savings = maker_total - miratech_total

    with col_sim2:
        st.write("▼ 予想される削減効果")
        st.info(f"💡 1回あたりの削減額: **{maker_cost - miratech_cost} 万円**")
        st.success("✨ 年間コスト削減額 ✨")
        st.markdown(f"<h1 style='text-align: center; color: #ff4b4b; font-size: 3.5rem;'>{savings} 万円</h1>", unsafe_allow_html=True)

    st.markdown("---")
    
    st.markdown("### ⏳ 2. 現場スタッフの時間創出（業務効率化）")
    st.write("機器を探す時間、故障時の報告書作成、業者への電話連絡などにかかる「見えないコスト（時間）」を可視化します。")
    
    col_time1, col_time2 = st.columns(2)
    with col_time1:
        time_current = st.slider("現状：機器トラブル1件の対応時間 (分)", min_value=5, max_value=120, value=30, step=5)
        st.caption("※機器探し、紙の報告書作成、引継ぎ、業者手配など")
        time_miratech = st.slider("導入後：アプリ報告にかかる時間 (分)", min_value=1, max_value=10, value=2, step=1)
        st.caption("※スマホでQR読み込みからワンタッチ送信まで")
        incident_count = st.slider("年間トラブル・問い合わせ件数 (件)", min_value=10, max_value=500, value=50, step=10)

    # 時間計算
    time_saved_minutes = (time_current - time_miratech) * incident_count
    time_saved_hours = time_saved_minutes / 60
    shifts_saved = time_saved_hours / 8  # 8時間労働換算

    with col_time2:
        st.success("✨ 年間で生み出される看護時間 ✨")
        st.markdown(f"<h1 style='text-align: center; color: #00b4d8; font-size: 3.5rem;'>{time_saved_hours:.1f} 時間</h1>", unsafe_allow_html=True)
        st.info(f"💡 日勤シフト **約 {shifts_saved:.1f} 日分** の労働時間に相当！\n\nこの時間を**患者様へのケア**や、**スタッフの残業削減**に充てることができます。")
        
    st.markdown("---")
    st.write("### 📈 導入効果のまとめ")
    df_summary = pd.DataFrame({
        "指標": ["直接コスト削減", "業務時間の創出", "期待される経営効果"],
        "効果": [f"年間 {savings}万円", f"年間 {time_saved_hours:.1f}時間", "新規機器購入の原資化、残業代削減、離職率低下"]
    })
    st.dataframe(df_summary, hide_index=True, use_container_width=True)

if st.button("この診断結果でレポートを予約する"):
    if email:
        st.write(f"✅ ありがとうございます。{email} 宛に詳細なプランをお送りします。")
    else:
        st.warning("メールアドレスを入力してください。")
