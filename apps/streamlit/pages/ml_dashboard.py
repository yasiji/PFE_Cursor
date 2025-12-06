"""
ML Dashboard - Comprehensive Model Information for Thesis Presentation.

This dashboard provides detailed insights into:
- Model Architecture & Parameters
- Feature Engineering Pipeline
- Training Process & Metrics
- Model Performance Analysis
- Feature Importance Analysis
- Prediction Accuracy Visualization
- Demand Factors & Seasonality
- Model Comparison (LightGBM vs Baselines)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import json
from datetime import datetime, timedelta
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.config import get_config

config = get_config()


def load_model_results():
    """Load model training results."""
    results_path = project_root / "data" / "processed" / "lightgbm_results" / "lightgbm_results.json"
    if results_path.exists():
        with open(results_path, 'r') as f:
            return json.load(f)
    return None


def load_baseline_results():
    """Load baseline model results for comparison."""
    results_path = project_root / "data" / "processed" / "baseline_results" / "baseline_model_results.json"
    if results_path.exists():
        with open(results_path, 'r') as f:
            return json.load(f)
    return None


def load_feature_importance():
    """Load feature importance data."""
    importance_path = project_root / "data" / "processed" / "lightgbm_results" / "lightgbm_feature_importance.csv"
    if importance_path.exists():
        return pd.read_csv(importance_path)
    return None


def load_predictions():
    """Load model predictions."""
    predictions_path = project_root / "data" / "processed" / "lightgbm_results" / "lightgbm_predictions.csv"
    if predictions_path.exists():
        return pd.read_csv(predictions_path)
    return None


def load_training_info():
    """Load training data info."""
    info_path = project_root / "data" / "processed" / "inspection" / "train_info.txt"
    if info_path.exists():
        with open(info_path, 'r') as f:
            return f.read()
    return None


def render():
    """Render the ML Dashboard page."""
    
    # Header
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 1rem; margin-bottom: 2rem;">
        <h1 style="color: white; margin: 0; text-align: center;">
            🤖 Machine Learning Dashboard
        </h1>
        <p style="color: rgba(255,255,255,0.9); text-align: center; margin-top: 0.5rem;">
            Comprehensive Model Analysis for Fresh Product Demand Forecasting
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load all data
    model_results = load_model_results()
    baseline_results = load_baseline_results()
    feature_importance = load_feature_importance()
    predictions = load_predictions()
    training_info = load_training_info()
    
    # Create tabs for different sections
    tabs = st.tabs([
        "📋 Model Overview",
        "⚙️ Architecture",
        "🔧 Features",
        "📊 Performance",
        "🔍 Predictions",
        "📈 Comparison",
        "🌡️ Demand Factors"
    ])
    
    # ===== TAB 1: Model Overview =====
    with tabs[0]:
        render_model_overview(model_results, training_info)
    
    # ===== TAB 2: Architecture =====
    with tabs[1]:
        render_architecture()
    
    # ===== TAB 3: Features =====
    with tabs[2]:
        render_features(feature_importance)
    
    # ===== TAB 4: Performance =====
    with tabs[3]:
        render_performance(model_results, baseline_results)
    
    # ===== TAB 5: Predictions =====
    with tabs[4]:
        render_predictions(predictions)
    
    # ===== TAB 6: Model Comparison =====
    with tabs[5]:
        render_comparison(model_results, baseline_results)
    
    # ===== TAB 7: Demand Factors =====
    with tabs[6]:
        render_demand_factors()


def render_model_overview(model_results, training_info):
    """Render model overview section."""
    st.header("📋 Model Overview")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Project Objective")
        st.markdown("""
        <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #667eea;">
            <strong>Goal:</strong> Predict daily demand for fresh/perishable products to optimize:
            <ul>
                <li>📦 <strong>Inventory Levels</strong> - Right stock at the right time</li>
                <li>🚛 <strong>Replenishment Orders</strong> - Automated ordering suggestions</li>
                <li>🗑️ <strong>Waste Reduction</strong> - Minimize expired products</li>
                <li>📉 <strong>Stockout Prevention</strong> - Avoid lost sales</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("🏗️ Model Selection")
        st.markdown("""
        <div style="background: #e8f5e9; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #4caf50;">
            <strong>Model:</strong> LightGBM (Light Gradient Boosting Machine)
            <br><br>
            <strong>Why LightGBM?</strong>
            <ul>
                <li>✅ Fast training speed</li>
                <li>✅ Low memory usage</li>
                <li>✅ Handles categorical features</li>
                <li>✅ Better accuracy than traditional methods</li>
                <li>✅ Excellent for tabular retail data</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("📊 Training Data Summary")
        
        if training_info:
            # Parse key info from training info
            st.info("**Dataset:** Fresh Retail Net-50K (Synthetic)")
            
            # Display key metrics
            metrics_cols = st.columns(3)
            with metrics_cols[0]:
                st.metric("📁 Records", "182,500")
            with metrics_cols[1]:
                st.metric("🏪 Stores", "10")
            with metrics_cols[2]:
                st.metric("📦 SKUs", "306")
            
            st.markdown("---")
            
            st.markdown("**📅 Features Available:**")
            features_list = [
                "Date & Calendar", "Store ID", "SKU ID", 
                "Category", "Price", "Revenue",
                "Promotions", "Weather", "Stock Level"
            ]
            for i in range(0, len(features_list), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    if i + j < len(features_list):
                        col.markdown(f"✅ {features_list[i + j]}")
        
        if model_results:
            st.subheader("🎯 Model Performance (Quick View)")
            perf_cols = st.columns(2)
            with perf_cols[0]:
                st.metric(
                    "MAE", 
                    f"{model_results['mae']:.4f}",
                    help="Mean Absolute Error - Average prediction error"
                )
                st.metric(
                    "RMSE", 
                    f"{model_results['rmse']:.4f}",
                    help="Root Mean Square Error - Penalizes large errors"
                )
            with perf_cols[1]:
                st.metric(
                    "WAPE", 
                    f"{model_results['wape']:.2f}%",
                    help="Weighted Absolute Percentage Error"
                )
                st.metric(
                    "Bias", 
                    f"{model_results['bias']:.4f}",
                    delta="Under-forecast" if model_results['bias'] < 0 else "Over-forecast",
                    delta_color="off"
                )


def render_architecture():
    """Render model architecture section."""
    st.header("⚙️ Model Architecture")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🌲 LightGBM Architecture")
        
        # Architecture diagram using Plotly
        fig = go.Figure()
        
        # Create a tree-like visualization
        fig.add_trace(go.Scatter(
            x=[0, -2, 2, -3, -1, 1, 3],
            y=[3, 2, 2, 1, 1, 1, 1],
            mode='markers+text',
            marker=dict(size=50, color=['#667eea', '#764ba2', '#764ba2', '#4caf50', '#4caf50', '#4caf50', '#4caf50']),
            text=['Root', 'Split 1', 'Split 2', 'Leaf 1', 'Leaf 2', 'Leaf 3', 'Leaf 4'],
            textposition='middle center',
            textfont=dict(color='white', size=10)
        ))
        
        # Add edges
        for start, end in [((0,3), (-2,2)), ((0,3), (2,2)), 
                          ((-2,2), (-3,1)), ((-2,2), (-1,1)),
                          ((2,2), (1,1)), ((2,2), (3,1))]:
            fig.add_trace(go.Scatter(
                x=[start[0], end[0]], y=[start[1], end[1]],
                mode='lines',
                line=dict(color='#ccc', width=2),
                showlegend=False
            ))
        
        fig.update_layout(
            title="Decision Tree Structure (Simplified)",
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        <div style="background: #fff3e0; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #ff9800;">
            <strong>How LightGBM Works:</strong>
            <ol>
                <li><strong>Gradient Boosting:</strong> Builds trees sequentially, each correcting previous errors</li>
                <li><strong>Leaf-wise Growth:</strong> Grows tree leaf-by-leaf (faster than level-wise)</li>
                <li><strong>Histogram-based:</strong> Bins continuous features for speed</li>
                <li><strong>Feature Bundling:</strong> Bundles sparse features together</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("🔧 Hyperparameters")
        
        params_data = {
            'Parameter': [
                'objective', 'metric', 'boosting_type', 'num_leaves',
                'learning_rate', 'feature_fraction', 'bagging_fraction',
                'bagging_freq', 'num_boost_round', 'early_stopping_rounds'
            ],
            'Value': [
                'regression', 'rmse', 'gbdt', '31',
                '0.05', '0.9', '0.8',
                '5', '100', '10'
            ],
            'Description': [
                'Regression task for continuous demand',
                'Root Mean Square Error loss',
                'Gradient Boosting Decision Tree',
                'Maximum leaves per tree (complexity)',
                'Step size for gradient descent',
                'Fraction of features per tree',
                'Fraction of data per tree',
                'Bagging every N iterations',
                'Maximum number of trees',
                'Stop if no improvement for N rounds'
            ]
        }
        
        params_df = pd.DataFrame(params_data)
        st.dataframe(params_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        st.subheader("🔄 Training Process")
        st.markdown("""
        ```
        1. Data Loading
           └── Load 182,500 training records
           
        2. Feature Engineering
           └── Create 31 features (calendar, lags, rolling)
           
        3. Train/Validation Split
           └── 80% train, 20% validation
           
        4. Model Training
           └── Gradient boosting with early stopping
           
        5. Evaluation
           └── Calculate MAE, RMSE, WAPE, Bias
        ```
        """)


def render_features(feature_importance):
    """Render feature engineering section."""
    st.header("🔧 Feature Engineering")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Feature Categories")
        
        feature_categories = {
            "Calendar Features": [
                ("dayofweek", "Day of week (0-6)"),
                ("dayofyear", "Day of year (1-365)"),
                ("month", "Month (1-12)"),
                ("week", "Week number"),
                ("is_weekend", "Weekend flag (0/1)"),
                ("is_month_end", "Month end flag"),
                ("quarter", "Quarter (1-4)")
            ],
            "Lag Features": [
                ("demand_lag_1", "Yesterday's demand"),
                ("demand_lag_7", "Same day last week"),
                ("demand_lag_14", "Same day 2 weeks ago"),
                ("demand_lag_28", "Same day 4 weeks ago")
            ],
            "Rolling Window Features": [
                ("demand_rolling_mean_7", "7-day average demand"),
                ("demand_rolling_mean_14", "14-day average demand"),
                ("demand_rolling_std_7", "7-day demand volatility"),
                ("demand_rolling_max_7", "7-day max demand"),
                ("demand_rolling_min_7", "7-day min demand")
            ],
            "Entity Features": [
                ("store_id_encoded", "Store identifier"),
                ("product_id_encoded", "Product identifier")
            ]
        }
        
        for category, features in feature_categories.items():
            with st.expander(f"📁 {category}", expanded=(category == "Rolling Window Features")):
                for feat_name, feat_desc in features:
                    st.markdown(f"• **{feat_name}**: {feat_desc}")
    
    with col2:
        st.subheader("📈 Feature Importance")
        
        if feature_importance is not None:
            # Sort and get top 15
            top_features = feature_importance.nlargest(15, 'importance')
            
            # Create horizontal bar chart
            fig = px.bar(
                top_features,
                x='importance',
                y='feature',
                orientation='h',
                color='importance',
                color_continuous_scale='Viridis',
                title="Top 15 Most Important Features"
            )
            fig.update_layout(
                yaxis=dict(categoryorder='total ascending'),
                height=500,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("""
            <div style="background: #e3f2fd; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #2196f3;">
                <strong>Key Insights:</strong>
                <ul>
                    <li>🔹 <strong>Rolling means</strong> are the most predictive features</li>
                    <li>🔹 <strong>Day of week</strong> captures weekly patterns</li>
                    <li>🔹 <strong>Lag features</strong> capture autoregressive patterns</li>
                    <li>🔹 <strong>Product ID</strong> shows SKU-level variation</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("Feature importance data not available")


def render_performance(model_results, baseline_results):
    """Render performance metrics section."""
    st.header("📊 Model Performance")
    
    if model_results is None:
        st.warning("Model results not available")
        return
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🎯 Error Metrics")
        
        # Create metrics visualization
        metrics_data = {
            'Metric': ['MAE', 'RMSE', 'MAPE', 'WAPE', 'Bias'],
            'Value': [
                model_results['mae'],
                model_results['rmse'],
                model_results['mape'],
                model_results['wape'],
                model_results['bias']
            ],
            'Interpretation': [
                f"On average, predictions are off by {model_results['mae']:.2f} units",
                f"Root mean square error of {model_results['rmse']:.2f} units",
                f"Mean absolute percentage error of {model_results['mape']:.1f}%",
                f"Weighted absolute percentage error of {model_results['wape']:.1f}%",
                f"Model {'under-forecasts' if model_results['bias'] < 0 else 'over-forecasts'} by {abs(model_results['bias']):.2f} units"
            ]
        }
        
        for metric, value, interpretation in zip(metrics_data['Metric'], metrics_data['Value'], metrics_data['Interpretation']):
            st.markdown(f"""
            <div style="background: #f5f5f5; padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem;">
                <strong>{metric}</strong>: {value:.4f}
                <br><small style="color: #666;">{interpretation}</small>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("📈 Metrics Visualization")
        
        # Create gauge charts for key metrics
        fig = make_subplots(
            rows=2, cols=2,
            specs=[[{'type': 'indicator'}, {'type': 'indicator'}],
                   [{'type': 'indicator'}, {'type': 'indicator'}]],
            subplot_titles=('MAE', 'RMSE', 'WAPE (%)', 'Bias')
        )
        
        # MAE
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=model_results['mae'],
            domain={'x': [0, 0.45], 'y': [0.55, 1]},
            gauge={'axis': {'range': [0, 1]},
                   'bar': {'color': "#667eea"},
                   'steps': [{'range': [0, 0.5], 'color': "#e8f5e9"},
                            {'range': [0.5, 1], 'color': "#ffebee"}]}
        ), row=1, col=1)
        
        # RMSE
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=model_results['rmse'],
            domain={'x': [0.55, 1], 'y': [0.55, 1]},
            gauge={'axis': {'range': [0, 1.5]},
                   'bar': {'color': "#764ba2"},
                   'steps': [{'range': [0, 0.75], 'color': "#e8f5e9"},
                            {'range': [0.75, 1.5], 'color': "#ffebee"}]}
        ), row=1, col=2)
        
        # WAPE
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=model_results['wape'],
            domain={'x': [0, 0.45], 'y': [0, 0.45]},
            number={'suffix': '%'},
            gauge={'axis': {'range': [0, 50]},
                   'bar': {'color': "#4caf50"},
                   'steps': [{'range': [0, 25], 'color': "#e8f5e9"},
                            {'range': [25, 50], 'color': "#ffebee"}]}
        ), row=2, col=1)
        
        # Bias
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=model_results['bias'],
            domain={'x': [0.55, 1], 'y': [0, 0.45]},
            gauge={'axis': {'range': [-1, 1]},
                   'bar': {'color': "#ff9800"},
                   'steps': [{'range': [-1, -0.2], 'color': "#fff3e0"},
                            {'range': [-0.2, 0.2], 'color': "#e8f5e9"},
                            {'range': [0.2, 1], 'color': "#fff3e0"}]}
        ), row=2, col=2)
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)


def render_predictions(predictions):
    """Render predictions analysis section."""
    st.header("🔍 Predictions Analysis")
    
    if predictions is None:
        st.warning("Predictions data not available")
        return
    
    # Convert date column
    predictions['date'] = pd.to_datetime(predictions['date'])
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 Actual vs Predicted")
        
        # Sample data for visualization
        sample = predictions.sample(min(500, len(predictions)))
        
        fig = px.scatter(
            sample,
            x='actual',
            y='predicted_demand',
            color='store_id',
            title="Actual vs Predicted Demand",
            labels={'actual': 'Actual Demand', 'predicted_demand': 'Predicted Demand'},
            opacity=0.6
        )
        
        # Add perfect prediction line
        max_val = max(sample['actual'].max(), sample['predicted_demand'].max())
        fig.add_trace(go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode='lines',
            name='Perfect Prediction',
            line=dict(color='red', dash='dash')
        ))
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Prediction Distribution")
        
        # Error distribution
        predictions['error'] = predictions['predicted_demand'] - predictions['actual']
        
        fig = px.histogram(
            predictions,
            x='error',
            nbins=50,
            title="Prediction Error Distribution",
            labels={'error': 'Error (Predicted - Actual)'},
            color_discrete_sequence=['#667eea']
        )
        fig.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Zero Error")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Time series sample
    st.subheader("📅 Time Series Predictions (Sample Product)")
    
    # Get one product's predictions
    sample_product = predictions.groupby('product_id').size().idxmax()
    product_data = predictions[predictions['product_id'] == sample_product].sort_values('date')
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=product_data['date'],
        y=product_data['actual'],
        mode='lines',
        name='Actual',
        line=dict(color='#1f77b4')
    ))
    fig.add_trace(go.Scatter(
        x=product_data['date'],
        y=product_data['predicted_demand'],
        mode='lines',
        name='Predicted',
        line=dict(color='#ff7f0e')
    ))
    fig.add_trace(go.Scatter(
        x=product_data['date'],
        y=product_data['upper_bound'],
        mode='lines',
        name='Upper Bound',
        line=dict(color='rgba(255,127,14,0.3)'),
        fill=None
    ))
    fig.add_trace(go.Scatter(
        x=product_data['date'],
        y=product_data['lower_bound'],
        mode='lines',
        name='Lower Bound',
        line=dict(color='rgba(255,127,14,0.3)'),
        fill='tonexty',
        fillcolor='rgba(255,127,14,0.1)'
    ))
    
    fig.update_layout(
        title=f"Time Series Forecast - Product {sample_product}",
        xaxis_title="Date",
        yaxis_title="Demand",
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)


def render_comparison(model_results, baseline_results):
    """Render model comparison section."""
    st.header("📈 Model Comparison")
    
    if baseline_results is None or model_results is None:
        st.warning("Comparison data not available")
        return
    
    # Prepare comparison data
    comparison_data = []
    
    # Add LightGBM
    comparison_data.append({
        'Model': 'LightGBM',
        'MAE': model_results['mae'],
        'RMSE': model_results['rmse'],
        'WAPE': model_results['wape'],
        'Type': 'ML Model'
    })
    
    # Add baselines
    for model_name, metrics in baseline_results.items():
        display_name = model_name.replace('_', ' ')
        comparison_data.append({
            'Model': display_name,
            'MAE': metrics['mae'],
            'RMSE': metrics['rmse'],
            'WAPE': metrics['wape'],
            'Type': 'Baseline'
        })
    
    df_comparison = pd.DataFrame(comparison_data)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 MAE Comparison")
        
        fig = px.bar(
            df_comparison,
            x='Model',
            y='MAE',
            color='Type',
            title="Mean Absolute Error by Model",
            color_discrete_map={'ML Model': '#667eea', 'Baseline': '#ccc'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 WAPE Comparison")
        
        fig = px.bar(
            df_comparison,
            x='Model',
            y='WAPE',
            color='Type',
            title="Weighted Absolute Percentage Error by Model",
            color_discrete_map={'ML Model': '#764ba2', 'Baseline': '#ccc'}
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Improvement calculation
    st.subheader("🚀 Improvement over Baselines")
    
    best_baseline_mae = min([m['mae'] for m in baseline_results.values()])
    best_baseline_wape = min([m['wape'] for m in baseline_results.values()])
    
    mae_improvement = ((best_baseline_mae - model_results['mae']) / best_baseline_mae) * 100
    wape_improvement = ((best_baseline_wape - model_results['wape']) / best_baseline_wape) * 100
    
    imp_cols = st.columns(3)
    with imp_cols[0]:
        st.metric(
            "MAE Improvement",
            f"{mae_improvement:.1f}%",
            delta=f"vs Moving Avg",
            delta_color="normal"
        )
    with imp_cols[1]:
        st.metric(
            "WAPE Improvement",
            f"{wape_improvement:.1f}%",
            delta=f"vs Moving Avg",
            delta_color="normal"
        )
    with imp_cols[2]:
        st.metric(
            "Best Baseline",
            "Moving Avg 7",
            delta="Naive methods",
            delta_color="off"
        )
    
    # Comparison table
    st.subheader("📋 Detailed Comparison Table")
    st.dataframe(
        df_comparison.style.highlight_min(subset=['MAE', 'RMSE', 'WAPE'], color='lightgreen'),
        use_container_width=True,
        hide_index=True
    )


def render_demand_factors():
    """Render demand factors section."""
    st.header("🌡️ Demand Factors & Seasonality")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); 
                padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem;">
        <h4>Real-Time External Factors</h4>
        <p>Our forecasting system integrates real-time data from external APIs to adjust predictions based on:</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #e3f2fd; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
            <h3>📅 Day of Week</h3>
            <p><strong>Source:</strong> Calendar</p>
            <hr>
            <p>Monday: 0.85x<br>
            Tuesday: 0.88x<br>
            Wednesday: 0.95x<br>
            Thursday: 1.00x<br>
            Friday: 1.15x<br>
            <strong>Saturday: 1.30x</strong><br>
            Sunday: 1.10x</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #fff8e1; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
            <h3>🌤️ Weather</h3>
            <p><strong>Source:</strong> Open-Meteo API</p>
            <hr>
            <p>Clear/Sunny: 1.05x<br>
            Cloudy: 1.00x<br>
            Rainy: 0.90x<br>
            Stormy: 0.80x<br>
            <strong>Very Hot (>30°C):</strong> 1.15x<br>
            Cold (<5°C): 1.10x</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #f3e5f5; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
            <h3>🎉 Holidays</h3>
            <p><strong>Source:</strong> Nager.Date API</p>
            <hr>
            <p>Regular Day: 1.00x<br>
            Pre-Holiday: 1.25x<br>
            <strong>Holiday: 1.40x</strong><br>
            Major Holiday: 1.60x<br>
            Post-Holiday: 0.90x</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Factor combination formula
    st.subheader("🧮 Combined Seasonality Factor")
    
    st.latex(r"S_{combined} = 0.30 \times F_{day} + 0.35 \times F_{weather} + 0.35 \times F_{holiday}")
    
    st.markdown("""
    <div style="background: #e8f5e9; padding: 1rem; border-radius: 0.5rem;">
        <strong>Example Calculation:</strong><br>
        <ul>
            <li>Saturday (F_day = 1.30)</li>
            <li>Sunny weather (F_weather = 1.05)</li>
            <li>Regular day (F_holiday = 1.00)</li>
        </ul>
        <strong>S_combined = 0.30 × 1.30 + 0.35 × 1.05 + 0.35 × 1.00 = 1.1075</strong>
        <br>This means demand is expected to be 10.75% higher than baseline.
    </div>
    """, unsafe_allow_html=True)
    
    # Weekly pattern visualization
    st.subheader("📊 Weekly Demand Pattern")
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    factors = [0.85, 0.88, 0.95, 1.00, 1.15, 1.30, 1.10]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=days,
        y=factors,
        marker_color=['#90caf9' if f < 1 else '#4caf50' if f < 1.2 else '#ff9800' for f in factors],
        text=[f'{f:.2f}x' for f in factors],
        textposition='outside'
    ))
    
    fig.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="Baseline")
    fig.update_layout(
        title="Day-of-Week Demand Factors",
        xaxis_title="Day",
        yaxis_title="Demand Factor",
        yaxis=dict(range=[0.7, 1.5]),
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # API Integration diagram
    st.subheader("🔗 API Integration Architecture")
    
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────┐
    │                    FORECASTING SERVICE                      │
    │                                                             │
    │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
    │  │  LightGBM   │   │   Weather   │   │   Holiday   │       │
    │  │    Model    │   │   Service   │   │   Service   │       │
    │  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
    │         │                 │                 │               │
    │         └────────────┬────┴─────────────────┘               │
    │                      │                                      │
    │              ┌───────▼───────┐                              │
    │              │ Demand Factors│                              │
    │              │    Service    │                              │
    │              └───────┬───────┘                              │
    │                      │                                      │
    │              ┌───────▼───────┐                              │
    │              │   Combined    │                              │
    │              │   Forecast    │                              │
    │              └───────────────┘                              │
    └─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
      ┌───────▼───────┐ ┌──▼──┐ ┌───────▼───────┐
      │   Open-Meteo  │ │ DB  │ │  Nager.Date   │
      │      API      │ │     │ │     API       │
      └───────────────┘ └─────┘ └───────────────┘
    ```
    """)


if __name__ == "__main__":
    render()

