from django.urls import path
from . import mongo_views

app_name = 'week_summary'

urlpatterns = [
    # Test endpoints
    path('test', mongo_views.mongo_test, name='mongo-test'),
    path('debug-events', mongo_views.mongo_debug_events, name='debug-events'),
    
    # Week Summary CRUD - MongoDB
    path('', mongo_views.mongo_week_summary_list, name='week-summary-list'),
    path('<str:id>', mongo_views.mongo_week_summary_detail, name='week-summary-detail'),
    
    # Rankings API - MongoDB
    path('rankings/realtime', mongo_views.mongo_realtime_rankings, name='realtime-rankings'),
    path('rankings/realtime/classroom-detail', mongo_views.mongo_realtime_classroom_detail, name='realtime-classroom-detail'),
    
    # Week Milestone API
    path('milestone', mongo_views.mongo_week_milestone, name='week-milestone'),
] 