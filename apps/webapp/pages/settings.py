"""Settings page."""

import streamlit as st
from apps.webapp.utils import get_current_user, get_api_url

def render():
    """Render settings page."""
    st.title("⚙️ Settings")
    
    user = get_current_user()
    
    if not user:
        st.error("Not authenticated. Please login.")
        return
    
    st.markdown("### User Information")
    
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Username", value=user.get('username', ''), disabled=True)
        st.text_input("Email", value=user.get('email', ''), disabled=True)
    with col2:
        st.text_input("Role", value=user.get('role', ''), disabled=True)
        if user.get('store_id'):
            st.text_input("Store ID", value=str(user.get('store_id', '')), disabled=True)
    
    st.markdown("---")
    st.markdown("### API Configuration")
    
    api_url = st.text_input(
        "API URL",
        value=get_api_url(),
        help="URL of the FastAPI backend"
    )
    
    if st.button("Save API URL"):
        st.session_state.api_url = api_url
        st.success("API URL saved!")
    
    st.markdown("---")
    st.markdown("### Preferences")
    
    # Notification preferences (placeholder)
    email_notifications = st.checkbox("Email Notifications", value=False)
    daily_summary = st.checkbox("Daily Summary Report", value=True)
    
    if st.button("Save Preferences"):
        st.success("Preferences saved! (Feature in development)")

