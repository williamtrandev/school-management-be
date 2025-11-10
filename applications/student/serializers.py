from rest_framework import serializers

# Mongo student serializers (no ORM models)
class MongoStudentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    student_code = serializers.CharField(max_length=20)
    classroom_id = serializers.CharField()
    classroom_name = serializers.CharField(read_only=True)
    user = serializers.DictField(read_only=True)
    gender = serializers.ChoiceField(choices=[('male', 'Nam'), ('female', 'Nữ')])
    date_of_birth = serializers.DateField()
    address = serializers.CharField(required=False, allow_blank=True)
    parent_phone = serializers.CharField(required=False, allow_blank=True, max_length=15)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

class MongoStudentCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    student_code = serializers.CharField(max_length=20)
    classroom_id = serializers.CharField()
    date_of_birth = serializers.DateField()
    gender = serializers.ChoiceField(choices=[('male', 'Nam'), ('female', 'Nữ')])
    address = serializers.CharField(required=False, allow_blank=True)
    parent_phone = serializers.CharField(required=False, allow_blank=True, max_length=15)

class MongoStudentUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30, required=False)
    last_name = serializers.CharField(max_length=30, required=False)
    email = serializers.EmailField(required=False)
    classroom_id = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=[('male', 'Nam'), ('female', 'Nữ')], required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    parent_phone = serializers.CharField(required=False, allow_blank=True, max_length=15) 