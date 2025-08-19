from rest_framework import serializers
from .models import (
    Course,
    Lesson,
    Activity,
    Profile,
    StudentCourse,
    StudentActivity,
)


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "title"]


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "lessons", "description"]  # Basic course fields


class LessonSerializer(serializers.ModelSerializer):
    activities = ActivitySerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = ["id", "title", "activities"]  # Include nested activities


class CourseWithLessonsSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)  # Nest lessons

    class Meta:
        model = Course
        fields = ["id", "title", "lessons"]  # Include nested lessons


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "username",  # From User model
            "email",  # From User model
            "role",
            "name",
            "picture",
            "created_at",
            "updated_at",
            "last_login_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_email(self, obj):
        """Get email from the related User model"""
        return obj.user.email

    def get_username(self, obj):
        """Get username from the related User model"""
        return obj.user.username


class CourseProgressSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    total_activities = serializers.SerializerMethodField()
    completed_activities = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "image",
            "video",
            "description",
            "teacher_name",
            "progress",
            "total_activities",
            "completed_activities",
            "created_at",
        ]

    def get_progress(self, obj):
        """Get overall course progress percentage"""
        student = self.context["request"].user.profile
        try:
            student_course = StudentCourse.objects.get(student=student, course=obj)
            return student_course.progress
        except StudentCourse.DoesNotExist:
            return 0

    def get_teacher_name(self, obj):
        """Get teacher's name if available"""
        return obj.teacher.name if obj.teacher else None

    def get_total_activities(self, obj):
        """Count all activities in the course"""
        return Activity.objects.filter(lesson__course=obj).count()

    def get_completed_activities(self, obj):
        """Count completed activities for this student"""
        student = self.context["request"].user.profile
        return StudentActivity.objects.filter(
            student=student,
            activity__lesson__course=obj,
            progress=100,  # Assuming 100 means completed
        ).count()
