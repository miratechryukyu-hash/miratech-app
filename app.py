# ==========================================
# ✨ 経営改善シミュレーター（タブなし版）
# ==========================================
st.markdown("---")
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
