from rest_framework import serializers
from django.contrib.auth.models import User
from user.models import Profile
from dictionary.models import DictionaryItem, StudentWord


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "password", "email", "first_name", "last_name"]
        extra_kwargs = {"password": {"write_only": True}}


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Profile
        fields = [
            "user",
            "name",
            "picture",
            "created_at",
            "updated_at",
            "last_login_at",
        ]

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        # Create user
        user = User.objects.create_user(**user_data)
        # Check if profile already exists (created by post_save signal)
        try:
            profile = Profile.objects.get(user=user)
            # Update existing profile with provided data
            for attr, value in validated_data.items():
                setattr(profile, attr, value)
            profile.save()
        except Profile.DoesNotExist:
            # If no profile exists, create one
            profile = Profile.objects.create(user=user, **validated_data)
        return profile


class DictionaryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictionaryItem
        fields = ["word", "meaning"]


class DictionarySearchResponseSerializer(serializers.Serializer):
    input_word = serializers.CharField(allow_null=True)
    db_word = serializers.CharField()
    meaning = serializers.CharField()
    is_owned_by_student = serializers.BooleanField()


class StudentWordSerializer(serializers.ModelSerializer):
    dictionary_item = DictionaryItemSerializer(read_only=True)
    dictionary_item_id = serializers.PrimaryKeyRelatedField(
        queryset=DictionaryItem.objects.all(), source="dictionary_item", write_only=True
    )

    class Meta:
        model = StudentWord
        fields = [
            "id",
            "student",
            "dictionary_item",
            "dictionary_item_id",
            "word",
            "meaning",
            "start_at",
            "updated_at",
            "successes",
            "is_master",
            "next_1",
            "next_2",
            "revise_at",
            "continue_revision",
        ]
        read_only_fields = ["student", "start_at", "updated_at"]

    def validate(self, data):
        """
        Ensure unique_together constraint for student and word.
        """
        student = self.context["request"].user.profile
        word = data.get("word")
        if (
            not self.instance
            and StudentWord.objects.filter(student=student, word=word).exists()
        ):
            raise serializers.ValidationError(
                "This word is already in the student's library."
            )
        return data
