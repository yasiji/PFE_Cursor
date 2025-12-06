"""History and overrides page."""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from apps.webapp.utils import (
    get_auth_token, make_api_request, get_current_user,
    format_currency, format_number
)

def render():
    """Render history page."""
    st.title("📜 History & Overrides")
    
    user = get_current_user()
    token = get_auth_token()
    
    if not user or not token:
        st.error("Not authenticated. Please login.")
        return
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today() - timedelta(days=7)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today()
        )
    
    # Store selection (for admins/regional managers)
    store_id = None
    if user.get('role') in ['admin', 'regional_manager']:
        store_id = st.selectbox(
            "Select Store",
            options=[None, "235", "236", "237", "238", "239"],
            format_func=lambda x: "All Stores" if x is None else f"Store {x}"
        )
    else:
        store_id = user.get('store_id')
    
    # Load history
    if st.button("Load History", type="primary"):
        load_history(store_id, start_date, end_date, token)
    
    # Display history
    if 'history_data' in st.session_state:
        display_history(st.session_state.history_data)
        display_overrides_section()
    else:
        st.info("Click 'Load History' to view past recommendations.")


def load_history(store_id: str, start_date: date, end_date: date, token: str):
    """Load historical recommendations."""
    with st.spinner("Loading history..."):
        # In production, this would call a history endpoint
        # For now, use mock data
        st.session_state.history_data = {
            'recommendations': [
                {
                    'date': str(start_date + timedelta(days=i)),
                    'store_id': store_id or '235',
                    'sku_id': '123',
                    'order_quantity': 25.0,
                    'status': 'executed',
                    'actual_quantity': 23.0
                }
                for i in range((end_date - start_date).days + 1)
            ]
        }
        st.success("History loaded!")


def display_history(data: dict):
    """Display historical recommendations."""
    st.markdown("---")
    st.subheader("Historical Recommendations")
    
    recs = data.get('recommendations', [])
    if not recs:
        st.info("No historical data available.")
        return
    
    df = pd.DataFrame(recs)
    
    # Calculate variance
    if 'actual_quantity' in df.columns and 'order_quantity' in df.columns:
        df['variance'] = df['actual_quantity'] - df['order_quantity']
        df['variance_pct'] = (df['variance'] / df['order_quantity'] * 100).round(1)
    
    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Summary metrics
    if 'variance' in df.columns:
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_variance = df['variance'].mean()
            st.metric("Avg Variance", format_number(avg_variance))
        with col2:
            total_recommended = df['order_quantity'].sum()
            st.metric("Total Recommended", format_number(total_recommended))
        with col3:
            total_actual = df['actual_quantity'].sum() if 'actual_quantity' in df.columns else 0
            st.metric("Total Actual", format_number(total_actual))


def display_overrides_section():
    """Display section for overriding recommendations."""
    st.markdown("---")
    st.subheader("Override Recommendations")
    
    st.info("""
    **Override Functionality:**
    - Select a recommendation to override
    - Enter a manual order quantity
    - Save the override (will be sent to API)
    
    *Note: This feature requires API endpoint implementation.*
    """)
    
    # Override form (placeholder)
    with st.form("override_form"):
        st.selectbox("Select Recommendation", options=["Rec 1", "Rec 2"])
        override_qty = st.number_input("Override Quantity", min_value=0.0, value=0.0)
        
        if st.form_submit_button("Save Override"):
            st.success("Override saved! (Feature in development)")

