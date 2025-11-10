from django.urls import path
from . import mongo_views

urlpatterns = [
    # Event Types APIs - MongoDB
    path('types', mongo_views.mongo_event_types_list, name='event-types-list'),
    path('types/template', mongo_views.mongo_event_types_template, name='event-types-template'),
    path('types/<str:pk>', mongo_views.mongo_event_types_detail, name='event-types-detail'),
    path('types/<str:pk>/update', mongo_views.mongo_event_types_update, name='event-types-update'),
    path('types/<str:pk>/delete', mongo_views.mongo_event_types_delete, name='event-types-delete'),
    
    # Events APIs - MongoDB (Optimized)
    path('', mongo_views.mongo_events_optimized_list, name='events-list'),
    path('detail', mongo_views.mongo_events_optimized_detail, name='events-detail'),
    path('create', mongo_views.mongo_events_optimized_create, name='events-create'),
    path('replace', mongo_views.mongo_events_optimized_replace, name='events-replace'),
    path('bulk-sync', mongo_views.mongo_events_bulk_sync, name='events-bulk-sync'),
    path('bulk-replace', mongo_views.mongo_events_bulk_replace, name='events-bulk-replace'),
    path('approve', mongo_views.mongo_events_approve, name='events-approve'),
    
    # Public Events API (không cần authentication)
    path('public', mongo_views.mongo_events_public, name='events-public'),
    
    # Attendance Export API
    path('attendance/export', mongo_views.mongo_attendance_export, name='attendance-export'),
]