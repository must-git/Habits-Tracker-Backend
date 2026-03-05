from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import urlsafe_base64_decode
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from jwt.exceptions import JWTDecodeError
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.http import JsonResponse
from django.core.cache import cache
from jwt import JWT, jwk_from_dict
from django.conf import settings
from .utils import verify_email
from .models import User
import requests
import base64
import random
import string
import json

SECRET_KEY = settings.SECRET_KEY

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name')
            email = data.get('email')
            password = data.get('password')

            if not name or not email or not password:
                return JsonResponse({'message': 'Missing fields'}, status=400)
            
            if not verify_email(email):
                return JsonResponse({'message': 'Invalid or undeliverable email address'}, status=400)

            User = get_user_model()
            if User.objects.filter(email=email).exists():
                return JsonResponse({'message': 'Email already exists'}, status=400)

            verification_code = generate_verification_code()
            cache.set(f'verify_code_{email}', verification_code, timeout=600)
            cache.set(f'temp_user_{email}', {'name': name, 'email': email, 'password': password}, timeout=600)

            send_mail(
                'Verify Your Account',
                f'Your verification code is: {verification_code}',
                'no-reply@habittracker.com',
                [email],
                fail_silently=False,
            )

            return JsonResponse({"message": "Signup successful. Verification code sent.", "email": email}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
    
@csrf_exempt
def verify_signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            code = data.get('code')

            if not email or not code:
                return JsonResponse({'message': 'Missing email or verification code'}, status=400)

            stored_code = cache.get(f'verify_code_{email}')
            temp_user = cache.get(f'temp_user_{email}')

            if not stored_code or not temp_user:
                return JsonResponse({'message': 'Invalid or expired verification code'}, status=400)

            if stored_code != code:
                return JsonResponse({'message': 'Incorrect verification code'}, status=400)

            User = get_user_model()
            user = User.objects.create_user(
                email=temp_user['email'], 
                password=temp_user['password'], 
                first_name=temp_user['name']
            )
            user.is_active = True
            user.save()

            exp = datetime.utcnow() + timedelta(days=1)
            payload = {
                'id': user.id,
                'exp': int(exp.timestamp()),
                'iat': int(datetime.utcnow().timestamp())
            }
            jwt_instance = JWT()
            secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
            token = jwt_instance.encode(payload, jwk_from_dict({'k': secret_key, 'kty': 'oct'}), alg='HS256')

            cache.delete(f'verify_code_{email}')
            cache.delete(f'temp_user_{email}')

            return JsonResponse({'message': 'Email verified successfully', 'token': token})

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method'}, status=405)
    
@csrf_exempt
def signin(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return JsonResponse({'error': 'Missing fields'}, status=400)

            user = authenticate(email=email, password=password)
            if user:
                exp = datetime.utcnow() + timedelta(days=1)
                payload = {
                    'id': user.id,
                    'exp': int(exp.timestamp()),
                    'iat': int(datetime.utcnow().timestamp())
                }
                jwt_instance = JWT()
                secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
                token = jwt_instance.encode(payload, jwk_from_dict({'k': secret_key, 'kty': 'oct'}), alg='HS256')
                return JsonResponse({'token': token, 'username': user.email, 'user_id': user.id})
        except Exception as e:
            print(f"Error during signin: {str(e)}")
            return JsonResponse({'message': str(e)}, status=400)
    return JsonResponse({'message': 'Invalid method'}, status=400)

@csrf_exempt
def forgot_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            return JsonResponse({'error': 'Email is required'}, status=400)

        User = get_user_model()
        try:
            user = User.objects.get(email=email)

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"http://localhost:3000/reset-password/{uid}/{token}"

            send_mail(
                'Password reset',
                f'Click this link to reset your password: {reset_link}',
                'noreply@habittracker.com',
                [email],
            )
            return JsonResponse({'message': 'Email sent successfully'})
        except User.DoesNotExist:
            return JsonResponse({'message': 'User does not exist'})
        
    return JsonResponse({'error': 'Invalid method'}, status=400)

@csrf_exempt
def reset_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        uidb64 = data.get('uid')
        token = data.get('token')
        new_password = data.get('password')

        if not uidb64 or not token or not new_password:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return JsonResponse({'message': 'Password reset successfully'})
        else:
            return JsonResponse({'error': 'Invalid token or user ID'}, status=400)

    return JsonResponse({'error': 'Invalid method'}, status=400)
    

def generate_token(user):
    exp = datetime.utcnow() + timedelta(days=1)
    payload = {
        'id': user.id,
        'exp': int(exp.timestamp()),
        'iat': int(datetime.utcnow().timestamp())
    }
    jwt_instance = JWT()
    secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
    token = jwt_instance.encode(payload, jwk_from_dict({'k': secret_key, 'kty': 'oct'}), alg='HS256')
    return token

def google_signin_redirect(request):
    print(f"User authenticated? {request.user.is_authenticated}, User: {request.user}")
    user = request.user

    if not user.is_authenticated:
        return redirect("http://localhost:3000/signin")
    
    if not user.is_google_user:
        user.is_google_user = True
        user.save()

    token = generate_token(user)
    print(token)
    response = redirect(f'http://localhost:3000/?token={token}')
    return response

from django.middleware.csrf import get_token
from datetime import timedelta

@csrf_exempt
def verify_token(request):
    if request.method == 'POST':
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split(' ')[1]
            jwt_instance = JWT()
            secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
            key = jwk_from_dict({'k': secret_key, 'kty': 'oct'})
            try:
                payload = jwt_instance.decode(token, key, do_verify=True, algorithms=['HS256'])
                print(f"Token payload: {payload}") 
                return JsonResponse({'valid': True})
            except JWTDecodeError as e:
                error_message = str(e)
                print(f"JWTDecodeError: {error_message}")
                if 'expired' in error_message:
                    return JsonResponse({'valid': False, 'error': 'Token has expired'}, status=401)
                else:
                    return JsonResponse({'valid': False, 'error': 'Invalid token'}, status=401)
        print("Token not provided")
        return JsonResponse({'valid': False, 'error': 'Token not provided'}, status=401)
    print("Invalid method")
    return JsonResponse({'error': 'Invalid method'}, status=400)

@csrf_exempt
def user_info(request):
    if request.method == 'GET':
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                return JsonResponse({'error': 'No token provided'}, status=401)
            
            token = auth_header.split(' ')[1]
            jwt_instance = JWT()
            secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
            key = jwk_from_dict({'k': secret_key, 'kty': 'oct'})
            payload = jwt_instance.decode(token, key, do_verify=True, algorithms=['HS256'])
            
            user = User.objects.get(id=payload['id'])
            avatar_url = None
            
            try:
                social_auth = user.social_auth.get(provider='google-oauth2')
                if social_auth and social_auth.extra_data:
                    extra_data = social_auth.extra_data
                    print(f"Extra data: {extra_data}")
                    
                    if 'access_token' in extra_data:
                        access_token = extra_data['access_token']
                        try:
                            headers = {
                                'Authorization': f'Bearer {access_token}',
                                'Accept': 'application/json'
                            }
                            profile_response = requests.get(
                                'https://www.googleapis.com/oauth2/v3/userinfo',
                                headers=headers,
                                timeout=5
                            )
                            print(f"Profile response status: {profile_response.status_code}")
                            print(f"Profile response: {profile_response.text}")
                            
                            if profile_response.ok:
                                profile_data = profile_response.json()
                                avatar_url = profile_data.get('picture')
                            else:
                                print(f"Failed to get profile. Status code: {profile_response.status_code}")
                        except requests.exceptions.RequestException as e:
                            print(f"Request error: {str(e)}")
                            
            except ObjectDoesNotExist:
                print("No social auth data found for user")
            except Exception as e:
                print(f"Error getting social auth data: {str(e)}")

            response_data = {
                'firstname': user.first_name,
                'lastname': user.last_name,
                'avatar': avatar_url,
                'email': user.email
            }
            print(f"Returning data: {response_data}")
            return JsonResponse(response_data)
            
        except Exception as e:
            print(f"Error in user_info: {str(e)}")
            return JsonResponse({'error': str(e)}, status=401)
            
    return JsonResponse({'error': 'Invalid method'}, status=400)

def get_current_date(request):
    current_date = datetime.today().date()
    return JsonResponse({'current_date': current_date})