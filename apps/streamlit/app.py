"""
Streamlit ML Dashboard for Fresh Product Replenishment Manager.

Thesis Presentation Dashboard - LightGBM Forecasting System
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
    page_title="ML Dashboard - Fresh Product Forecasting",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar by default
)

# Custom CSS for better styling
st.markdown("""
    <style>
    /* Hide the default Streamlit sidebar pages */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* Hide sidebar completely */
    section[data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Remove sidebar toggle button */
    button[kind="header"] {
        display: none !important;
    }
    
    /* Make main content full width */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Fix info boxes - ensure dark text on light backgrounds */
    .stAlert > div {
        color: #1f2937 !important;
    }
    
    .stAlert p, .stAlert li, .stAlert strong {
        color: #1f2937 !important;
    }
    
    /* Fix for info/success/warning boxes */
    div[data-testid="stAlert"] {
        color: #1f2937 !important;
    }
    
    div[data-testid="stAlert"] * {
        color: #1f2937 !important;
    }
    
    /* Ensure markdown text in colored boxes is visible */
    .element-container div[data-testid="stMarkdownContainer"] p {
        color: inherit;
    }
    
    /* Fix list items in info boxes */
    .stAlert ul li {
        color: #1f2937 !important;
    }
    
    /* Custom styled boxes - ensure text is dark */
    div[style*="background"] {
        color: #1f2937 !important;
    }
    
    div[style*="background"] p,
    div[style*="background"] li,
    div[style*="background"] strong,
    div[style*="background"] h4,
    div[style*="background"] ul {
        color: #1f2937 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Load and render ML Dashboard directly
from apps.streamlit.pages import ml_dashboard
ml_dashboard.render()
