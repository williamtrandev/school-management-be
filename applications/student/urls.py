from django.urls import path
from . import views

app_name = 'student'

urlpatterns = [
    # Mongo students only (remove SQL endpoints)
    path('mongo', views.mongo_students_list, name='mongo-students-list'),
    path('mongo/dropdown', views.mongo_students_dropdown, name='mongo-students-dropdown'),
    path('mongo/create', views.mongo_students_create, name='mongo-students-create'),
    path('mongo/create-by-teacher', views.mongo_students_create_by_teacher, name='mongo-students-create-by-teacher'),
    path('mongo/my-classroom-students', views.mongo_students_my_classroom, name='mongo-students-my-classroom'),
    path('mongo/my-classroom-students/dropdown', views.mongo_students_my_classroom_dropdown, name='mongo-students-my-classroom-dropdown'),
    path('mongo/<str:id>', views.mongo_students_detail, name='mongo-students-detail'),
    path('mongo/<str:id>/update', views.mongo_students_update, name='mongo-students-update'),
    path('mongo/<str:id>/delete', views.mongo_students_delete, name='mongo-students-delete'),
    path('import', views.mongo_students_import, name='mongo-students-import'),
    path('import/template', views.mongo_students_import_template, name='mongo-students-import-template'),
]