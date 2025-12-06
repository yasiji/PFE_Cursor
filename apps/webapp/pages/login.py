"""Login page."""

import streamlit as st
from apps.webapp.utils import login_user, get_api_url

def render():
    """Render login page."""
    st.title("🛒 Replenishment Manager")
    st.markdown("### Login to continue")
    
    # API URL configuration (for development)
    with st.expander("⚙️ API Configuration", expanded=False):
        api_url = st.text_input(
            "API URL",
            value=get_api_url(),
            help="URL of the FastAPI backend"
        )
        st.session_state.api_url = api_url
    
    st.markdown("---")
    
    # Login form
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submit = st.form_submit_button("Login", type="primary", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                with st.spinner("Logging in..."):
                    if login_user(username, password):
                        st.success("Login successful!")
                        st.rerun()
    
    # Demo credentials info
    st.markdown("---")
    st.info("""
    **Demo Credentials:**
    - First, register a user using the API endpoint `/api/v1/auth/register`
    - Or use the API documentation at http://localhost:8000/docs to create a user
    """)

