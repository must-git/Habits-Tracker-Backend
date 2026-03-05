from django.urls import path
from .views import create_order, capture_order, paypal_webhook, user_plan

urlpatterns = [
    path("api/orders/", create_order, name="create_order"),
    path("api/orders/<str:order_id>/capture/", capture_order, name="capture_order"),
    path("webhook/", paypal_webhook, name="paypal-webhook"),
    path("user_plan/", user_plan, name="user_plan"),
]