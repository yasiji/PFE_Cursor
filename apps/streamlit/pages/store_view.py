"""Store View page for Streamlit dashboard."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apps.streamlit.utils import load_daily_aggregated_data


def render():
    """Render the Store View page."""
    st.title("🏪 Store View")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df_daily, column_map = load_daily_aggregated_data()
    
    if df_daily.empty:
        st.error("No data available. Please ensure MVP data is loaded.")
        return
    
    store_col = column_map['store_col']
    sku_col = column_map['sku_col']
    date_col = column_map['date_col']
    
    # Store selection
    stores = sorted(df_daily[store_col].unique())
    selected_store = st.selectbox("Select Store", stores, index=0)
    
    # Filter data for selected store
    store_data = df_daily[df_daily[store_col] == selected_store].copy()
    
    st.markdown("---")
    
    # Store KPIs
    st.subheader(f"📊 Store {selected_store} - Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_demand = store_data['demand'].sum()
    total_skus = store_data[sku_col].nunique()
    avg_daily_demand = store_data.groupby(date_col)['demand'].sum().mean()
    total_days = store_data[date_col].nunique()
    
    with col1:
        st.metric("Total Demand", f"{total_demand:,.0f}")
    with col2:
        st.metric("SKUs", f"{total_skus}")
    with col3:
        st.metric("Avg Daily Demand", f"{avg_daily_demand:.1f}")
    with col4:
        st.metric("Days Active", f"{total_days}")
    
    st.markdown("---")
    
    # Store Performance Over Time
    st.subheader("📅 Store Performance Over Time")
    
    store_daily = store_data.groupby(date_col)['demand'].agg(['sum', 'mean', 'count']).reset_index()
    store_daily.columns = ['date', 'total_demand', 'avg_demand', 'transactions']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Daily Total Demand")
        fig = px.line(
            store_daily,
            x='date',
            y='total_demand',
            title=f"Store {selected_store} - Daily Total Demand",
            labels={'total_demand': 'Total Demand', 'date': 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Daily Average Demand per SKU")
        fig = px.line(
            store_daily,
            x='date',
            y='avg_demand',
            title=f"Store {selected_store} - Daily Avg Demand",
            labels={'avg_demand': 'Avg Demand', 'date': 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Top SKUs
    st.subheader("📦 Top SKUs by Demand")
    
    sku_stats = store_data.groupby(sku_col).agg({
        'demand': ['sum', 'mean', 'count']
    }).reset_index()
    sku_stats.columns = ['sku', 'total_demand', 'avg_demand', 'transactions']
    sku_stats = sku_stats.sort_values('total_demand', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Top 10 SKUs")
        fig = px.bar(
            sku_stats.head(10),
            x='sku',
            y='total_demand',
            title=f"Store {selected_store} - Top 10 SKUs",
            labels={'total_demand': 'Total Demand', 'sku': 'SKU ID'}
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### SKU Statistics")
        st.dataframe(
            sku_stats.head(20).style.format({
                'total_demand': '{:,.0f}',
                'avg_demand': '{:.2f}',
                'transactions': '{:,.0f}'
            }),
            width='stretch'
        )
    
    st.markdown("---")
    
    # Store Comparison
    st.subheader("🏆 Store Ranking")
    
    store_ranking = df_daily.groupby(store_col).agg({
        'demand': ['sum', 'mean'],
        sku_col: 'nunique',
        date_col: 'nunique'
    }).reset_index()
    store_ranking.columns = ['store', 'total_demand', 'avg_demand', 'unique_skus', 'active_days']
    store_ranking = store_ranking.sort_values('total_demand', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Store Ranking by Total Demand")
        fig = px.bar(
            store_ranking,
            x='store',
            y='total_demand',
            title="All Stores - Total Demand Ranking",
            labels={'total_demand': 'Total Demand', 'store': 'Store ID'}
        )
        fig.update_layout(height=400, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Store Statistics")
        st.dataframe(
            store_ranking.style.format({
                'total_demand': '{:,.0f}',
                'avg_demand': '{:.2f}',
                'unique_skus': '{:.0f}',
                'active_days': '{:.0f}'
            }),
            width='stretch'
        )
    
    # Highlight selected store
    if selected_store in store_ranking['store'].values:
        selected_rank = store_ranking[store_ranking['store'] == selected_store].index[0] + 1
        st.info(f"📌 Store {selected_store} is ranked **#{selected_rank}** out of {len(store_ranking)} stores by total demand.")

