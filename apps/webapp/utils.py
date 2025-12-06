"""Utility functions for web app."""

import streamlit as st
import httpx
from typing import Optional, Dict, Any
from shared.logging_setup import get_logger

logger = get_logger(__name__)


def get_api_url() -> str:
    """Get API URL from session state or default."""
    return st.session_state.get('api_url', 'http://localhost:8000')


def make_api_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    token: Optional[str] = None
) -> Optional[Dict]:
    """
    Make HTTP request to API.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path
        data: Request body data
        params: Query parameters
        token: Authentication token
        
    Returns:
        Response JSON or None if error
    """
    api_url = get_api_url()
    url = f"{api_url}{endpoint}"
    
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = client.post(url, headers=headers, json=data, params=params)
            elif method == "PUT":
                response = client.put(url, headers=headers, json=data, params=params)
            elif method == "DELETE":
                response = client.delete(url, headers=headers, params=params)
            else:
                st.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"API error: {e.response.status_code} - {e.response.text}")
        st.error(f"API Error: {e.response.status_code}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error: {e}")
        st.error(f"Connection error: Could not connect to API at {api_url}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        st.error(f"Unexpected error: {e}")
        return None


def check_authentication() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)


def get_current_user() -> Optional[Dict]:
    """Get current user from session state."""
    return st.session_state.get('user')


def get_auth_token() -> Optional[str]:
    """Get authentication token from session state."""
    return st.session_state.get('token')


def login_user(username: str, password: str) -> bool:
    """
    Login user and store credentials in session state.
    
    Args:
        username: Username
        password: Password
        
    Returns:
        True if login successful, False otherwise
    """
    api_url = get_api_url()
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{api_url}/api/v1/auth/login",
                data={
                    "username": username,
                    "password": password
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            result = response.json()
            
            # Store token
            st.session_state.token = result.get('access_token')
            
            # Get user info
            user_response = client.get(
                f"{api_url}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            )
            user_response.raise_for_status()
            user = user_response.json()
            
            # Store user and authentication status
            st.session_state.user = user
            st.session_state.authenticated = True
            
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            st.error("Invalid username or password")
        else:
            st.error(f"Login error: {e.response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Login error: {e}")
        st.error(f"Login error: {str(e)}")
        return False


def format_currency(value: float) -> str:
    """Format value as currency."""
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    """Format number with commas."""
    return f"{value:,.0f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    return f"{value:.1f}%"

