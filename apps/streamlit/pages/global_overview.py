"""Global Overview page for Streamlit dashboard."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apps.streamlit.utils import (
    load_daily_aggregated_data,
    load_simulation_results,
    load_baseline_results,
    load_lightgbm_results
)


def render():
    """Render the Global Overview page."""
    st.title("📊 Global Overview")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df_daily, column_map = load_daily_aggregated_data()
        sim_results = load_simulation_results()
        baseline_results = load_baseline_results()
        lightgbm_results = load_lightgbm_results()
    
    if df_daily.empty:
        st.error("No data available. Please ensure MVP data is loaded.")
        return
    
    store_col = column_map['store_col']
    sku_col = column_map['sku_col']
    date_col = column_map['date_col']
    
    # Key Metrics Row
    st.subheader("📈 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_demand = df_daily['demand'].sum()
    total_stores = df_daily[store_col].nunique()
    total_skus = df_daily[sku_col].nunique()
    avg_daily_demand = df_daily.groupby(date_col)['demand'].sum().mean()
    
    with col1:
        st.metric("Total Demand", f"{total_demand:,.0f}")
    with col2:
        st.metric("Stores", f"{total_stores}")
    with col3:
        st.metric("SKUs", f"{total_skus}")
    with col4:
        st.metric("Avg Daily Demand", f"{avg_daily_demand:.1f}")
    
    st.markdown("---")
    
    # Model Performance Comparison
    st.subheader("🎯 Model Performance")
    
    if lightgbm_results is not None and baseline_results is not None and not baseline_results.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Baseline Models")
            baseline_df = pd.DataFrame(baseline_results)
            if not baseline_df.empty:
                # Handle column names - check if 'model' exists, otherwise use first column
                display_cols = ['mae', 'mape', 'rmse']
                if 'model' in baseline_df.columns:
                    display_cols = ['model'] + display_cols
                elif baseline_df.columns[0] == 'Unnamed: 0':
                    # Rename first column to 'model' for display
                    baseline_df = baseline_df.rename(columns={baseline_df.columns[0]: 'model'})
                    display_cols = ['model'] + display_cols
                
                # Only use columns that exist
                available_cols = [col for col in display_cols if col in baseline_df.columns]
                st.dataframe(
                    baseline_df[available_cols].style.format({
                        'mae': '{:.3f}',
                        'mape': '{:.2f}%',
                        'rmse': '{:.3f}'
                    }),
                    width='stretch'
                )
        
        with col2:
            st.markdown("### LightGBM Model")
            if isinstance(lightgbm_results, dict):
                metrics = lightgbm_results.get('metrics', {})
                if metrics:
                    st.metric("MAE", f"{metrics.get('mae', 0):.3f}")
                    st.metric("MAPE", f"{metrics.get('mape', 0):.2f}%")
                    st.metric("RMSE", f"{metrics.get('rmse', 0):.3f}")
                    st.metric("Improvement", f"{metrics.get('mae_improvement', 0):.1f}%")
    
    st.markdown("---")
    
    # Time Series Analysis
    st.subheader("📅 Time Series Analysis")
    
    # Aggregate by date
    daily_agg = df_daily.groupby(date_col)['demand'].agg(['sum', 'mean', 'count']).reset_index()
    daily_agg.columns = ['date', 'total_demand', 'avg_demand', 'transactions']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Total Daily Demand")
        fig = px.line(
            daily_agg,
            x='date',
            y='total_demand',
            title="Total Daily Demand Over Time",
            labels={'total_demand': 'Total Demand', 'date': 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Average Daily Demand per Store-SKU")
        fig = px.line(
            daily_agg,
            x='date',
            y='avg_demand',
            title="Average Daily Demand",
            labels={'avg_demand': 'Avg Demand', 'date': 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Category Analysis
    if 'category_col' in column_map:
        category_col = column_map['category_col']
        if category_col in df_daily.columns:
            st.markdown("---")
            st.subheader("📦 Category Analysis")
            
            category_stats = df_daily.groupby(category_col).agg({
                'demand': ['sum', 'mean', 'count'],
                sku_col: 'nunique'
            }).reset_index()
            category_stats.columns = ['category', 'total_demand', 'avg_demand', 'transactions', 'unique_skus']
            category_stats = category_stats.sort_values('total_demand', ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Top Categories by Demand")
                fig = px.bar(
                    category_stats.head(10),
                    x='category',
                    y='total_demand',
                    title="Top 10 Categories by Total Demand",
                    labels={'total_demand': 'Total Demand', 'category': 'Category ID'}
                )
                fig.update_layout(height=400, xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("### Category Statistics")
                st.dataframe(
                    category_stats.style.format({
                        'total_demand': '{:,.0f}',
                        'avg_demand': '{:.2f}',
                        'transactions': '{:,.0f}',
                        'unique_skus': '{:.0f}'
                    }),
                    width='stretch'
                )
    
    # Simulation Results
    if sim_results is not None and isinstance(sim_results, pd.DataFrame) and not sim_results.empty:
        st.markdown("---")
        st.subheader("🧪 Simulation Results")
        
        if 'policy' in sim_results.columns:
            policy_comparison = sim_results.copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Policy Comparison")
                comparison_cols = ['policy', 'service_level_pct', 'waste_pct', 'stockout_pct']
                available_cols = [col for col in comparison_cols if col in policy_comparison.columns]
                if available_cols:
                    st.dataframe(
                        policy_comparison[available_cols].style.format({
                            'service_level_pct': '{:.2f}%',
                            'waste_pct': '{:.2f}%',
                            'stockout_pct': '{:.2f}%'
                        }),
                        width='stretch'
                    )
            
            with col2:
                st.markdown("### Waste Rate Comparison")
                if 'waste_pct' in policy_comparison.columns and 'policy' in policy_comparison.columns:
                    fig = px.bar(
                        policy_comparison,
                        x='policy',
                        y='waste_pct',
                        title="Waste Rate by Policy",
                        labels={'waste_pct': 'Waste Rate (%)', 'policy': 'Policy'}
                    )
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)

