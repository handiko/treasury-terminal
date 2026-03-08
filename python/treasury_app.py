import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIG & PERSISTENT DATA ---
st.set_page_config(page_title="Treasury Monitoring Terminal", layout="wide")

# Optional custom CSS for a polished look
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .metric-card {
        background-color: #1e2130;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialise session state
if 'treasury' not in st.session_state:
    st.session_state.treasury = {
        "Local_Wallet": {"USDT": 400000, "Min_Threshold": 150000},
        "Global_Exchange": {"USDT": 600000, "Min_Threshold": 200000}
    }
    st.session_state.logs = []   # will store dicts

# Constants
TARGET_LOCAL_RATIO = 0.40        # 40% Local, 60% Global
DRIFT_BAND = 0.05                 # 5% deviation allowed
NETWORK_FEES = {"TRC20": 1.0, "ERC20": 15.0, "SOL": 0.01}

# --- 2. LOGIC ENGINE ---
def calculate_metrics():
    local_usdt = st.session_state.treasury["Local_Wallet"]["USDT"]
    global_usdt = st.session_state.treasury["Global_Exchange"]["USDT"]
    total_usdt = local_usdt + global_usdt

    current_ratio = local_usdt / total_usdt if total_usdt > 0 else 0

    # Health score: 0-100 based on local wallet vs its minimum threshold
    # 50% health when local = min_threshold
    health = (local_usdt / st.session_state.treasury["Local_Wallet"]["Min_Threshold"]) * 50
    health = min(100, max(0, health))

    return total_usdt, current_ratio, health

def execute_move(amount, direction, fee_type="TRC20"):
    """Move funds and log the transaction with balances."""
    fee = NETWORK_FEES[fee_type]

    if direction == "Global -> Local":
        st.session_state.treasury["Global_Exchange"]["USDT"] -= (amount + fee)
        st.session_state.treasury["Local_Wallet"]["USDT"] += amount
    else:  # Local -> Global
        st.session_state.treasury["Local_Wallet"]["USDT"] -= (amount + fee)
        st.session_state.treasury["Global_Exchange"]["USDT"] += amount

    # Structured log entry
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": direction,
        "amount": amount,
        "fee": fee,
        "local_balance": st.session_state.treasury["Local_Wallet"]["USDT"],
        "global_balance": st.session_state.treasury["Global_Exchange"]["USDT"]
    }
    st.session_state.logs.insert(0, log_entry)

# --- 3. UI LAYOUT ---
st.title("🏦 Smart Treasury Monitoring Terminal")
total, ratio, health_score = calculate_metrics()

# --- TOP ROW: KPI Dashboard ---
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric("Total Reserves", f"{total:,.2f} USDT")
    st.caption("Combined local + global")

with kpi2:
    st.metric("Liquidity Health", f"{health_score:.1f}%", delta=f"{health_score - 100:.1f}%")
    st.caption("100% when local ≥ 2× min threshold")

with kpi3:
    delta_ratio = (ratio - TARGET_LOCAL_RATIO) * 100
    st.metric("Local Ratio", f"{ratio * 100:.1f}%", delta=f"{delta_ratio:.1f}% vs target")
    st.caption(f"Target: {TARGET_LOCAL_RATIO*100:.0f}%")

# --- MIDDLE ROW: Visualizations & Threshold Info ---
col_viz1, col_viz2 = st.columns([1, 1])

with col_viz1:
    # Drift Gauge with threshold lines
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ratio * 100,
        title={'text': "Local Allocation %"},
        gauge={
            'axis': {'range': [0, 100]},
            'steps': [
                {'range': [0, 35], 'color': "#ff4b4b"},
                {'range': [35, 45], 'color': "#00d1b2"},
                {'range': [45, 100], 'color': "#ff4b4b"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'value': TARGET_LOCAL_RATIO * 100
            }
        }
    ))
    fig_gauge.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10), template="plotly_dark")
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Show minimum thresholds below gauge
    local_min = st.session_state.treasury["Local_Wallet"]["Min_Threshold"]
    global_min = st.session_state.treasury["Global_Exchange"]["Min_Threshold"]
    st.caption(f"🔹 Local min: {local_min:,.0f} USDT  |  Global min: {global_min:,.0f} USDT")

