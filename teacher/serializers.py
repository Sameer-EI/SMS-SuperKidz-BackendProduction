from rest_framework import serializers
from . models import SubstituteAssignment, Teacher, TeacherYearLevel , TeacherAttendance ,SubstituteAssignment
from authentication . models import User
from director . models import Role
from django.db import IntegrityError
from django.core.exceptions import MultipleObjectsReturned
from director.models import YearLevel , Subject
from director.serializers import ClassPeriodSerializer , subjectSerializer, YearLevelSerializer
from django.core.validators import RegexValidator







class TeacherSerializer(serializers.ModelSerializer):
    # User-related fields (write_only)
    first_name = serializers.CharField(max_length=250, write_only=True)
    middle_name = serializers.CharField(max_length=250, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=250, write_only=True)
    password = serializers.CharField(max_length=250, write_only=True, required=False)
    email = serializers.EmailField(max_length=250, write_only=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    # Teacher model explicit fields
    # phone_no = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    # gender = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    # adhaar_no = serializers.IntegerField(required=False, allow_null=True)
    # pan_no = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    qualification = serializers.CharField(max_length=250, required=False, allow_blank=True, allow_null=True)
    phone_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?\d{10,15}$',
                message="Enter a valid phone number (10-15 digits, optional + at start).")])
    adhaar_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^\d{12}$',
                message="Enter a valid 12-digit Aadhaar number.")])

    pan_no = serializers.CharField(required=False,allow_blank=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z]{5}[0-9]{4}[A-Z]$',
                message="Enter a valid PAN number (e.g., ABCDE1234F).")])
    gender = serializers.ChoiceField(
        choices=[('Male','Male'),('Female','Female'),('Other','Other')],
        required=False,
        error_messages={"invalid_choice": "Gender must be Male, Female, or Other."}
    )
    class Meta:
        model = Teacher
        fields = [
            'id', 'first_name', 'middle_name', 'last_name', 'password', 'email',
            'phone_no', 'gender', 'adhaar_no', 'pan_no', 'qualification', 'user_profile','joining_date','is_active'
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


from rest_framework import serializers
from .models import TeacherYearLevel

class TeacherYearLevelSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    year_level_name = serializers.CharField(source='year_level.level_name', read_only=True)

    class Meta:
        model = TeacherYearLevel
        fields = "__all__"
       
    def get_teacher_name(self, obj):
        if obj.teacher and obj.teacher.user:
            return obj.teacher.user.get_full_name() or f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}".strip()
        return ""

    def validate(self, data):
        teacher = data.get('teacher')  
        year_level = data.get('year_level')
        instance = self.instance  # None if create, else update

        # 🔹 Check if this teacher already has any year_level assigned
        qs = TeacherYearLevel.objects.filter(teacher=teacher)
        if instance:
            qs = qs.exclude(pk=instance.pk)  # exclude current record if updating

        if qs.exists():
            assigned_year_level = qs.first().year_level
            teacher_name = f"{teacher.user.get_full_name()}" if teacher and hasattr(teacher, 'user') else str(teacher)
            raise serializers.ValidationError({
                'teacher': f"Teacher {teacher_name} is already assigned to '{assigned_year_level}'. Cannot assign another class."
            })

        return data



from django.utils import timezone

class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    absent_teacher_name = serializers.SerializerMethodField()
    substitute_teacher_name = serializers.SerializerMethodField()
    
    class Meta:
        model = SubstituteAssignment
        fields = [
            'id', 'period', 'date', 'absent_teacher', 'substitute_teacher',
            'year_level', 'absent_teacher_name', 'substitute_teacher_name'
        ]
        extra_kwargs = {
            "date": {"required": False}  # <- date ko optional banaya
        }

    def get_absent_teacher_name(self, obj):
        return f"{obj.absent_teacher.user.first_name} {obj.absent_teacher.user.last_name}"
    
    def get_substitute_teacher_name(self, obj):
        return f"{obj.substitute_teacher.user.first_name} {obj.substitute_teacher.user.last_name}"

    def validate(self, attrs):
        absent_teacher = attrs.get("absent_teacher")
        substitute_teacher = attrs.get("substitute_teacher")
        period = attrs.get("period")
        year_level = attrs.get("year_level")
        date = attrs.get("date")

        # ✅ agar date missing ho to today set karo
        if not date:
            date = timezone.now().date()
            attrs["date"] = date  

        instance_id = self.instance.id if self.instance else None

        duplicate_qs = SubstituteAssignment.objects.filter(
            absent_teacher=absent_teacher,
            period=period,
            date=date,
            year_level=year_level
        )
        if instance_id:
            duplicate_qs = duplicate_qs.exclude(id=instance_id)

        if duplicate_qs.exists():
            raise serializers.ValidationError(
                {"errors": [
                    f"❌ Duplicate not allowed: "
                    f"Absent Teacher '{absent_teacher.user.first_name} {absent_teacher.user.last_name}' "
                    f"already assigned on {period} ({date}) for Year {year_level} "
                    f"with Substitute '{duplicate_qs.first().substitute_teacher.user.first_name} {duplicate_qs.first().substitute_teacher.user.last_name}'"
                ]}
            )

        return attrs


# [
    # {
    #     "absent_teacher": 1,
    #     "substitute_teacher": 6,
    #     "year_level": 15,
    #     "period": "Period 1",
    #     "date": "2025-08-18"
    # },
#     {
#         "absent_teacher": 1,
#         "substitute_teacher": 7,
#         "year_level": 15,
#         "period": "Period 2",
#         "date": "2025-08-18"
#     },
    # {
    #     "absent_teacher": 2,
    #     "substitute_teacher": 8,
    #     "year_level": 15,
    #     "period": "Period 1",
    #     "date": "2025-08-18"
    # }
# ]


class TeacherAttendanceSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = TeacherAttendance
        fields = ["id", "date", "status", "teacher", "teacher_name"]

    def get_teacher_name(self, obj):
        return f"{obj.teacher.user.first_name} {obj.teacher.user.last_name}"