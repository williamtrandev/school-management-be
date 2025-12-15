from django.urls import path, include
from applications.common.healthcheck import healthcheck
from applications.common.academic_year_views import current_academic_year

urlpatterns = [
    # Health check endpoint (public, no auth required)
    path('health', healthcheck, name='healthcheck'),
    
    # Academic year config
    path('mongo/academic-year/current', current_academic_year, name='current-academic-year'),
    
    # User Management (Mongo auth)
    path('', include('applications.user_management.urls')),

    # Events (Mongo-only)
    path('events/', include('applications.event.urls')),

    # Classrooms (Mongo-only)
    path('classrooms/', include('applications.classroom.urls')),

    # Students
    path('students/', include('applications.student.urls')),

    # Teachers
    path('teachers/', include('applications.teacher.urls')),
    
    # Week Summaries - MongoDB
    path('mongo/week-summaries/', include('applications.week_summary.urls')),
] 