from django.urls import path
from . import views

app_name = 'classroom'

urlpatterns = [
    # Mongo endpoints only (remove SQL endpoints)
    path('mongo', views.mongo_classrooms_list, name='mongo-classrooms-list'),
    path('mongo/dropdown', views.mongo_classrooms_dropdown, name='mongo-classrooms-dropdown'),
    path('mongo/dropdown/public', views.mongo_classrooms_dropdown_public, name='mongo-classrooms-dropdown-public'),
    path('mongo/<str:id>', views.mongo_classrooms_detail, name='mongo-classrooms-detail'),
    path('mongo/create', views.mongo_classrooms_create, name='mongo-classrooms-create'),
    path('mongo/<str:id>/update', views.mongo_classrooms_update, name='mongo-classrooms-update'),
    path('mongo/<str:id>/delete', views.mongo_classrooms_delete, name='mongo-classrooms-delete'),
    path('stats', views.get_classroom_stats, name='classroom-stats'),
] 