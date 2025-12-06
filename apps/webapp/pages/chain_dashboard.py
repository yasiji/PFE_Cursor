"""Chain/Regional dashboard page."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from apps.webapp.utils import (
    get_auth_token, make_api_request, get_current_user,
    format_currency, format_number, format_percentage
)

def render():
    """Render chain/regional dashboard page."""
    st.title("🌐 Chain Dashboard")
    
    user = get_current_user()
    token = get_auth_token()
    
    if not user or not token:
        st.error("Not authenticated. Please login.")
        return
    
    if user.get('role') not in ['regional_manager', 'admin']:
        st.error("Access denied. This page is only available for regional managers and admins.")
        return
    
    st.markdown("### Multi-Store Overview")
    
    # Date selection
    from datetime import timedelta
    target_date = st.date_input(
        "Target Date",
        value=date.today() + timedelta(days=1),
        help="Date for which to view aggregated data"
    )
    
    # Load aggregated data
    if st.button("Load Dashboard Data", type="primary"):
        load_dashboard_data(token)
    
    # Display KPIs
    if 'dashboard_data' in st.session_state:
        display_kpis(st.session_state.dashboard_data)
        display_store_rankings(st.session_state.dashboard_data)
        display_category_analysis(st.session_state.dashboard_data)
    else:
        st.info("Click 'Load Dashboard Data' to view aggregated KPIs.")


def load_dashboard_data(token: str):
    """Load aggregated dashboard data."""
    with st.spinner("Loading dashboard data..."):
        # In production, this would call an aggregated endpoint
        # For now, we'll use mock data
        st.session_state.dashboard_data = {
            'stores': [
                {'store_id': '235', 'total_orders': 150, 'total_qty': 2500, 'markdown_count': 5},
                {'store_id': '236', 'total_orders': 120, 'total_qty': 2100, 'markdown_count': 3},
                {'store_id': '237', 'total_orders': 180, 'total_qty': 3200, 'markdown_count': 8},
            ],
            'categories': [
                {'category': 'Category 4', 'total_qty': 1200, 'store_count': 3},
                {'category': 'Category 20', 'total_qty': 800, 'store_count': 2},
            ]
        }
        st.success("Dashboard data loaded!")


def display_kpis(data: dict):
    """Display key performance indicators."""
    st.markdown("---")
    st.subheader("Key Performance Indicators")
    
    stores = data.get('stores', [])
    total_stores = len(stores)
    total_orders = sum(s['total_orders'] for s in stores)
    total_qty = sum(s['total_qty'] for s in stores)
    total_markdowns = sum(s['markdown_count'] for s in stores)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Stores", total_stores)
    with col2:
        st.metric("Total Orders", format_number(total_orders))
    with col3:
        st.metric("Total Quantity", format_number(total_qty))
    with col4:
        st.metric("Markdown Items", total_markdowns)


def display_store_rankings(data: dict):
    """Display store rankings."""
    st.markdown("---")
    st.subheader("Store Rankings")
    
    stores = data.get('stores', [])
    if not stores:
        st.info("No store data available.")
        return
    
    df = pd.DataFrame(stores)
    df = df.sort_values('total_qty', ascending=False)
    df['Rank'] = range(1, len(df) + 1)
    
    # Reorder columns
    df = df[['Rank', 'store_id', 'total_orders', 'total_qty', 'markdown_count']]
    df.columns = ['Rank', 'Store ID', 'Orders', 'Total Quantity', 'Markdowns']
    
    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Chart
    fig = px.bar(
        df,
        x='Store ID',
        y='Total Quantity',
        title='Total Order Quantity by Store',
        labels={'Total Quantity': 'Quantity', 'Store ID': 'Store'}
    )
    st.plotly_chart(fig, use_container_width=True)


def display_category_analysis(data: dict):
    """Display category analysis."""
    st.markdown("---")
    st.subheader("Category Analysis")
    
    categories = data.get('categories', [])
    if not categories:
        st.info("No category data available.")
        return
    
    df = pd.DataFrame(categories)
    
    # Display table
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Chart
    fig = px.pie(
        df,
        values='total_qty',
        names='category',
        title='Order Quantity Distribution by Category'
    )
    st.plotly_chart(fig, use_container_width=True)

