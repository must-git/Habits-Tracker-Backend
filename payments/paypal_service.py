import requests
from django.conf import settings

PAYPAL_CLIENT_ID = settings.PAYPAL_CLIENT_ID
PAYPAL_CLIENT_SECRET = settings.PAYPAL_CLIENT_SECRET
PAYPAL_API_URL = settings.PAYPAL_API_URL


def get_paypal_access_token():
    url = f"{PAYPAL_API_URL}/v1/oauth2/token"
    headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    
    response = requests.post(url, headers=headers, data=data, auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET))
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        raise Exception(f"Error getting PayPal token: {response.json()}")


def create_paypal_order():
    url = f"{PAYPAL_API_URL}/v2/checkout/orders"
    access_token = get_paypal_access_token()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": "4.99"
                }
            }
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()


def capture_paypal_order(order_id):
    url = f"{PAYPAL_API_URL}/v2/checkout/orders/{order_id}/capture"
    access_token = get_paypal_access_token()
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    
    response = requests.post(url, headers=headers)
    return response.json()
