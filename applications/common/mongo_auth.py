from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import AnonymousUser
from applications.common.mongo import get_users_collection
import logging
from bson import ObjectId


class MongoUser:
    """MongoDB User class để tương thích với Django authentication"""
    def __init__(self, doc):
        self.id = str(doc['_id'])
        self.email = doc.get('email', '')
        self.username = doc.get('username', '')
        self.first_name = doc.get('first_name', '')
        self.last_name = doc.get('last_name', '')
        self.full_name = doc.get('full_name', '')
        self.role = doc.get('role', 'user')
        self.is_active = doc.get('status') == 'active'
        self.is_authenticated = True
        self.is_anonymous = False
    
    def has_perm(self, perm, obj=None):
        return True
    
    def has_module_perms(self, app_label):
        return True
    
    def get_username(self):
        return self.username
    
    def get_full_name(self):
        return self.full_name
    
    def get_short_name(self):
        return self.first_name


class MongoJWTAuthentication(JWTAuthentication):
    """Custom JWT Authentication cho MongoDB users"""
    
    def authenticate(self, request):
        """
        Override authenticate method để sử dụng MongoDB thay vì Django User
        """
        try:
            # Lấy token từ header
            header = self.get_header(request)
            if header is None:
                return None
            
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None
            
            # Validate token
            validated_token = self.get_validated_token(raw_token)
            
            # Tìm user trong MongoDB
            user = self.get_user(validated_token)
            if user is None or user.is_anonymous:
                return None
                
            return user, validated_token
            
        except Exception as exc:
            logging.getLogger(__name__).exception(f'MongoJWTAuthentication: Authentication error: {exc}')
            return None
    
    def get_user(self, validated_token):
        """
        Tìm user trong MongoDB dựa trên token
        """
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                return AnonymousUser()
            
            # Tìm user trong MongoDB
            users_coll = get_users_collection()
            user_doc = users_coll.find_one({'_id': ObjectId(user_id)})
            
            if not user_doc:
                logging.getLogger(__name__).warning(f'MongoJWTAuthentication: User not found in MongoDB: {user_id}')
                return AnonymousUser()
            
            # Tạo MongoUser object
            mongo_user = MongoUser(user_doc)
            logging.getLogger(__name__).debug(f'MongoJWTAuthentication: User authenticated: {mongo_user.email}')
            return mongo_user
            
        except Exception as exc:
            logging.getLogger(__name__).exception(f'MongoJWTAuthentication: Error getting user: {exc}')
            return AnonymousUser()
    
    def get_validated_token(self, raw_token):
        """
        Validate JWT token
        """
        try:
            token = AccessToken(raw_token)
            return token
        except TokenError as exc:
            logging.getLogger(__name__).warning(f'MongoJWTAuthentication: Invalid token: {exc}')
            raise InvalidToken(exc)
