import base64
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from jwt.exceptions import JWTDecodeError
from jwt import JWT, jwk_from_dict

class CustomJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        User = get_user_model()

        try:
            payload = self.decode_token(token)
            user_id = payload.get('id')

            if not user_id:
                raise AuthenticationFailed('Invalid token: User ID not found')

            user = User.objects.get(id=user_id)

            return (user, token)

        except JWTDecodeError:
            raise AuthenticationFailed('Invalid token')
        except User.DoesNotExist:
            raise AuthenticationFailed('User not found')

    def decode_token(self, token):
        jwt_instance = JWT()
        secret_key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()).decode()
        payload = jwt_instance.decode(token, jwk_from_dict({'k': secret_key, 'kty': 'oct'}))
        return payload