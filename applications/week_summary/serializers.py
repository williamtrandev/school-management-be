from rest_framework import serializers
from .models import WeekSummary
from applications.classroom.serializers import ClassroomSerializer
from applications.user_management.models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer cho User"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']


class WeekSummarySerializer(serializers.ModelSerializer):
    """Serializer cho WeekSummary"""
    classroom = ClassroomSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)

    class Meta:
        model = WeekSummary
        fields = [
            'id', 'classroom', 'week_number', 'year', 'positive_points',
            'negative_points', 'total_points', 'rank', 'is_approved',
            'approved_by', 'approved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WeekSummaryCreateRequestSerializer(serializers.ModelSerializer):
    """Serializer cho tạo WeekSummary"""
    class Meta:
        model = WeekSummary
        fields = ['classroom_id', 'week_number', 'year', 'positive_points', 'negative_points']

    def validate(self, attrs):
        """Validate unique constraint"""
        classroom_id = attrs.get('classroom_id')
        week_number = attrs.get('week_number')
        year = attrs.get('year')
        
        if classroom_id and week_number and year:
            existing_summary = WeekSummary.objects.filter(
                classroom_id=classroom_id,
                week_number=week_number,
                year=year
            )
            
            if self.instance:
                existing_summary = existing_summary.exclude(id=self.instance.id)
            
            if existing_summary.exists():
                raise serializers.ValidationError('Tổng kết tuần này đã tồn tại')
        
        return attrs


class WeekSummaryUpdateRequestSerializer(serializers.ModelSerializer):
    """Serializer cho cập nhật WeekSummary"""
    class Meta:
        model = WeekSummary
        fields = ['positive_points', 'negative_points'] 