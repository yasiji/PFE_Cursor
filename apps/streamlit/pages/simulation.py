"""Simulation/Sandbox page for Streamlit dashboard."""

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
    load_lightgbm_model
)
from shared.config import get_config

config = get_config()


def render():
    """Render the Simulation/Sandbox page."""
    st.title("🧪 Simulation & Sandbox")
    st.markdown("---")
    st.markdown("""
    This page allows you to explore different scenarios and see their impact on forecasts and replenishment recommendations.
    """)
    
    # Load data
    with st.spinner("Loading data..."):
        df_daily, column_map = load_daily_aggregated_data()
        sim_results = load_simulation_results()
        model_data = load_lightgbm_model()
    
    if df_daily.empty:
        st.error("No data available. Please ensure MVP data is loaded.")
        return
    
    store_col = column_map['store_col']
    sku_col = column_map['sku_col']
    date_col = column_map['date_col']
    
    st.markdown("---")
    
    # Scenario Configuration
    st.subheader("⚙️ Scenario Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        stores = sorted(df_daily[store_col].unique())
        selected_store = st.selectbox("Select Store", stores, index=0)
        
        store_skus = sorted(df_daily[df_daily[store_col] == selected_store][sku_col].unique())
        if not store_skus:
            st.warning(f"No SKUs found for store {selected_store}")
            selected_sku = None
        else:
            selected_sku = st.selectbox("Select SKU", store_skus, index=0)
    
    with col2:
        # External conditions
        st.markdown("### External Conditions")
        holiday_flag = st.checkbox("Holiday", value=False)
        promo_flag = st.checkbox("Promotion Active", value=False)
        discount_pct = st.slider("Discount %", 0, 50, 0, 5)
    
    # Weather conditions
    st.markdown("### Weather Conditions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        temperature = st.slider("Temperature (°C)", -10, 40, 20, 1)
    with col2:
        weather_bucket = st.selectbox(
            "Weather Bucket",
            ["Cold", "Normal", "Warm", "Hot"],
            index=2
        )
    with col3:
        precipitation = st.checkbox("Rain/Precipitation", value=False)
    
    st.markdown("---")
    
    # Current vs Scenario Comparison
    st.subheader("📊 Current vs Scenario Comparison")
    
    if selected_sku is not None:
        # Get current data for selected store-SKU
        current_data = df_daily[
            (df_daily[store_col] == selected_store) & 
            (df_daily[sku_col] == selected_sku)
        ].copy().sort_values(date_col)
        
        if not current_data.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Current Conditions")
                st.metric("Avg Daily Demand", f"{current_data['demand'].mean():.2f}")
                st.metric("Total Demand", f"{current_data['demand'].sum():,.0f}")
                st.metric("Days Active", f"{len(current_data)}")
            
            with col2:
                st.markdown("### Scenario Impact (Estimated)")
                # Simple impact estimation
                impact_factor = 1.0
                if holiday_flag:
                    impact_factor *= 1.2  # 20% increase
                if promo_flag:
                    impact_factor *= (1 + discount_pct / 100 * 0.5)  # Discount impact
                if weather_bucket == "Hot":
                    impact_factor *= 1.15
                elif weather_bucket == "Cold":
                    impact_factor *= 0.9
                
                estimated_avg = current_data['demand'].mean() * impact_factor
                estimated_total = current_data['demand'].sum() * impact_factor
                
                st.metric("Estimated Avg Daily Demand", f"{estimated_avg:.2f}")
                st.metric("Estimated Total Demand", f"{estimated_total:,.0f}")
                st.metric("Impact", f"{(impact_factor - 1) * 100:+.1f}%")
            
            # Visualization
            st.markdown("---")
            st.subheader("📈 Demand Comparison")
            
            comparison_data = pd.DataFrame({
                'date': current_data[date_col],
                'Current': current_data['demand'],
                'Scenario': current_data['demand'] * impact_factor
            })
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=comparison_data['date'],
                y=comparison_data['Current'],
                name='Current',
                line=dict(color='blue')
            ))
            fig.add_trace(go.Scatter(
                x=comparison_data['date'],
                y=comparison_data['Scenario'],
                name='Scenario',
                line=dict(color='red', dash='dash')
            ))
            fig.update_layout(
                title="Current vs Scenario Demand",
                xaxis_title="Date",
                yaxis_title="Demand",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"No data available for Store {selected_store} - SKU {selected_sku}")
    else:
        st.info("Please select a Store and SKU to see scenario comparison.")
    
    # Simulation Results
    if sim_results is not None and isinstance(sim_results, pd.DataFrame) and not sim_results.empty:
        st.markdown("---")
        st.subheader("🧪 Historical Simulation Results")
        
        if 'policy' in sim_results.columns:
            policy_comparison = sim_results.copy()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Policy Performance")
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
                st.markdown("### Key Metrics Comparison")
                if 'waste_pct' in policy_comparison.columns:
                    metrics_to_plot = ['waste_pct', 'service_level_pct']
                    if 'stockout_pct' in policy_comparison.columns:
                        metrics_to_plot.append('stockout_pct')
                    
                    for metric in metrics_to_plot:
                        if metric in policy_comparison.columns:
                            fig = px.bar(
                                policy_comparison,
                                x='policy',
                                y=metric,
                                title=f"{metric.replace('_', ' ').title()}",
                                labels={metric: metric.replace('_', ' ').title()}
                            )
                            fig.update_layout(height=250)
                            st.plotly_chart(fig, use_container_width=True)
    
    # Replenishment Policy Info
    st.markdown("---")
    st.subheader("📋 Replenishment Policy Configuration")
    
    with st.expander("View Policy Settings"):
        st.json({
            'service_level': f"{config.models.forecasting.default_service_level * 100}%",
            'safety_factor': config.models.forecasting.safety_factor,
            'target_coverage_days': config.models.replenishment.target_coverage_days,
            'min_order_quantity': config.models.replenishment.min_order_quantity,
            'max_order_quantity': config.models.replenishment.max_order_quantity,
            'case_pack_size': config.models.replenishment.case_pack_size
        })
    
    # Markdown Policy Info
    st.markdown("---")
    st.subheader("💰 Markdown Policy Configuration")
    
    with st.expander("View Markdown Settings"):
        markdown_buckets = [
            {
                'days_before_expiry': bucket.days_before_expiry,
                'discount_percent': bucket.discount_percent
            }
            for bucket in config.models.markdown.expiry_buckets
        ]
        st.json({
            'expiry_buckets': markdown_buckets,
            'price_elasticity': -2.0  # Default assumption
        })

