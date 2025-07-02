from rest_framework import serializers
from . models import Teacher, TeacherYearLevel
from authentication . models import User
from director . models import Role
from django.db import IntegrityError
from django.core.exceptions import MultipleObjectsReturned
from director.models import YearLevel







class TeacherSerializer(serializers.ModelSerializer):
    # User-related fields (write_only)
    first_name = serializers.CharField(max_length=250, write_only=True)
    middle_name = serializers.CharField(max_length=250, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=250, write_only=True)
    password = serializers.CharField(max_length=250, write_only=True, required=False)
    email = serializers.EmailField(max_length=250, write_only=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    # Teacher model explicit fields
    phone_no = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    gender = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    adhaar_no = serializers.IntegerField(required=False, allow_null=True)
    pan_no = serializers.IntegerField(required=False, allow_null=True)
    qualification = serializers.CharField(max_length=250, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Teacher
        fields = [
            'id', 'first_name', 'middle_name', 'last_name', 'password', 'email',
            'phone_no', 'gender', 'adhaar_no', 'pan_no', 'qualification', 'user_profile'
        ]

    def create(self, validated_data):
        user_data = {
            'first_name': validated_data.pop('first_name', ''),
            'middle_name': validated_data.pop('middle_name', ''),
            'last_name': validated_data.pop('last_name', ''),
            'password': validated_data.pop('password', ''),
            'email': validated_data.pop('email', ''),
            'user_profile': validated_data.pop('user_profile', None),
        }

        try:
            role, _ = Role.objects.get_or_create(name='teacher')
        except MultipleObjectsReturned:
            raise serializers.ValidationError("Multiple 'teacher' roles found.")

        existing_user = User.objects.filter(email=user_data['email']).first()

        if existing_user:
            if not existing_user.role.filter(name='teacher').exists():
                existing_user.role.add(role)
                existing_user.save()
            else:
                raise serializers.ValidationError("User email already exists with this role.")
            user = existing_user
        else:
            user = User.objects.create_user(**user_data)
            user.role.add(role)
            user.save()

        teacher = Teacher.objects.create(user=user, **validated_data)
        return teacher

    def update(self, instance, validated_data):
        user = instance.user

        # Update user fields
        user.first_name = validated_data.get("first_name", user.first_name)
        user.middle_name = validated_data.get("middle_name", user.middle_name or "")
        user.last_name = validated_data.get("last_name", user.last_name)
        user.email = validated_data.get("email", user.email)

        if "user_profile" in validated_data:
            user.user_profile = validated_data.get("user_profile")

        if "password" in validated_data:
            user.set_password(validated_data["password"])

        try:
            user.save()
        except IntegrityError:
            raise serializers.ValidationError("Email already exists.")

        # Update teacher fields
        instance.phone_no = validated_data.get("phone_no", instance.phone_no)
        instance.gender = validated_data.get("gender", instance.gender)
        instance.adhaar_no = validated_data.get("adhaar_no", instance.adhaar_no)
        instance.pan_no = validated_data.get("pan_no", instance.pan_no)
        instance.qualification = validated_data.get("qualification", instance.qualification)
        instance.save()

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update({
            'first_name': instance.user.first_name,
            'middle_name': instance.user.middle_name,
            'last_name': instance.user.last_name,
            'email': instance.user.email,
            'user_profile': instance.user.user_profile.url if instance.user.user_profile else None,
            'phone_no': instance.phone_no,
            'gender': instance.gender,
            'adhaar_no': instance.adhaar_no,
            'pan_no': instance.pan_no,
            'qualification': instance.qualification,
        })
        return representation


# ******************TeacherYearLevelSerializer***********************************
class TeacherYearLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model =TeacherYearLevel
        fields ="__all__"
        