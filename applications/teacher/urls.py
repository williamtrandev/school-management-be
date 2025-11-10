from django.urls import path
from . import views

app_name = 'teacher'

urlpatterns = [
    # Mongo teachers only (remove SQL endpoints)
    path('mongo', views.mongo_teachers_list, name='mongo-teachers-list'),
    path('mongo/create', views.mongo_teachers_create, name='mongo-teachers-create'),
    path('mongo/<str:id>', views.mongo_teachers_detail, name='mongo-teachers-detail'),
    path('mongo/<str:id>/update', views.mongo_teachers_update, name='mongo-teachers-update'),
    path('mongo/<str:id>/delete', views.mongo_teachers_delete, name='mongo-teachers-delete'),
] 