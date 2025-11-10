from rest_framework import serializers


class GradeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)


class TeacherSerializer(serializers.Serializer):
    id = serializers.CharField()
    username = serializers.CharField(allow_blank=True, required=False)
    first_name = serializers.CharField(allow_blank=True, required=False)
    last_name = serializers.CharField(allow_blank=True, required=False)
    full_name = serializers.CharField(allow_blank=True, required=False)
    email = serializers.EmailField(allow_blank=True, required=False)


class ClassroomSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    grade = GradeSerializer()
    grade_id = serializers.CharField(required=False)
    homeroom_teacher = TeacherSerializer(allow_null=True, required=False)
    homeroom_teacher_id = serializers.CharField(allow_blank=True, required=False)
    full_name = serializers.CharField(allow_blank=True, required=False)
    created_at = serializers.CharField(allow_blank=True, required=False)
    updated_at = serializers.CharField(allow_blank=True, required=False)

    # All validation handled in Mongo views; no ORM checks here


class ClassroomListSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    grade = GradeSerializer()
    homeroom_teacher = TeacherSerializer(allow_null=True, required=False)
    full_name = serializers.CharField(allow_blank=True, required=False)
    student_count = serializers.IntegerField(required=False)
    created_at = serializers.CharField(allow_blank=True, required=False)


class ClassroomCreateRequestSerializer(serializers.Serializer):
    name = serializers.CharField()
    grade_id = serializers.CharField()
    homeroom_teacher_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Validations moved to Mongo views


class ClassroomUpdateRequestSerializer(serializers.Serializer):
    name = serializers.CharField(required=False)
    grade_id = serializers.CharField(required=False)
    homeroom_teacher_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Validations moved to Mongo views