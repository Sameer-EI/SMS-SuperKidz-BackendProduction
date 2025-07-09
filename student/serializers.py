from rest_framework import serializers

from authentication.models import User
from director.models import Address, City, Country, Role, ClassPeriod, State
# from director.serializers import BankingDetailsSerializer
from .models import GuardianType, Student, StudentGuardian,StudentYearLevel
from director.models import ClassPeriod, YearLevel



from django.db import IntegrityError
from django.core.exceptions import MultipleObjectsReturned

from .models import Guardian
from director.models import BankingDetail


class GuardianTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuardianType
        fields = "__all__"
        




# ***********************new*********************

class StudentSerializer(serializers.ModelSerializer):
    # User fields (write-only)
    first_name = serializers.CharField(max_length=100, write_only=True)
    middle_name = serializers.CharField(max_length=100, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(max_length=100, write_only=True, required=False)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    # Student model fields
    father_name = serializers.CharField(required=False, allow_null=True)
    mother_name = serializers.CharField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, allow_null=True)
    religion = serializers.CharField(required=False, allow_null=True)
    category = serializers.ChoiceField(
        choices=[('SC', 'Scheduled Caste'), ('ST', 'Scheduled Tribe'), ('OBC', 'Other Backward Class'), ('GEN', 'General')],
        default='GEN'
    )
    height = serializers.FloatField(required=False, allow_null=True)
    weight = serializers.FloatField(required=False, allow_null=True)
    blood_group = serializers.CharField(required=False, allow_null=True)
    number_of_siblings = serializers.IntegerField(required=False, allow_null=True)
    roll_number = serializers.CharField(required=False, allow_null=True) 
    contact_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    scholar_number = serializers.CharField(required=False, allow_null=True, allow_blank=True)


    # Classes many-to-many
    classes = serializers.PrimaryKeyRelatedField(queryset=ClassPeriod.objects.all(), many=True,required=False,allow_empty=True,default=[])

    class Meta:
        model = Student
        fields = ['id',
            'first_name', 'middle_name', 'last_name', 'email', 'password', 'user_profile',
            'father_name', 'mother_name', 'date_of_birth', 'gender', 'religion', 'category',
            'height', 'weight', 'blood_group', 'number_of_siblings', 'roll_number','contact_number','scholar_number','classes'
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user = instance.user
        rep.update({
            'first_name': user.first_name,
            'middle_name': user.middle_name,
            'last_name': user.last_name,
            'email': user.email,
            'user_profile': user.user_profile.url if user.user_profile else None,
        })
        return rep

    def create(self, validated_data):
        user_data = {
            'first_name': validated_data.pop('first_name'),
            'middle_name': validated_data.pop('middle_name', ''),
            'last_name': validated_data.pop('last_name'),
            'email': validated_data.pop('email'),
            'password': validated_data.pop('password', None),
            'user_profile': validated_data.pop('user_profile', None),
        }
        classes_data = validated_data.pop('classes',[])
            # ✅ Normalize class IDs to integers
        if isinstance(classes_data, list):
            try:
                classes_data = [int(c) for c in classes_data]
            except (ValueError, TypeError):
                raise serializers.ValidationError({"classes": "Class IDs must be integers."})
        elif isinstance(classes_data, str):
            if classes_data.isdigit():
                classes_data = [int(classes_data)]
            else:
                raise serializers.ValidationError({"classes": "Invalid class ID format."})

        if User.objects.filter(email=user_data['email']).exists():
            raise serializers.ValidationError("User with this email already exists.")

        user = User.objects.create_user(

            email=user_data['email'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            password=user_data['password'],
        )
        user.middle_name = user_data['middle_name']
        if user_data['user_profile']:
            user.user_profile = user_data['user_profile']
        user.save()

        student = Student.objects.create(user=user, **validated_data)
        # student.classes.set(classes_data)
        # ✅ Only call .set() if the list is not empty
        if classes_data:
            student.classes.set(classes_data)

        return student

    def update(self, instance, validated_data):
        user = instance.user

        user_fields = ['first_name', 'middle_name', 'last_name', 'email', 'user_profile']
        for field in user_fields:
            if field in validated_data:
                setattr(user, field, validated_data.pop(field))
        if 'password' in validated_data:
            user.set_password(validated_data.pop('password'))
        user.save()

        if 'classes' in validated_data:
            instance.classes.set(validated_data.pop('classes'))

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance









class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]





class GuardianSerializer(serializers.ModelSerializer):
    # User Info (write_only on input)
    first_name = serializers.CharField(max_length=100, write_only=True)
    middle_name = serializers.CharField(max_length=100, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, write_only=True)
    password = serializers.CharField(max_length=100, write_only=True, required=False)
    email = serializers.EmailField(write_only=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)
    
    # Guardian Fields (include here)
    phone_no = serializers.CharField(required=False, allow_null=True,max_length=50)
    annual_income = serializers.IntegerField(required=False, allow_null=True,)
    means_of_livelihood = serializers.ChoiceField(choices=[('Govt', 'Government'), ('Non-Govt', 'Non-Government')], default='Govt')
    qualification = serializers.CharField(required=False, allow_null=True,max_length=300)
    occupation = serializers.CharField(required=False, allow_null=True,max_length=300)
    designation = serializers.CharField(required=False, allow_null=True,max_length=300)

    class Meta:
        model = Guardian
        exclude = ["user"]

    def create(self, validated_data):
        user_data = {
            "first_name": validated_data.pop("first_name"),
            "middle_name": validated_data.pop("middle_name", ""),
            "last_name": validated_data.pop("last_name"),
            "password": validated_data.pop("password", None),
            "email": validated_data.pop("email"),
            "user_profile": validated_data.pop("user_profile", None),
        }

        phone_no = validated_data.pop('phone_no')
        annual_income = validated_data.pop('annual_income')
        means_of_livelihood = validated_data.pop('means_of_livelihood', 'Govt')
        qualification = validated_data.pop('qualification')
        occupation = validated_data.pop('occupation')
        designation = validated_data.pop('designation')

        if User.objects.filter(email=user_data["email"]).exists():
            raise serializers.ValidationError("User with this email already exists.")

        role, _ = Role.objects.get_or_create(name='guardian')
        user = User.objects.create_user(**user_data)
        user.role.add(role)

        guardian = Guardian.objects.create(
            user=user,
            phone_no=phone_no,
            annual_income=annual_income,
            means_of_livelihood=means_of_livelihood,
            qualification=qualification,
            occupation=occupation,
            designation=designation,
            **validated_data
        )

        return guardian

    def update(self, instance, validated_data):
        user = instance.user

        # Update user fields
        user.first_name = validated_data.get('first_name', user.first_name)
        user.middle_name = validated_data.get('middle_name', user.middle_name)
        user.last_name = validated_data.get('last_name', user.last_name)
        password = validated_data.get('password', None)
        if password:
            user.set_password(password)
        user.email = validated_data.get('email', user.email)
        user_profile = validated_data.get('user_profile', None)
        if user_profile is not None:
            user.user_profile = user_profile
        user.save()

        # Update guardian fields
        instance.phone_no = validated_data.get('phone_no', instance.phone_no)
        instance.annual_income = validated_data.get('annual_income', instance.annual_income)
        instance.means_of_livelihood = validated_data.get('means_of_livelihood', instance.means_of_livelihood)
        instance.qualification = validated_data.get('qualification', instance.qualification)
        instance.occupation = validated_data.get('occupation', instance.occupation)
        instance.designation = validated_data.get('designation', instance.designation)
        instance.save()

        return instance


    def to_representation(self, instance):
        rep = super().to_representation(instance)
        user = instance.user
        rep.update({
            "first_name": user.first_name,
            "middle_name": user.middle_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone_no": instance.phone_no,
            "annual_income": instance.annual_income,
            "means_of_livelihood": instance.means_of_livelihood,
            "qualification": instance.qualification,
            "occupation": instance.occupation,
            "designation": instance.designation,
            "user_profile": user.user_profile.url if user.user_profile else None,
        })
        return rep







## As of 29May25 at 02:30 PM
class StudentYearLevelSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField(read_only=True)
    level_name = serializers.CharField(source='level.level_name', read_only=True)
    year_name = serializers.CharField(source='year.year_name', read_only=True)
    student_id = serializers.IntegerField(source='student.id', read_only=True)  # added as of 24June25 at 04:13 PM
    student_email = serializers.SerializerMethodField(read_only=True)  # Added email as of 26June25 at 02:07 PM

    class Meta:
        model = StudentYearLevel
        fields = ['id', 'student', 'level', 'year','student_id', 'student_name','student_email', 'level_name', 'year_name']
        extra_kwargs = {
            'student': {'write_only': True},
            'level': {'write_only': True},
            'year': {'write_only': True},
        }

    def get_student_name(self, obj):
        first_name = obj.student.user.first_name or ''
        last_name = obj.student.user.last_name or ''
        return f"{first_name} {last_name}".strip()
    
    def get_student_email(self, obj):           #  Added email as of 26June25 at 02:07 PM
        return obj.student.user.email if obj.student and obj.student.user else ''



