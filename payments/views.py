import json
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from .paypal_service import create_paypal_order, capture_paypal_order
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_order(request):
    order = create_paypal_order()

    user = request.user
    user.paypal_order_id = order["id"]
    user.save()

    return Response(order, status=status.HTTP_201_CREATED)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def capture_order(request, order_id):
    capture = capture_paypal_order(order_id)
    return Response(capture, status=status.HTTP_200_OK)
    
User = get_user_model()

@csrf_exempt
def paypal_webhook(request):
    if request.method == "POST":
        data = json.loads(request.body)

        event_type = data.get("event_type")
        resource = data.get("resource", {})
        capture_id = resource.get("id")

        order_id = None
        if "supplementary_data" in resource:
            order_id = resource["supplementary_data"].get("related_ids", {}).get("order_id")

        print("Webhook capture ID:", capture_id)
        print("Original PayPal Order ID:", order_id)

        if event_type == "PAYMENT.CAPTURE.COMPLETED" and order_id:
            user = User.objects.filter(paypal_order_id=order_id).first()
            if user:
                user.is_pro = True
                user.save()
                return JsonResponse({"status": "User upgraded to Pro"})
            else:
                print("No user found with order ID:", order_id)

        return JsonResponse({"status": "Webhook received"})

    return JsonResponse({"error": "Invalid request"}, status=400)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_plan(request):
    return Response({"is_pro": request.user.is_pro})
