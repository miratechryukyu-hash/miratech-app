import streamlit as st
import pandas as pd

# ページ設定
st.set_page_config(page_title="ミラテック琉球 コスト削減予想", layout="wide")

# ==========================================
# 📊 左側：サイドバー（病院データ入力）
# ==========================================
with st.sidebar:
    st.header("🏥 病院データ入力")
    
    # 診断対象の切り替え
    target_device = st.selectbox(
        "🔍 診断する機器を選択",
        ["輸液・シリンジポンプ", "人工呼吸器", "生体情報モニター", "その他"]
    )
    
    st.markdown("---")
    
    # 台数ベースの入力
    total_units = st.number_input(f"{target_device} 総保有台数", min_value=1, value=100, step=10)
    
    st.markdown(f"### 🔍 {target_device} の現状")
    # %ではなく台数で指定
    stuck_units = st.slider("軽微な不具合で放置・故障判断されている台数", 0, total_units, int(total_units * 0.15))
    battery_units = st.slider("バッテリー不安で早期廃棄・更新予定の台数", 0, total_units, int(total_units * 0.10))
    
    st.markdown("---")
    trouble_time = st.number_input("トラブル1件あたりの現場対応時間 (分)", min_value=5, value=30, step=5)
    
    # 計算用の裏パラメータ（機器ごとに単価を変える設定）
    price_map = {
        "輸液・シリンジポンプ": {"new": 0, "repair": 5}, # 新規30万, 修理5万
        "人工呼吸器": {"new": 300, "repair": 50},       # 新規300万, 修理50万
        "生体情報モニター": {"new": 80, "repair": 15},    # 新規80万, 修理15万
        "その他": {"new": 50, "repair": 10}
    }
    unit_price = price_map[target_device]

# ==========================================
# 📈 メインダッシュボード
# ==========================================
st.title(f"ミラテック　コスト削減予想")
st.subheader(f"対象：{target_device}")

# 計算ロジック（単位を「万円」で統一）
# 1. 復活可能（新規購入回避）による利益
profit_recovery = stuck_units * unit_price["new"]
# 2. 寿命延長（早期廃棄回避）による利益
profit_battery = battery_units * unit_price["new"]
# 合計利益
profit_total_man = profit_recovery + profit_battery

# 時間計算
time_saved_hours = int((total_units * 12 * trouble_time) / 60)

# 表示
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("資産復活（現役復帰）", f"{stuck_units} 台", f"{target_device}")
    st.caption("清拭・注油・簡易点検で継続使用可能な台数")

with col2:
    # 単位を「万円」に固定し、大きな数字になりすぎないよう調整
    st.metric("期待される経営改善効果", f"¥ {profit_total_man:,} 万円", "資産価値の最大化")
    st.caption("新規購入の抑制および減価償却費の最適化")

with col3:
    st.metric("現場の創出可能時間", f"{time_saved_hours:,} 時間/年", "働き方改革")
    st.caption("看護師が本来の業務に集中できる時間")

# ==========================================
# 💰 運用コスト比較
# ==========================================
st.markdown("---")
st.subheader("🛠️ 具体的コスト削減プラン")

c1, c2 = st.columns(2)
with c1:
    maker_cost = st.slider("🏢 メーカー修理代/保守代 (万円)", 1, 100, unit_price["repair"])
    miratech_cost = st.slider("🔧 ミラテック 修理代/保守代 (万円)", 1, 100, int(unit_price["repair"] * 0.6))
    annual_cases = st.slider("📅 年間の修理・点検依頼件数 (件)", 1, 200, 20)

    total_m = maker_cost * annual_cases
    total_mi = miratech_cost * annual_cases
    diff = total_m - total_mi

with c2:
    st.info(f"ミラテック琉球への切り替えによる年間削減額")
    st.markdown(f"<h1 style='color: #ff4b4b; text-align: center;'>¥ {diff:,} 万円</h1>", unsafe_allow_html=True)
    
    # グラフ用データ
    chart_data = pd.DataFrame({
        "プラン": ["現状 (メーカー等)", "ミラテック導入後"],
        "コスト (万円)": [total_m, total_mi]
    }).set_index("プラン")
    st.bar_chart(chart_data)

# ==========================================
# 📑 経営報告用サマリー
# ==========================================
with st.expander("📝 院長・事務長への提案用データを確認"):
    st.write(f"今回の診断に基づき、**{target_device}** の管理をミラテック琉球へ委託することで、")
    st.write(f"1. **資産の有効活用**: 年間 ¥{profit_total_man}万円 相当の新規投資を抑制。")
    st.write(f"2. **直接コストの適正化**: 外部委託費を年間 ¥{diff}万円 削減。")
    st.write(f"3. **人的リソースの最適化**: 看護師の雑務時間を年間 {time_saved_hours}時間 削減します。")