with col_viz2:
    # Distribution Pie
    fig_pie = go.Figure(go.Pie(
        labels=["Local Wallet", "Global Exchange"],
        values=[st.session_state.treasury["Local_Wallet"]["USDT"],
                st.session_state.treasury["Global_Exchange"]["USDT"]],
        hole=.5,
        marker_colors=['#00d1b2', '#209cee'],
        textinfo='label+percent'
    ))
    fig_pie.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10), template="plotly_dark")
    st.plotly_chart(fig_pie, use_container_width=True)

# --- SIDEBAR: Controls & Stress Test ---
st.sidebar.header("🕹️ Control Center")

# Stress test (custom amount)
with st.sidebar.expander("💥 Stress Test", expanded=False):
    outflow = st.number_input("Outflow Amount (USDT)", min_value=0, value=200000, step=10000)
    if st.button("Apply Outflow to Local Wallet"):
        st.session_state.treasury["Local_Wallet"]["USDT"] -= outflow
        st.session_state.logs.insert(0, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "STRESS TEST",
            "amount": outflow,
            "fee": 0,
            "local_balance": st.session_state.treasury["Local_Wallet"]["USDT"],
            "global_balance": st.session_state.treasury["Global_Exchange"]["USDT"]
        })
        st.rerun()

# Manual transfer
with st.sidebar.expander("🔁 Manual Transfer", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        amount = st.number_input("Amount (USDT)", min_value=0, value=10000, step=1000)
    with col2:
        direction = st.selectbox("Direction", ["Local → Global", "Global → Local"])
    fee_type = st.selectbox("Network", list(NETWORK_FEES.keys()))
    if st.button("Execute Transfer"):
        # Convert display direction to internal format
        dir_internal = "Local -> Global" if direction == "Local → Global" else "Global -> Local"
        execute_move(amount, dir_internal, fee_type)
        st.rerun()

# Reset button
if st.sidebar.button("♻️ Reset Treasury", type="primary"):
    del st.session_state.treasury
    del st.session_state.logs
    st.rerun()

# --- AUTO-PILOT REBALANCING ADVISOR (prominent placement) ---
st.divider()
st.subheader("🤖 Auto-Pilot Rebalancing Advisor")

target_local_val = total * TARGET_LOCAL_RATIO
drift_val = target_local_val - st.session_state.treasury["Local_Wallet"]["USDT"]
drift_percent = abs(drift_val) / total * 100 if total > 0 else 0

if abs(drift_val) > (total * DRIFT_BAND):
    dir_rec = "Global -> Local" if drift_val > 0 else "Local -> Global"
    with st.container():
        st.warning(f"⚠️ **Drift Detected!** Deviation: {drift_percent:.1f}% (allowed band: {DRIFT_BAND*100:.0f}%)")
        if st.button(f"Execute Recommended Move: {abs(drift_val):,.0f} USDT ({dir_rec})", type="primary"):
            execute_move(abs(drift_val), dir_rec)
            st.success("Target parity restored.")
            st.rerun()
else:
    st.success(f"✅ System Balanced – within {DRIFT_BAND*100:.0f}% drift band.")

# --- LOGS ---
with st.expander("📜 Operation Logs", expanded=True):
    if st.button("Clear Logs"):
        st.session_state.logs = []
        st.rerun()

    if st.session_state.logs:
        # Convert logs to DataFrame for better display
        logs_df = pd.DataFrame(st.session_state.logs)
        # Reorder columns for readability
        logs_df = logs_df[["timestamp", "action", "amount", "fee", "local_balance", "global_balance"]]
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("No operations logged yet.")
