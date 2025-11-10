from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from pymongo import MongoClient
import bcrypt


def _get_mongo_client():
    uri = getattr(settings, 'MONGO_URI', None)
    if not uri:
        raise RuntimeError('MONGO_URI is not configured')
    return MongoClient(uri, tlsAllowInvalidCertificates=True)


@api_view(['POST'])
@permission_classes([AllowAny])
def mongo_login(request):
    """Authenticate user against MongoDB collection and return basic profile.

    Expected JSON body: { "username": "...", "password": "..." }
    Env/settings required: MONGO_URI, MONGO_DB, MONGO_USERS_COLLECTION
    User doc fields: username, password_hash (bcrypt), role, full_name, email
    """
    payload = request.data or {}
    username = (payload.get('username') or '').strip()
    password = (payload.get('password') or '').encode('utf-8')

    if not username or not password:
        return Response({'detail': 'Missing username or password'}, status=status.HTTP_400_BAD_REQUEST)

    db_name = getattr(settings, 'MONGO_DB', None)
    coll_name = getattr(settings, 'MONGO_USERS_COLLECTION', 'users')
    if not db_name:
        return Response({'detail': 'Mongo database not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        client = _get_mongo_client()
        users = client[db_name][coll_name]
        user_doc = users.find_one({'username': username})
        if not user_doc:
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        stored_hash = (user_doc.get('password_hash') or '').encode('utf-8')
        if not stored_hash or not bcrypt.checkpw(password, stored_hash):
            return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        profile = {
            'id': str(user_doc.get('_id')),
            'username': user_doc.get('username'),
            'full_name': user_doc.get('full_name') or '',
            'email': user_doc.get('email') or '',
            'role': user_doc.get('role') or 'user',
        }

        return Response({'authenticated': True, 'user': profile}, status=status.HTTP_200_OK)
    except Exception as exc:
        return Response({'detail': str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        try:
            client.close()  # type: ignore
        except Exception:
            pass




