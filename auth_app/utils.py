import requests
from django.conf import settings

def verify_email(email):
    api_key = settings.ABSTRACTAPI_API_KEY
    url = f"https://emailvalidation.abstractapi.com/v1/?api_key={api_key}&email={email}"
    
    try:
        response = requests.get(url)
        response.raise_for_status() 
        data = response.json()

        is_valid = data.get("is_valid_format", {}).get("value", False)
        is_deliverable = data.get("deliverability", "") == "DELIVERABLE"

        return is_valid and is_deliverable
    except requests.exceptions.RequestException as e:
        print(f"Error verifying email: {e}")
        return False