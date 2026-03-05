from social_core.exceptions import AuthException
from social_django.models import UserSocialAuth
from social_core.exceptions import AuthForbidden
from django.contrib.auth import get_user_model

User = get_user_model()

def associate_by_email(backend, details, user=None, *args, **kwargs):
    email = details.get('email')
    User = get_user_model()
    if not email:
        raise AuthException(backend, 'No email provided')

    existing_user = User.objects.filter(email=email).first()
    if existing_user and user is None:
        return {'user': existing_user}
    
    return {}


import logging
logger = logging.getLogger(__name__)

def debug_google_response(strategy, details, backend, response, user=None, *args, **kwargs):
    """
    Debugging function to log the full response from Google.
    """
    logger.info(f"Google OAuth2 Response: {response}")  # Print the full response
    print("Google OAuth2 Response:", response)  # Log in console
    return {}

