from rest_framework import serializers


class ClassroomEventDetailSerializer(serializers.Serializer):
    date = serializers.CharField()
    period = serializers.IntegerField()
    event_type_key = serializers.CharField(allow_blank=True)
    event_type_name = serializers.CharField(allow_blank=True)
    student_id = serializers.CharField(allow_blank=True, required=False)
    student_name = serializers.CharField(allow_blank=True, required=False)
    points = serializers.IntegerField()
    description = serializers.CharField(allow_blank=True, required=False)


class ClassroomDetailResponseSerializer(serializers.Serializer):
    classroom_id = serializers.CharField()
    classroom_name = serializers.CharField()
    week_number = serializers.IntegerField()
    year = serializers.IntegerField()
    total_positive = serializers.IntegerField()
    total_negative = serializers.IntegerField()
    total_points = serializers.IntegerField()
    events = ClassroomEventDetailSerializer(many=True)


