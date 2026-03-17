import streamlit as st
import pandas as pd
import plotly.express as px
from utils import get_processed_data

# Page Config
st.set_page_config(page_title="SBM Traders Dashboard", layout="wide")

# Title
st.title("📊 SBM Traders - Payment Dashboard")

# Load Data
DATA_PATH = 'Customer_Payment.xlsx'

# Sidebar: Refresh Button & Info
with st.sidebar:
    st.header("Controls")
    if st.button('🔄 Refresh Data'):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.info("""
    **Auto-Update Guide:**
    1. Edit & Save `Customer_Payment.xlsx`.
    2. Click 'Refresh Data' above or reload the page.
    """)

# Load logic with caching
@st.cache_data
def load_and_process_data(path):
    return get_processed_data(path)

try:
    df = load_and_process_data(DATA_PATH)
except Exception as e:
    st.error(f"Error loading data: {e}. Please make sure 'Customer_Payment.xlsx' exists.")
    st.stop()

if df is None:
    st.error("Failed to load data. Please check the file.")
    st.stop()

# --- KPI Section ---
st.markdown("### Key Metrics")
col1, col2, col3 = st.columns(3)

total_amount = df['Amount'].sum()
total_unused = df['Unused Amount'].sum()
avg_delay = df[df['Late_Only_Delay'] > 0]['Late_Only_Delay'].mean()

col1.metric("Total Payment Received", f"₹{total_amount:,.2f}")
col2.metric("Total Outstanding Amount", f"₹{total_unused:,.2f}")
val_delay = f"{avg_delay:.1f} Days" if not pd.isna(avg_delay) else "0 Days"
col3.metric("Avg Delay (Late Payments)", val_delay)

st.markdown("---")

# --- 1. Top Customers (Most Orders) ---
st.subheader("🏆 Top Customers by Order Amount")

# Group by CustomerID and Name, sum Amount
# We use Name as label, ID for uniqueness if needed, but grouping by Name is usually preferred for display
top_customers = df.groupby(['CustomerID', 'Customer Name'])['Amount'].sum().reset_index()
top_customers = top_customers.sort_values(by='Amount', ascending=False)
top_10_customers = top_customers.head(10)

# Bar Chart
fig_top = px.bar(
    top_10_customers, 
    x='Amount', 
    y='Customer Name', 
    orientation='h', 
    text='Amount',
    title="Top 10 Customers by Total Payment Received",
    # Color mapping
    color='Amount',
    color_continuous_scale='Viridis'
)
fig_top.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig_top, use_container_width=True)

# --- 2. Delayed Payments ---
st.subheader("⚠️ Delayed Payments")

# Filter: Late_Only_Delay > 0
delayed_df = df[df['Late_Only_Delay'] > 0].copy()

if not delayed_df.empty:
    st.write(f"Found **{len(delayed_df)}** transactions with payment delays.")
    
    tab1, tab2 = st.tabs(["📋 Detailed List", "📊 Delay Analysis"])
    
    with tab1:
        st.write("#### Detailed Delayed Transactions")
        display_cols = ['Date', 'Invoice Date', 'Customer Name', 'Amount', 'Delay', 'Late_Only_Delay']
        st.dataframe(
            delayed_df[display_cols].sort_values(by='Delay', ascending=False),
            use_container_width=True
        )
        
    with tab2:
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.write("#### Top Defaulters (Average Delay)")
            avg_delay_by_customer = delayed_df.groupby('Customer Name')['Late_Only_Delay'].mean().reset_index()
            # Rename for display
            avg_delay_by_customer.rename(columns={'Late_Only_Delay': 'Avg Delay (Days)'}, inplace=True)
            avg_delay_by_customer = avg_delay_by_customer.sort_values(by='Avg Delay (Days)', ascending=False).head(10)
            
            fig_delay = px.bar(
                avg_delay_by_customer, 
                x='Avg Delay (Days)', 
                y='Customer Name', 
                orientation='h',
                color='Avg Delay (Days)',
                color_continuous_scale='Reds'
            )
            fig_delay.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_delay, use_container_width=True)
            
        with col_d2:
             st.write("#### Delay Distribution")
             fig_hist = px.histogram(delayed_df, x="Late_Only_Delay", nbins=20, title="Distribution of Delay Days")
             st.plotly_chart(fig_hist, use_container_width=True)

else:
    st.success("✅ No delayed payments found!")

# --- 3. Pending Payments (Unpaid Invoices) ---
st.subheader("⏳ Pending Payments (Unpaid)")

# Filter for Pending
pending_df = df[df['Payment_Status'] == 'Pending'].copy()

if not pending_df.empty:
    st.warning(f"Found **{len(pending_df)}** pending invoices (No Payment Date). Delay is calculated from today.")
    
    # Display table
    st.dataframe(
        pending_df[['Invoice Date', 'Customer Name', 'Amount', 'Unused Amount', 'Delay']].sort_values(by='Delay', ascending=False),
        use_container_width=True
    )
    
    # Metric for total pending
    st.metric("Total Pending Amount", f"₹{pending_df['Amount'].sum():,.2f}")

else:
    st.success("✅ No pending invoices found in the dataset.")
