from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings

from .serializers import (
    LoginRequestSerializer, RegisterRequestSerializer, ChangePasswordRequestSerializer,
    UserResponseSerializer, LoginResponseSerializer, RegisterResponseSerializer, 
    ChangePasswordResponseSerializer
)
from applications.permissions import IsAdminUser
from applications.common.mongo import get_users_collection
from applications.common.responses import ok, created, bad_request, unauthorized, server_error
import bcrypt
import logging

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def login_with_mongo(request):
    """Đăng nhập sử dụng MongoDB (song song với login SQL hiện tại)."""
    data = request.data or {}
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').encode('utf-8')

    if not email or not password:
        return bad_request('Thiếu email hoặc password')

    try:
        logging.getLogger(__name__).info('login_with_mongo: start email=%s', email)
        users = get_users_collection()
        logging.getLogger(__name__).debug('login_with_mongo: querying users collection')
        doc = users.find_one({'email': email})
        if not doc:
            logging.getLogger(__name__).warning('login_with_mongo: user not found email=%s', email)
            return unauthorized('Sai thông tin đăng nhập')

        stored_hash = (doc.get('password_hash') or '').encode('utf-8')
        if not stored_hash or not bcrypt.checkpw(password, stored_hash):
            logging.getLogger(__name__).warning('login_with_mongo: invalid password email=%s', email)
            return unauthorized('Sai thông tin đăng nhập')

        # Tạo JWT token trực tiếp từ MongoDB user
        from rest_framework_simplejwt.tokens import RefreshToken
        from django.contrib.auth.models import AnonymousUser
        
        # Tạo một user object tạm thời để phát hành JWT
        class MongoUser:
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
        
        mongo_user = MongoUser(doc)
        # Tạo JWT token với user_id từ MongoDB
        refresh = RefreshToken()
        refresh['user_id'] = str(doc['_id'])
        refresh['email'] = doc.get('email', '')
        refresh['role'] = doc.get('role', 'user')
        
        response_data = {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': mongo_user.id,
                'email': mongo_user.email,
                'username': mongo_user.username,
                'first_name': mongo_user.first_name,
                'last_name': mongo_user.last_name,
                'full_name': mongo_user.full_name,
                'role': mongo_user.role,
                'is_active': mongo_user.is_active,
            },
        }
        logging.getLogger(__name__).info('login_with_mongo: success email=%s', email)
        response_serializer = LoginResponseSerializer(data=response_data)
        response_serializer.is_valid()
        return ok(response_serializer.data)
    except Exception as exc:
        logging.getLogger(__name__).exception('login_with_mongo: error email=%s', email)
        return server_error(exc)


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register_with_mongo(request):
    """Đăng ký tài khoản mới trong MongoDB."""
    data = request.data or {}
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').encode('utf-8')
    full_name = (data.get('full_name') or '').strip()
    role = (data.get('role') or 'user').strip()

    if not email or not password:
        return bad_request('Thiếu email hoặc password')

    try:
        logging.getLogger(__name__).info('register_with_mongo: start email=%s', email)
        users = get_users_collection()
        if users.find_one({'email': email}):
            logging.getLogger(__name__).warning('register_with_mongo: email exists email=%s', email)
            return bad_request('Email đã tồn tại')

        password_hash = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

        doc = {
            'username': email,  # Sử dụng email làm username
            'password_hash': password_hash,
            'full_name': full_name,
            'email': email,
            'role': role,
        }
        result = users.insert_one(doc)

        # Tạo JWT token trực tiếp từ MongoDB user
        from rest_framework_simplejwt.tokens import RefreshToken
        
        # Tạo một user object tạm thời để phát hành JWT
        class MongoUser:
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
        
        mongo_user = MongoUser(doc)
        # Tạo JWT token với user_id từ MongoDB
        refresh = RefreshToken()
        refresh['user_id'] = str(doc['_id'])
        refresh['email'] = doc.get('email', '')
        refresh['role'] = doc.get('role', 'user')
        
        response_data = {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': {
                'id': mongo_user.id,
                'email': mongo_user.email,
                'username': mongo_user.username,
                'first_name': mongo_user.first_name,
                'last_name': mongo_user.last_name,
                'full_name': mongo_user.full_name,
                'role': mongo_user.role,
                'is_active': mongo_user.is_active,
            },
        }
        logging.getLogger(__name__).info('register_with_mongo: success email=%s', email)
        response_serializer = RegisterResponseSerializer(data=response_data)
        response_serializer.is_valid()
        return created(response_serializer.data, message='Đăng ký thành công')
    except Exception as exc:
        logging.getLogger(__name__).exception('register_with_mongo: error email=%s', email)
        return server_error(exc)

# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Đăng nhập"""
    serializer = LoginRequestSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserResponseSerializer(user).data
        }
        
        response_serializer = LoginResponseSerializer(data=response_data)
        response_serializer.is_valid()
        return Response(response_serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Đăng ký"""
    serializer = RegisterRequestSerializer(data=request.data)
    if serializer.is_valid():
        # Tạo user mới
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            role=serializer.validated_data['role'],
            phone=serializer.validated_data.get('phone', '')
        )
        
        # Tạo token
        refresh = RefreshToken.for_user(user)
        
        response_data = {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserResponseSerializer(user).data
        }
        
        response_serializer = RegisterResponseSerializer(data=response_data)
        response_serializer.is_valid()
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_token(request):
    """Refresh token"""
    try:
        refresh_token = request.data.get('refresh_token')
        refresh = RefreshToken(refresh_token)
        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh)
        })
    except Exception:
        return Response({'error': 'Invalid refresh token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def logout(request):
    """Đăng xuất"""
    try:
        refresh_token = request.data.get('refresh_token')
        refresh = RefreshToken(refresh_token)
        refresh.blacklist()
        return Response({'message': 'Đăng xuất thành công'})
    except Exception:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Đổi mật khẩu"""
    serializer = ChangePasswordRequestSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        if user.check_password(serializer.validated_data['old_password']):
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            response_data = {'message': 'Đổi mật khẩu thành công'}
            response_serializer = ChangePasswordResponseSerializer(data=response_data)
            response_serializer.is_valid()
            return Response(response_serializer.data)
        else:
            return Response({'error': 'Mật khẩu cũ không đúng'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# User Views
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def user_list(request):
    """Danh sách users (Admin only)"""
    users = User.objects.all()
    
    # Filter theo role
    role = request.query_params.get('role', None)
    if role:
        users = users.filter(role=role)
    
    serializer = UserResponseSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Lấy thông tin profile của user hiện tại"""
    serializer = UserResponseSerializer(request.user)
    return Response(serializer.data)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """Cập nhật profile của user hiện tại"""
    serializer = UserResponseSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 