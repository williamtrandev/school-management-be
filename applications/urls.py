from django.urls import path, include

urlpatterns = [
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