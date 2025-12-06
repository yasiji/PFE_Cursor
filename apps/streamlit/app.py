"""
Streamlit Analytics Dashboard for Fresh Product Replenishment Manager.

Main entry point for the Streamlit dashboard application.
"""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.config import get_config
from shared.logging_setup import setup_logging

# Setup logging
setup_logging()
config = get_config()

# Page configuration
st.set_page_config(
    page_title="Fresh Product Replenishment Manager",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    /* Fix metric text visibility - make text white on dark/colored background */
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #ffffff !important;
        font-weight: 500;
    }
    [data-testid="stMetricDelta"] {
        color: #ffffff !important;
    }
    /* Ensure metric containers have dark background with white text */
    div[data-testid="stMetricContainer"] {
        background-color: #1f77b4 !important;
        border: 1px solid #1565a0 !important;
        border-radius: 0.5rem;
        padding: 1rem;
    }
    div[data-testid="stMetricContainer"] > div {
        color: #ffffff !important;
    }
    div[data-testid="stMetricContainer"] * {
        color: #ffffff !important;
    }
    /* Fix any text color issues */
    .stMetric label {
        color: #ffffff !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    /* Ensure all text in metric boxes is white */
    section[data-testid="stMetric"] {
        background-color: #1f77b4 !important;
    }
    section[data-testid="stMetric"] * {
        color: #ffffff !important;
    }
    /* Additional fix for metric value display */
    .stMetric > div > div {
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🛒 Fresh Product Replenishment Manager")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["📊 Global Overview", "🏪 Store View", "📦 SKU Detail", "🧪 Simulation", "🤖 ML Dashboard"],
    index=0
)

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("### Project Status")
st.sidebar.success("✅ Phase 4 Complete")
st.sidebar.info("🔄 Phase 5: Dashboard Development")

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Info")
st.sidebar.markdown(f"**Model:** LightGBM")
st.sidebar.markdown(f"**Service Level:** {config.models.forecasting.default_service_level*100:.0f}%")
st.sidebar.markdown(f"**Coverage Days:** {config.models.replenishment.target_coverage_days}")

# Main content area
if page == "📊 Global Overview":
    from apps.streamlit.pages import global_overview
    global_overview.render()
elif page == "🏪 Store View":
    from apps.streamlit.pages import store_view
    store_view.render()
elif page == "📦 SKU Detail":
    from apps.streamlit.pages import sku_detail
    sku_detail.render()
elif page == "🧪 Simulation":
    from apps.streamlit.pages import simulation
    simulation.render()
elif page == "🤖 ML Dashboard":
    from apps.streamlit.pages import ml_dashboard
    ml_dashboard.render()

