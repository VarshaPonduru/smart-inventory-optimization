import streamlit as st
import pandas as pd
import joblib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ================= CONFIG =================
st.set_page_config(
    page_title="Inventory Intelligence | Pro", 
    page_icon="📦",
    layout="wide"
)

# ULTIMATE HIGH-CONTRAST CSS
st.markdown("""
    <style>
    /* Force Bright White Background */
    .stApp { background-color: #ffffff !important; }
    
    /* Force Title Visibility */
    h1 { color: #000000 !important; font-weight: 800 !important; }
    
    /* METRIC CARDS - High Contrast */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 20px !important;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1) !important;
    }
    
    /* LARGE SOLID BLACK LABELS */
    [data-testid="stMetricLabel"] div, 
    [data-testid="stMetricLabel"] p {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 1.4rem !important;
        opacity: 1 !important;
        line-height: 1.2 !important;
    }
    
    /* Large Value Text */
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 2.4rem !important;
    }

    /* Section Headers */
    .header-style {
        font-size: 1.5rem;
        font-weight: 800;
        color: #000000;
        margin-top: 30px;
        margin-bottom: 15px;
        border-left: 8px solid #004a99;
        padding-left: 15px;
    }

    /* Professional Sidebar Button */
    .stButton>button {
        background-color: #004a99 !important;
        color: white !important;
        font-weight: 800 !important;
        height: 3.5em !important;
        width: 100%;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ================= ASSETS =================
@st.cache_resource
def load_assets():
    try:
        model = joblib.load('model.pkl')
        df = pd.read_csv('data.csv', low_memory=True)
        df['Date'] = pd.to_datetime(df['Date'])
        return model, df
    except:
        return None, None

model, df = load_assets()
features = ['DayOfWeek', 'Month', 'Day', 'lag_1', 'lag_7', 'rolling_mean_7', 'rolling_mean_14', 'rolling_std_7']

# ================= LOGIC =================
def predict_demand(product_id, model, df, features, days=7):
    p_data = df[df['StockCode'] == product_id].sort_values('Date')
    if p_data.empty: return 0
    last_row = p_data.iloc[-1:].copy()
    preds = []
    for _ in range(days):
        p = max(0, model.predict(last_row[features])[0])
        preds.append(p)
        last_row['lag_1'] = p
    return sum(preds)

def get_restock_status(current, predicted):
    if current < predicted: return "🔴 High Stock-out"
    if current > predicted * 1.5: return "🟡 Overstock"
    return "🟢 Optimized"

# ================= UI =================
st.title("📦 Inventory Control Center")

if df is not None:
    with st.sidebar:
        st.markdown("### **Operational Parameters**")
        product_id = st.selectbox("SKU Selection", sorted(df['StockCode'].unique()))
        current_stock = st.number_input("Warehouse Stock", value=50)
        days = st.selectbox("Forecast Horizon", [7, 30], index=0)
        st.markdown("---")
        run = st.button("🚀 GENERATE REPORT")

    if run:
        p_data = df[df['StockCode'] == product_id].copy()
        demand = predict_demand(product_id, model, df, features, days)
        recommended = max(10, round(demand * 1.2))
        status = get_restock_status(current_stock, demand)
        gap = int(current_stock - demand)
        
        # 1. METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Predicted Demand", f"{int(demand)} Units")
        m2.metric("Recommended Stock", f"{recommended} Units")
        m3.metric("Inventory Status", status)
        m4.metric("Net Gap", f"{gap} Units", delta=gap)

        # 2. CHARTS
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown('<div class="header-style">Demand Forecast Trend</div>', unsafe_allow_html=True)
            data_tail = p_data.tail(30)
            dates_future = pd.date_range(start=data_tail['Date'].iloc[-1], periods=days+1)[1:]
            
            plot_row = data_tail.iloc[-1:].copy()
            future_points = []
            for _ in range(days):
                p = max(0, model.predict(plot_row[features])[0])
                future_points.append(p)
                plot_row['lag_1'] = p

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(data_tail['Date'], data_tail['Quantity'], color='#004a99', label="Historical Sales", linewidth=3)
            ax.plot(dates_future, future_points, color='#f59e0b', linestyle='--', label="AI Forecast", linewidth=3)
            ax.fill_between(data_tail['Date'], data_tail['Quantity'], alpha=0.1, color='#004a99')
            
            # FIX: PREVENT DATE OVERLAP
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.xticks(rotation=45, ha='right', fontweight='bold', fontsize=10)
            
            ax.legend(frameon=False)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.grid(axis='y', alpha=0.3)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        with col_right:
            st.markdown('<div class="header-style">Weekly Cycle</div>', unsafe_allow_html=True)
            p_data['Quantity'] = p_data['Quantity'].clip(lower=0)
            weekly = p_data.groupby('DayOfWeek')['Quantity'].mean().reindex(range(7), fill_value=0)
            day_map = {0:"Mon", 1:"Tue", 2:"Wed", 3:"Thu", 4:"Fri", 5:"Sat", 6:"Sun"}
            
            max_v = weekly.max() if weekly.max() > 0 else 1
            for i, val in weekly.items():
                percent = (val / max_v) * 100
                st.markdown(f"""
                    <div style="margin-bottom:18px;">
                        <div style="color:#000; font-weight:800; font-size:14px; margin-bottom:5px;">
                            {day_map[i]} <span style="float:right; font-weight:500;">{int(val)} units</span>
                        </div>
                        <div style="width:100%; height:12px; background:#e2e8f0; border-radius:6px;">
                            <div style="width:{percent}%; height:100%; background:#004a99; border-radius:6px;"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        # 3. INSIGHTS SECTION
        st.markdown('<div class="header-style">Strategic Insights</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"**Analytics:** Product {product_id} shows a {'rising' if p_data['rolling_mean_7'].iloc[-1] > p_data['rolling_mean_14'].iloc[-1] else 'stable'} velocity trend.")
        with c2:
            if gap < 0:
                st.error(f"**Action:** Shortfall of {abs(gap)} units projected. Immediate restock advised.")
            else:
                st.success("**Inventory Health:** Warehouse levels are sufficient for the selected period.")

    else:
        st.info("👈 Please configure SKU and click 'Generate Report'.")
else:
    st.error("System Error: 'data.csv' or 'model.pkl' not detected.")