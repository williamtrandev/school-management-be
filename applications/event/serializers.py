from rest_framework import serializers
from .models import Event, EventType, StudentEventPermission


# Request Serializers
class EventCreateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['event_type', 'classroom', 'student', 'date', 'period', 'points', 'description']


class EventUpdateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['event_type', 'classroom', 'student', 'date', 'period', 'points', 'description']


class EventBulkCreateRequestSerializer(serializers.Serializer):
    events = EventCreateRequestSerializer(many=True)


class EventBulkSyncRequestSerializer(serializers.Serializer):
    """Request for bulk upsert/delete synchronization.
    Accepts the desired list of events; backend will update existing,
    create missing, and delete removed within the same (classroom, date, period) scopes.
    Optionally accepts top-level scope (classroom/date/period) to allow deleting all
    events in a scope when desired events is empty.
    """
    classroom = serializers.PrimaryKeyRelatedField(queryset=Event._meta.get_field('classroom').remote_field.model.objects.all(), required=False)
    date = serializers.DateField(required=False)
    period = serializers.IntegerField(required=False, allow_null=True)
    events = EventCreateRequestSerializer(many=True)


# Response Serializers
class EventTypeResponseSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    allowed_roles_display = serializers.CharField(source='get_allowed_roles_display', read_only=True)
    
    class Meta:
        model = EventType
        fields = [
            'id', 'name', 'description', 'category', 'category_display', 
            'allowed_roles', 'allowed_roles_display', 'default_points', 
            'is_active', 'created_at'
        ]


class EventResponseSerializer(serializers.ModelSerializer):
    event_type = EventTypeResponseSerializer(read_only=True)
    classroom_name = serializers.CharField(source='classroom.full_name', read_only=True)
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'event_type', 'classroom', 'classroom_name', 'student', 'student_name',
            'date', 'period', 'points', 'description', 'recorded_by', 'recorded_by_name',
            'status', 'approved_by', 'approved_by_name', 'approved_at', 'rejection_notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'recorded_by', 'created_at', 'updated_at']


class EventBulkCreateResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    created_count = serializers.IntegerField()
    events = EventResponseSerializer(many=True)

class EventBulkSyncResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    created_count = serializers.IntegerField()
    updated_count = serializers.IntegerField()
    deleted_count = serializers.IntegerField()
    events = EventResponseSerializer(many=True)


class EventBulkApprovalRequestSerializer(serializers.Serializer):
    classroom = serializers.PrimaryKeyRelatedField(queryset=Event._meta.get_field('classroom').remote_field.model.objects.all(), required=False)
    date = serializers.DateField(required=False)
    period = serializers.IntegerField(required=False, allow_null=True)
    # Optional: approve/reject by explicit ids list
    event_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    rejection_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


# Student Event Permission Serializers
class StudentEventPermissionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEventPermission
        fields = ['student', 'classroom', 'expires_at', 'notes']


class StudentEventPermissionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEventPermission
        fields = ['is_active', 'expires_at', 'notes']


class StudentEventPermissionResponseSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_code = serializers.CharField(source='student.student_code', read_only=True)
    classroom_name = serializers.CharField(source='classroom.full_name', read_only=True)
    granted_by_name = serializers.CharField(source='granted_by.full_name', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = StudentEventPermission
        fields = [
            'id', 'student', 'student_name', 'student_code', 'classroom', 'classroom_name',
            'granted_by', 'granted_by_name', 'is_active', 'granted_at', 'expires_at',
            'notes', 'is_expired', 'is_valid', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'granted_by', 'granted_at', 'created_at', 'updated_at'] 