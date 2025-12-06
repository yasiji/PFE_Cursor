"""SKU Detail page for Streamlit dashboard."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from apps.streamlit.utils import (
    load_daily_aggregated_data,
    load_lightgbm_model,
    load_feature_importance
)


def render():
    """Render the SKU Detail page."""
    st.title("📦 SKU Detail")
    st.markdown("---")
    
    # Load data
    with st.spinner("Loading data..."):
        df_daily, column_map = load_daily_aggregated_data()
        model_data = load_lightgbm_model()
        feature_importance = load_feature_importance()
    
    if df_daily.empty:
        st.error("No data available. Please ensure MVP data is loaded.")
        return
    
    store_col = column_map['store_col']
    sku_col = column_map['sku_col']
    date_col = column_map['date_col']
    
    # Store and SKU selection
    stores = sorted(df_daily[store_col].unique())
    selected_store = st.selectbox("Select Store", stores, index=0)
    
    # Filter SKUs for selected store
    store_skus = sorted(df_daily[df_daily[store_col] == selected_store][sku_col].unique())
    if not store_skus:
        st.warning(f"No SKUs found for store {selected_store}")
        return
    
    selected_sku = st.selectbox("Select SKU", store_skus, index=0)
    
    # Filter data for selected store-SKU
    sku_data = df_daily[
        (df_daily[store_col] == selected_store) & 
        (df_daily[sku_col] == selected_sku)
    ].copy().sort_values(date_col)
    
    if sku_data.empty:
        st.warning(f"No data found for Store {selected_store} - SKU {selected_sku}")
        return
    
    st.markdown("---")
    
    # SKU KPIs
    st.subheader(f"📊 Store {selected_store} - SKU {selected_sku}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_demand = sku_data['demand'].sum()
    avg_daily_demand = sku_data['demand'].mean()
    max_daily_demand = sku_data['demand'].max()
    total_days = len(sku_data)
    
    with col1:
        st.metric("Total Demand", f"{total_demand:,.0f}")
    with col2:
        st.metric("Avg Daily Demand", f"{avg_daily_demand:.2f}")
    with col3:
        st.metric("Max Daily Demand", f"{max_daily_demand:.0f}")
    with col4:
        st.metric("Days Active", f"{total_days}")
    
    st.markdown("---")
    
    # Time Series Plot
    st.subheader("📅 Demand Time Series")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Daily Demand")
        fig = px.line(
            sku_data,
            x=date_col,
            y='demand',
            title=f"Store {selected_store} - SKU {selected_sku} - Daily Demand",
            labels={'demand': 'Demand', date_col: 'Date'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Demand Distribution")
        fig = px.histogram(
            sku_data,
            x='demand',
            title="Demand Distribution",
            labels={'demand': 'Demand', 'count': 'Frequency'},
            nbins=30
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Statistics
    st.markdown("---")
    st.subheader("📈 Demand Statistics")
    
    stats = {
        'Mean': sku_data['demand'].mean(),
        'Median': sku_data['demand'].median(),
        'Std Dev': sku_data['demand'].std(),
        'Min': sku_data['demand'].min(),
        'Max': sku_data['demand'].max(),
        '25th Percentile': sku_data['demand'].quantile(0.25),
        '75th Percentile': sku_data['demand'].quantile(0.75),
    }
    
    stats_df = pd.DataFrame([stats]).T
    stats_df.columns = ['Value']
    st.dataframe(
        stats_df.style.format('{:.2f}'),
        width='stretch'
    )
    
    # Feature Importance (if available)
    if feature_importance is not None and not feature_importance.empty:
        st.markdown("---")
        st.subheader("🎯 Feature Importance")
        
        # Show top features
        top_features = feature_importance.head(20).sort_values('importance', ascending=True)
        
        fig = px.bar(
            top_features,
            x='importance',
            y='feature',
            orientation='h',
            title="Top 20 Features by Importance",
            labels={'importance': 'Importance', 'feature': 'Feature'}
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # Model Information
    if model_data is not None:
        st.markdown("---")
        st.subheader("🤖 Model Information")
        
        with st.expander("View Model Details"):
            st.json({
                'model_name': model_data.get('name', 'lightgbm'),
                'num_features': len(model_data.get('feature_cols', [])),
                'model_type': 'LightGBM'
            })
            
            if 'feature_cols' in model_data:
                st.markdown("**Features:**")
                st.write(", ".join(model_data['feature_cols'][:20]))
                if len(model_data['feature_cols']) > 20:
                    st.write(f"... and {len(model_data['feature_cols']) - 20} more")

