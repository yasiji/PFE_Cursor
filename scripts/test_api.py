"""Test the API endpoints."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def login():
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", data={"username": "test_user", "password": "test123"})
    if resp.status_code == 200:
        return resp.json()["access_token"]
    print(f"Login error: {resp.status_code} - {resp.text}")
    return None

def test_products(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/stores/235/products", headers=headers)
    if resp.status_code == 200:
        products = resp.json()[:5]
        print("\n=== PRODUCTS ===")
        for p in products:
            print(f"  {p['name']}")
            print(f"    Category: {p['category']}")
            print(f"    Stock: {p['current_stock']}")
            print(f"    Sold Today: {p['items_sold_today']}")
            print(f"    Expiry: {p['expiry_date']}")
            print(f"    Days Until Expiry: {p['days_until_expiry']}")
    else:
        print(f"Products error: {resp.status_code} - {resp.text}")

def test_inventory(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/stores/235/inventory", headers=headers)
    if resp.status_code == 200:
        items = resp.json()[:5]
        print("\n=== INVENTORY ===")
        for item in items:
            print(f"  {item['name']}")
            print(f"    Category: {item['category']}")
            print(f"    Shelf: {item['shelf_quantity']}, Backroom: {item['backroom_quantity']}")
            print(f"    Expiry Date: {item['expiry_date']}")
            print(f"    Days Until Expiry: {item['days_until_expiry']}")
    else:
        print(f"Inventory error: {resp.status_code} - {resp.text}")

def test_forecast_insights(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/api/v1/stores/235/forecast-insights", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print("\n=== FORECAST INSIGHTS ===")
        print(f"  Tomorrow: {data['tomorrow']['forecasted_items']} items, ${data['tomorrow']['forecasted_revenue']:.2f} revenue")
        print(f"  Next Week (daily avg): {data['next_week']['daily_avg_items']} items/day")
        print(f"  Next Month (daily avg): {data['next_month']['daily_avg_items']} items/day")
    else:
        print(f"Forecast insights error: {resp.status_code} - {resp.text}")

def main():
    token = login()
    if not token:
        return
    
    print("Login successful!")
    test_products(token)
    test_inventory(token)
    test_forecast_insights(token)

if __name__ == "__main__":
    main()

