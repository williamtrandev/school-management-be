from django.urls import path
from . import views

urlpatterns = [
    path('login', views.mongo_login, name='mongo-login'),
]




