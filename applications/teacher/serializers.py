from rest_framework import serializers

# Mongo teacher serializers (no ORM models)
class MongoTeacherSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    teacher_code = serializers.CharField(max_length=20)
    subject = serializers.CharField(max_length=50)
    user = serializers.DictField(read_only=True)
    homeroom_class_count = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

class MongoTeacherCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    teacher_code = serializers.CharField(max_length=20)
    subject = serializers.CharField(max_length=50)

class MongoTeacherUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)
    email = serializers.EmailField(required=False)
    teacher_code = serializers.CharField(max_length=20, required=False)
    subject = serializers.CharField(max_length=50, required=False) 