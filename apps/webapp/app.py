"""Store/Chain Manager Web Application - Main entry point."""

import streamlit as st
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.webapp.pages import login, store_dashboard, chain_dashboard, history, settings
from apps.webapp.utils import check_authentication, get_current_user
from shared.logging_setup import get_logger

logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Replenishment Manager",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
        .warning-box {
            background-color: #fff3cd;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #ffc107;
        }
        .success-box {
            background-color: #d4edda;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #28a745;
        }
    </style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'token' not in st.session_state:
        st.session_state.token = None
    if 'api_url' not in st.session_state:
        st.session_state.api_url = "http://localhost:8000"
    
    # Check authentication
    if not st.session_state.authenticated:
        login.render()
    else:
        # Show main app
        user = st.session_state.user
        
        # Sidebar navigation
        st.sidebar.title("🛒 Replenishment Manager")
        st.sidebar.markdown(f"**User:** {user.get('username', 'Unknown')}")
        st.sidebar.markdown(f"**Role:** {user.get('role', 'Unknown')}")
        
        if user.get('role') == 'store_manager':
            st.sidebar.markdown(f"**Store ID:** {user.get('store_id', 'N/A')}")
        
        st.sidebar.markdown("---")
        
        # Navigation
        page = st.sidebar.radio(
            "Navigation",
            ["Store Dashboard", "History", "Settings"],
            key="nav"
        )
        
        # Role-based navigation
        if user.get('role') in ['regional_manager', 'admin']:
            page = st.sidebar.radio(
                "Navigation",
                ["Store Dashboard", "Chain Dashboard", "History", "Settings"],
                key="nav_admin"
            )
        
        # Logout button
        if st.sidebar.button("Logout", type="secondary"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.token = None
            st.rerun()
        
        # Render selected page
        if page == "Store Dashboard":
            store_dashboard.render()
        elif page == "Chain Dashboard":
            if user.get('role') in ['regional_manager', 'admin']:
                chain_dashboard.render()
            else:
                st.error("Access denied. This page is only available for regional managers and admins.")
        elif page == "History":
            history.render()
        elif page == "Settings":
            settings.render()


if __name__ == "__main__":
    main()

