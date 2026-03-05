from django.urls import path
from .views import signup, signin, forgot_password, reset_password, verify_token, google_signin_redirect, user_info, verify_signup, get_current_date

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/', reset_password, name='reset-password'),
    path('google-signin-redirect/', google_signin_redirect, name='google_signin_redirect'),
    path('verify-signup/', verify_signup, name='verify-signup'),
    path('verify-token/', verify_token, name='verify-token'),
    path('user-info/', user_info, name='user_info'),
    path('current-date/', get_current_date, name='current-date'),
]
