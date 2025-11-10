from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('auth/login', views.login, name='auth_login'),
    path('auth/mongo-login', views.login_with_mongo, name='auth_mongo_login'),
    path('auth/mongo-register', views.register_with_mongo, name='auth_mongo_register'),
    path('auth/register', views.register, name='auth_register'),
    path('auth/refresh', views.refresh_token, name='auth_refresh'),
    path('auth/logout', views.logout, name='auth_logout'),
    path('auth/change_password', views.change_password, name='auth_change_password'),
    
    # User URLs
    path('users', views.user_list, name='user_list'),
    path('users/profile', views.user_profile, name='user_profile'),
    path('users/update_profile', views.update_profile, name='update_profile'),
] 