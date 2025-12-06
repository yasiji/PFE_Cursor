"""Store dashboard page."""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from apps.webapp.utils import (
    get_auth_token, make_api_request, get_current_user,
    format_currency, format_number, format_percentage
)

def render():
    """Render store dashboard page."""
    st.title("📊 Store Dashboard")
    
    user = get_current_user()
    token = get_auth_token()
    
    if not user or not token:
        st.error("Not authenticated. Please login.")
        return
    
    # Get store ID from user
    user_store_id = user.get('store_id')
    
    # Store selection
    st.markdown("### Store Selection")
    
    # If user has a store_id, show it but allow override
    if user_store_id:
        st.info(f"📌 Your assigned store: **{user_store_id}**")
        use_assigned = st.checkbox("Use assigned store", value=True, key="use_assigned_store")
        
        if use_assigned:
            store_id = str(user_store_id)
        else:
            # Allow manual entry or selection
            store_options = ["235", "236", "237", "238", "239", "240", "241", "242"]
            if str(user_store_id) not in store_options:
                store_options.insert(0, str(user_store_id))
            
            store_id = st.selectbox(
                "Select Store",
                options=store_options,
                index=0,
                key="store_selection"
            )
    else:
        # No store assigned - allow selection
        st.warning("⚠️ No store assigned to your account.")
        st.info("💡 You can select a store below to view recommendations, or contact an administrator to assign a store to your account.")
        
        store_options = ["235", "236", "237", "238", "239", "240", "241", "242"]
        store_id = st.selectbox(
            "Select Store to View",
            options=store_options,
            index=0,
            key="store_selection_no_assigned"
        )
        
        # Also allow manual entry
        manual_store = st.text_input("Or enter store ID manually", key="manual_store")
        if manual_store and manual_store.strip():
            store_id = manual_store.strip()
    
    if not store_id:
        st.error("Please select or enter a store ID")
        return
    
    # Date selection
    target_date = st.date_input(
        "Target Date",
        value=date.today() + timedelta(days=1),
        help="Date for which to generate recommendations"
    )
    
    # Load recommendations
    if st.button("Load Recommendations", type="primary"):
        load_recommendations(store_id, target_date, token)
    
    # Display recommendations if available
    if 'recommendations' in st.session_state:
        display_recommendations(st.session_state.recommendations, store_id, target_date)
    else:
        st.info("Click 'Load Recommendations' to generate recommendations for this store.")


def load_recommendations(store_id: str, target_date: date, token: str):
    """Load replenishment recommendations from API."""
    with st.spinner("Generating recommendations..."):
        # For now, use mock inventory - in production, this would come from inventory system
        # Provide a few sample SKUs for demonstration
        current_inventory = [
            {
                "sku_id": "123",
                "quantity": 50.0,
                "expiry_date": str(target_date + timedelta(days=2))
            },
            {
                "sku_id": "456",
                "quantity": 30.0,
                "expiry_date": str(target_date + timedelta(days=5))
            },
            {
                "sku_id": "789",
                "quantity": 20.0,
                "expiry_date": None  # No expiry date
            }
        ]
        
        try:
            response = make_api_request(
                method="POST",
                endpoint="/api/v1/replenishment_plan",
                data={
                    "store_id": str(store_id),
                    "date": str(target_date),
                    "current_inventory": current_inventory
                },
                token=token
            )
            
            if response:
                st.session_state.recommendations = response
                st.success("✅ Recommendations loaded successfully!")
            else:
                st.error("❌ Failed to load recommendations. Check API server logs for details.")
        except Exception as e:
            st.error(f"❌ Error loading recommendations: {str(e)}")
            st.info("💡 Make sure the API server is running and check the logs for more details.")


def display_recommendations(recommendations: dict, store_id: str, target_date: date):
    """Display recommendations in a user-friendly format."""
    st.markdown("---")
    st.subheader(f"Recommendations for Store {store_id} - {target_date}")
    
    recs = recommendations.get('recommendations', [])
    
    if not recs:
        st.info("No recommendations available for this store.")
        return
    
    # Create DataFrame for display
    data = []
    for rec in recs:
        markdown = rec.get('markdown')
        data.append({
            'SKU ID': rec['sku_id'],
            'Order Quantity': format_number(rec['order_quantity']),
            'Markdown': f"{markdown['discount_percent']}%" if markdown else "None",
            'Markdown Reason': markdown.get('reason', '') if markdown else '',
            'Effective Date': markdown.get('effective_date', '') if markdown else ''
        })
    
    df = pd.DataFrame(data)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total SKUs", len(recs))
    with col2:
        total_qty = sum(rec['order_quantity'] for rec in recs)
        st.metric("Total Quantity", format_number(total_qty))
    with col3:
        markdown_count = sum(1 for rec in recs if rec.get('markdown'))
        st.metric("Markdown Items", markdown_count)
    with col4:
        avg_qty = total_qty / len(recs) if recs else 0
        st.metric("Avg Order Qty", format_number(avg_qty))
    
    st.markdown("---")
    
    # Display table
    st.subheader("Recommended Orders")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Export button
    col1, col2 = st.columns([1, 4])
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name=f"recommendations_store_{store_id}_{target_date}.csv",
            mime="text/csv"
        )
    
    # Markdown recommendations section
    markdown_items = [rec for rec in recs if rec.get('markdown')]
    if markdown_items:
        st.markdown("---")
        st.subheader("⚠️ Near-Expiry Items - Markdown Recommendations")
        
        markdown_data = []
        for rec in markdown_items:
            markdown = rec['markdown']
            markdown_data.append({
                'SKU ID': rec['sku_id'],
                'Discount': f"{markdown['discount_percent']}%",
                'Reason': markdown.get('reason', 'Near expiry'),
                'Effective Date': markdown.get('effective_date', '')
            })
        
        markdown_df = pd.DataFrame(markdown_data)
        st.dataframe(markdown_df, use_container_width=True, hide_index=True)

