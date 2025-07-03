from datetime import date
import re
from rest_framework import serializers
from .models import *
from django.core.exceptions import MultipleObjectsReturned
from django.db import IntegrityError
from student.serializers import *
# from authentication.serializers import UserSerializer
from uuid import uuid4
from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
from django.db.models import Max


from django.utils import timezone
from decimal import Decimal
from collections import defaultdict
from django.db.models import Max



class YearLevelSerializer(serializers.ModelSerializer):   # coomented as of 05June25 at 01:36 AM
    class Meta:
        model = YearLevel
        fields = "__all__"

class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = "__all__"


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class ClassRoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassRoomType
        fields = "__all__"
        
        
class ClassPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassPeriod
        fields = "__all__"        


class BankingDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankingDetail
        fields = ["id", "account_no", "ifsc_code", "holder_name"]
        extra_kwargs = {
            "user": {"read_only": True}
        }

    
    def create(self, validated_data):
        user = self.context.get("user")
        if not user:
            raise serializers.ValidationError("User is required to create banking detail.")
        return BankingDetail.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        account_no = validated_data.get("account_no")
        if account_no and account_no != instance.account_no:
            if BankingDetail.objects.filter(account_no=account_no).exclude(id=instance.id).exists():
                raise serializers.ValidationError({
                    "account_no": "This account number is already in use by another user."
                })
        instance.account_no = validated_data.get("account_no", instance.account_no)
        instance.ifsc_code = validated_data.get("ifsc_code", instance.ifsc_code)
        instance.holder_name = validated_data.get("holder_name", instance.holder_name)
        instance.save()
        return instance


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "name"]

    def create_or_get_role(self, role_name):
        existing_role = Role.objects.filter(name=role_name).first()
        if existing_role:
            return existing_role
        else:
            new_role = Role.objects.create(name=role_name)
            return new_role


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = "__all__"
        
        


class subjectSerializer(serializers.ModelSerializer):
    department = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'department'] 

    def get_department(self, obj):
        return obj.department.department_name if obj.department else None



class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = "__all__"


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = "__all__"




class AddressSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(),write_only=True)
    state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(),write_only=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(),write_only=True)

    country_name = serializers.CharField(source='country.name', read_only=True)
    state_name = serializers.CharField(source='state.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = Address
        fields = [
            'id', 'user', 'house_no', 'habitation', 'ward_no', 'zone_no', 'block', 'district', 'division', 'area_code',
            'country', 'state', 'city', 'address_line',
            'country_name', 'state_name', 'city_name'
        ]
        extra_kwargs = {
            'user': {'read_only': True}
        }

    def validate(self, data):
        # user = data.get('user')  # No need to get user here, it's read-only
        house_no = data.get('house_no')
        area_code = data.get('area_code')
        country = data.get('country')
        state = data.get('state')
        city = data.get('city')
        address_line = data.get('address_line')

        # Access the user from the serializer context
        user = self.context.get('user')

        if Address.objects.filter(
            user=user,
            house_no=house_no,
            area_code=area_code,
            country=country,
            state=state,
            city=city,
            address_line=address_line
        ).exists():
            raise serializers.ValidationError("Address already exists for the user.")

        return data

    def create(self, validated_data):
            user = self.context['request'].user  # assuming request is passed in context
            return Address.objects.create(user=user, **validated_data)



class SchoolYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolYear
        fields = "__all__"


class PeriodSerializer(serializers.ModelSerializer):
    year = serializers.PrimaryKeyRelatedField(queryset=SchoolYear.objects.all())

    class Meta:
        model = Period
        fields = ["id","year", "name", "start_period_time", "end_period_time"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        try:
            representation["year"] = instance.year.year_name
        except AttributeError:
            representation["year"] = None
        return representation


class TermSerializer(serializers.ModelSerializer):
    year = serializers.PrimaryKeyRelatedField(queryset=SchoolYear.objects.all())

    class Meta:
        model = Term
        fields = ["id", "year", "term_number", "start_date", "end_date"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["year"] = instance.year.year_name
        return representation


class DirectorProfileSerializer(serializers.ModelSerializer):
    # User fields
    first_name = serializers.CharField(max_length=100, write_only=True)
    middle_name = serializers.CharField(max_length=100, write_only=True, allow_blank=True, required=False)
    last_name = serializers.CharField(max_length=100, write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_null=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    # Director fields
    phone_no = serializers.CharField(max_length=250, required=False, allow_blank=True)
    gender = serializers.CharField(max_length=50, required=False, allow_blank=True)

    class Meta:
        model = Director
        exclude = ["user"]

    def create(self, validated_data):
        # Extract user-related data
        user_data = {
            "first_name": validated_data.pop("first_name"),
            "middle_name": validated_data.pop("middle_name", ""),
            "last_name": validated_data.pop("last_name"),
            "email": validated_data.pop("email"),
            "password": validated_data.pop("password", ""),
            "user_profile": validated_data.pop("user_profile", None),
        }

        phone_no = validated_data.pop("phone_no", None)
        gender = validated_data.pop("gender", None)

        # Assign role
        try:
            role, _ = Role.objects.get_or_create(name="director")
        except MultipleObjectsReturned:
            raise serializers.ValidationError("Multiple 'director' roles exist. Please fix your roles table.")

        # Get or create user
        user = User.objects.filter(email=user_data["email"]).first()
        if user:
            if not user.role.filter(name="director").exists():
                user.role.add(role)
        else:
            user = User.objects.create_user(**user_data)
            user.role.add(role)
            user.save()

        try:
            director_profile = Director.objects.create(
                user=user,
                phone_no=phone_no,
                gender=gender,
                **validated_data
            )
        except IntegrityError:
            raise serializers.ValidationError("User with this email already exists.")

        return director_profile

    def update(self, instance, validated_data):
        user = instance.user

        # Update user info
        user.first_name = validated_data.get("first_name", user.first_name)
        user.middle_name = validated_data.get("middle_name", user.middle_name)
        user.last_name = validated_data.get("last_name", user.last_name)
        user.email = validated_data.get("email", user.email)

        if "password" in validated_data and validated_data["password"]:
            user.set_password(validated_data["password"])

        if "user_profile" in validated_data:
            user.user_profile = validated_data.get("user_profile")

        # Update director fields
        instance.phone_no = validated_data.get("phone_no", instance.phone_no)
        instance.gender = validated_data.get("gender", instance.gender)

        try:
            user.save()
            instance.save()
        except IntegrityError:
            raise serializers.ValidationError("Failed to update. Email may already exist.")

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update({
            "first_name": instance.user.first_name,
            "middle_name": instance.user.middle_name,
            "last_name": instance.user.last_name,
            "email": instance.user.email,
            "user_profile": instance.user.user_profile.url if instance.user.user_profile else None,
            "phone_no": instance.phone_no,
            "gender": instance.gender,
        })
        return representation







# ***************chnag varilable name *****************************
class AdmissionSerializer(serializers.ModelSerializer):
    # Use SerializerMethodField to output nested student and guardian data
    student_input = serializers.SerializerMethodField(read_only=True)
    guardian_input = serializers.SerializerMethodField(read_only=True)
    
    address = serializers.SerializerMethodField(read_only=True)
    banking_detail = serializers.SerializerMethodField(read_only=True)

    guardian_type = serializers.SerializerMethodField(read_only=True)
    guardian_type_input = serializers.SlugRelatedField(
        slug_field='name',
        queryset=GuardianType.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    year_level = serializers.SlugRelatedField(
        slug_field='level_name',
        queryset=YearLevel.objects.all(),
        required=False,
        allow_null=True,
    )
    
    school_year = serializers.SlugRelatedField(
        slug_field='year_name',
        queryset=SchoolYear.objects.all(),
        required=False,
        allow_null=True,
    )

    # These are write-only inputs for creating/updating admission
    student = StudentSerializer(write_only=True, required=True)
    guardian = GuardianSerializer(write_only=True, required=True)
    address_input = AddressSerializer(write_only=True, required=False, allow_null=True)
    banking_detail_input = BankingDetailsSerializer(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Admission
        fields = [
            'id',
            'student_input', 'guardian_input',  # output nested data
            'address', 'banking_detail',
            'student', 'guardian',  # write-only input nested data
            'address_input', 'banking_detail_input',
            'guardian_type', 'guardian_type_input',
            'year_level', 'school_year',
            'admission_date', 'previous_school_name', 'previous_standard_studied',
            'tc_letter', 'emergency_contact_no', 'entire_road_distance_from_home_to_school',
            'obtain_marks', 'total_marks', 'previous_percentage',
        ]
        read_only_fields = [
            'admission_date',
            'student_input',
            'guardian_input',
            'guardian_type',
            'address',
            'banking_detail'
        ]

    def get_student_input(self, obj):
        if obj.student:
            return StudentSerializer(obj.student).data
        return None

    def get_guardian_input(self, obj):
        if obj.guardian:
            return GuardianSerializer(obj.guardian).data
        return None

    def get_address(self, obj):
        address = Address.objects.filter(user=obj.student.user).first()
        return AddressSerializer(address).data if address else None

    def get_banking_detail(self, obj):
        banking = BankingDetail.objects.filter(user=obj.student.user).first()
        return BankingDetailsSerializer(banking).data if banking else None

    def get_guardian_type(self, obj):
        try:
            sg = StudentGuardian.objects.get(student=obj.student, guardian=obj.guardian)
            return sg.guardian_type.name
        except StudentGuardian.DoesNotExist:
            return None

    def create(self, validated_data):
        student_data = validated_data.pop('student')
        guardian_data = validated_data.pop('guardian')
        address_data = validated_data.pop('address_input', None)
        banking_data = validated_data.pop('banking_detail_input', None)
        guardian_type = validated_data.pop('guardian_type_input', None)
        year_level = validated_data.pop('year_level', None)
        school_year = validated_data.pop('school_year', None)

        # --- Student processing ---
        classes_data = student_data.pop('classes', [])
        if isinstance(classes_data, str):
            try:
                classes_data = [int(classes_data)]
            except ValueError:
                raise serializers.ValidationError({"student.classes": "Invalid class ID format."})

        user_data = {
            'first_name': student_data.pop('first_name', ''),
            'middle_name': student_data.pop('middle_name', ''),
            'last_name': student_data.pop('last_name', ''),
            'email': student_data.pop('email'),
            'password': student_data.pop('password', None),
            'user_profile': student_data.pop('user_profile', None),
        }

        user = User.objects.filter(email__iexact=user_data['email']).first()
        if not user:
            role, _ = Role.objects.get_or_create(name='student')
            user = User.objects.create_user(**user_data)
            user.role.add(role)

        student, created = Student.objects.get_or_create(user=user, defaults=student_data)
        if not created:
            raise serializers.ValidationError({"student": "Student already exists for this user."})

        if classes_data:
            student.classes.set(classes_data)

        # --- Address and banking ---
        if address_data:
            Address.objects.update_or_create(user=user, defaults=address_data)
        if banking_data:
            BankingDetail.objects.update_or_create(user=user, defaults=banking_data)

        # --- Guardian user creation ---
        guardian_user_data = {
            'first_name': guardian_data.pop('first_name', ''),
            'middle_name': guardian_data.pop('middle_name', ''),
            'last_name': guardian_data.pop('last_name', ''),
            'email': guardian_data.pop('email'),
            'password': guardian_data.pop('password', None),
            'user_profile': guardian_data.pop('user_profile', None),
        }

        guardian_user = User.objects.filter(email__iexact=guardian_user_data['email']).first()
        if not guardian_user:
            role, _ = Role.objects.get_or_create(name='guardian')
            guardian_user = User.objects.create_user(**guardian_user_data)
            guardian_user.role.add(role)
        else:
            for attr, value in guardian_user_data.items():
                if value:
                    setattr(guardian_user, attr, value)
            guardian_user.save()

        # --- Guardian model creation or update ---
        guardian, _ = Guardian.objects.get_or_create(user=guardian_user, defaults=guardian_data)
        if guardian_data:
            guardian_serializer = GuardianSerializer(guardian, data=guardian_data, partial=True)
            guardian_serializer.is_valid(raise_exception=True)
            guardian_serializer.save()

        # --- Admission creation ---
        admission = Admission.objects.create(
            student=student,
            guardian=guardian,
            previous_school_name=validated_data.get('previous_school_name'),
            previous_standard_studied=validated_data.get('previous_standard_studied'),
            tc_letter=validated_data.get('tc_letter'),
            year_level=year_level,
            school_year=school_year,
            emergency_contact_no=validated_data.get('emergency_contact_no'),
            entire_road_distance_from_home_to_school=validated_data.get('entire_road_distance_from_home_to_school'),
            obtain_marks=validated_data.get('obtain_marks'),
            total_marks=validated_data.get('total_marks'),
            previous_percentage=validated_data.get('previous_percentage'),
        )

        if guardian_type:
            StudentGuardian.objects.update_or_create(
                student=student, guardian=guardian, defaults={'guardian_type': guardian_type}
            )

        if year_level and school_year:
            StudentYearLevel.objects.update_or_create(
                student=student, level=year_level, year=school_year
            )

        return admission


    def update(self, instance, validated_data):
        student_data = validated_data.pop('student', None)
        guardian_data = validated_data.pop('guardian', None)
        address_data = validated_data.pop('address_input', None)
        banking_data = validated_data.pop('banking_detail_input', None)
        guardian_type = validated_data.pop('guardian_type_input', None)
        year_level = validated_data.pop('year_level', None)
        school_year = validated_data.pop('school_year', None)

        user = self.context.get("user") or instance.student.user

        if student_data:
            student_serializer = StudentSerializer(instance.student, data=student_data, partial=True)
            student_serializer.is_valid(raise_exception=True)
            student_serializer.save()

            classes_data = student_data.get('classes')
            if isinstance(classes_data, str):
                try:
                    classes_data = [int(classes_data)]
                except ValueError:
                    raise serializers.ValidationError({"student.classes": "Invalid class ID format."})

            if classes_data:
                instance.student.classes.set(classes_data)

        if guardian_data:
            guardian_serializer = GuardianSerializer(instance.guardian, data=guardian_data, partial=True)
            guardian_serializer.is_valid(raise_exception=True)
            guardian_serializer.save()

        if address_data:
            for key in ['city', 'state', 'country']:
                val = address_data.get(key)
                if hasattr(val, 'id'):
                    address_data[key] = val.id

            try:
                address_instance = Address.objects.get(user=user)
                address_serializer = AddressSerializer(address_instance, data=address_data, partial=True)
            except Address.DoesNotExist:
                address_serializer = AddressSerializer(data=address_data)

            address_serializer.is_valid(raise_exception=True)
            address_serializer.save(user=user)

        if banking_data:
            current_account_no = str(banking_data.get('account_no'))

            try:
                banking_instance = BankingDetail.objects.get(user=user)
                existing_account_no = str(banking_instance.account_no)

                if existing_account_no == current_account_no:
                    banking_data.pop('account_no', None)
                else:
                    if BankingDetail.objects.filter(account_no=current_account_no).exclude(user_id=user.id).exists():
                        raise serializers.ValidationError({
                            "banking_detail_input": {
                                "account_no": ["This account number is already in use by another user."]
                            }
                        })

                banking_serializer = BankingDetailsSerializer(banking_instance, data=banking_data, partial=True)
                banking_serializer.is_valid(raise_exception=True)
                banking_serializer.save(user=user)

            except BankingDetail.DoesNotExist:
                if BankingDetail.objects.filter(account_no=current_account_no).exists():
                    raise serializers.ValidationError({
                        "banking_detail_input": {
                            "account_no": ["This account number is already in use."]
                        }
                    })

                banking_serializer = BankingDetailsSerializer(data=banking_data)
                banking_serializer.is_valid(raise_exception=True)
                banking_serializer.save(user=user)

        if guardian_type:
            StudentGuardian.objects.update_or_create(
                student=instance.student,
                guardian=instance.guardian,
                defaults={"guardian_type": guardian_type}
            )

        if year_level:
            instance.year_level = year_level
        if school_year:
            instance.school_year = school_year

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance












# **********Assignment ClassPeriod for Student behalf of YearLevel(Standard)********************

# As of 05May25 at 01:00 PM


class ClassPeriodSerializer(serializers.ModelSerializer):
    # Extra fields for the custom POST action
    year_level_name = serializers.CharField(write_only=True, required=False)
    class_period_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = ClassPeriod
        fields = [
            'id', 'subject', 'teacher', 'term',
            'start_time', 'end_time', 'classroom', 'name',
            'year_level_name', 'class_period_names'  
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['start_time'] = instance.start_time.start_period_time.strftime('%I:%M %p')
        representation['end_time'] = instance.end_time.end_period_time.strftime('%I:%M %p')
        return representation

    def create(self, validated_data):
        # Handle assignment logic only if year_level_name and class_period_names are present
        year_level_name = validated_data.pop('year_level_name', None)
        class_period_names = validated_data.pop('class_period_names', None)

        if year_level_name and class_period_names:
            try:
                year_level = YearLevel.objects.get(level_name=year_level_name)
            except YearLevel.DoesNotExist:
                raise serializers.ValidationError("Invalid YearLevel name.")

            class_periods = ClassPeriod.objects.filter(name__in=class_period_names)
            if class_periods.count() != len(class_period_names):
                raise serializers.ValidationError("Some ClassPeriod names are invalid.")

            student_ids = StudentYearLevel.objects.filter(level=year_level).values_list("student_id", flat=True)
            students = Student.objects.filter(id__in=student_ids)

            for student in students:
                student.classes.add(*class_periods)

            return {
                "students_updated": students.count(),
                "class_periods_assigned": [cp.name for cp in class_periods]
            }

        # If not an assignment request, create a regular ClassPeriod (fallback)
        return super().create(validated_data)




# Added as of 06June25 at 02:50 PM

class FeeTypeSerializer(serializers.ModelSerializer):
    # name = serializers.SerializerMethodField()
    
    class Meta:
        model = FeeType
        fields = ['id', 'name']


class YearLevelFeeSerializer(serializers.ModelSerializer):
    year_level_name = serializers.SerializerMethodField()
    fee_type_name = serializers.SerializerMethodField()
    year_level_id = serializers.IntegerField(source='year_level.id', read_only=True)

    class Meta:
        model = YearLevelFee
        fields = ['id', 'year_level', 'fee_type', 'year_level_name', 'fee_type_name', 'amount', 'year_level_id']

    def get_year_level_name(self, obj):
        return obj.year_level.level_name

    def get_fee_type_name(self, obj):
        return obj.fee_type.name

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('year_level', None)
        data.pop('fee_type', None)
        return data
 
    # Added this as of 11June25 at 11:39 AM
    @staticmethod
    def group_by_year_level(fees):
        grouped_fees = {}
        for fee in fees:
            year_level_name = fee['year_level_name']
            year_level_id = fee['year_level_id']
            fee_data = {
                'id': fee['id'],
                'fee_type': fee['fee_type_name'],
                'amount': fee['amount']
            }

            # Use a tuple key to keep both id and name
            key = (year_level_id, year_level_name)

            if key not in grouped_fees:
                grouped_fees[key] = {
                    'id': year_level_id,
                    'year_level': year_level_name,
                    'fees': []
                }

            grouped_fees[key]['fees'].append(fee_data)

        return list(grouped_fees.values())



### just added to submit fee for multiple months as of 09Jun25 at 06:53 PM
class FeeRecordSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), source='student', write_only=True)
    year_level_fees = serializers.PrimaryKeyRelatedField(queryset=YearLevelFee.objects.all(), many=True, write_only=True)
    year_level_fees_grouped = serializers.SerializerMethodField(read_only=True)

    total_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    paid_amount = serializers.DecimalField(max_digits=8, decimal_places=2)
    due_amount = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    late_fee = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    payment_date = serializers.DateField(read_only=True)
    receipt_number = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(max_length=20, read_only=True)
    remarks = serializers.CharField(max_length=255, required=False, allow_null=True)
    received_by = serializers.CharField(max_length=100,required=False, allow_null=True)
    
    payment_mode = serializers.ChoiceField(choices=FeeRecord._meta.get_field('payment_mode').choices)

    month = serializers.ChoiceField(choices=FeeRecord.MONTH_CHOICES)

    class Meta:
        model = FeeRecord
        fields = [
            'id', 'student', 'student_id', 'month', 'year_level_fees', 'year_level_fees_grouped',
            'total_amount', 'paid_amount', 'due_amount', 'payment_date', 'payment_mode', 'is_cheque_cleared','receipt_number',
            'late_fee', 'payment_status', 'remarks', 'received_by'
        ]
        read_only_fields = ['receipt_number', 'payment_date', 'total_amount', 'due_amount', 'late_fee']

    def get_student(self, obj):
        return {
            "id": obj.student.id,
            "name": f"{obj.student.user.first_name} {obj.student.user.last_name}"
        }

    def get_year_level_fees_grouped(self, obj):
        grouped = defaultdict(list)
        for fee in obj.year_level_fees.all():
            year_level_name = fee.year_level.level_name
            grouped[year_level_name].append({
                "id": fee.id,
                "fee_type": fee.fee_type.name,
                "amount": str(fee.amount),
            })
        return [{"year_level": yl, "fees": fees} for yl, fees in grouped.items()]
    
    
    def validate(self, data):
        student = data.get('student')
        month = data.get('month')
        year_level_fees = data.get('year_level_fees', [])
        paid_amount = data.get('paid_amount', 0)

        # Prevent duplicate fee entry for same student + month
        if self.instance is None:  # Only during creation
            if FeeRecord.objects.filter(student=student, month=month).exists():
                raise serializers.ValidationError(f"Fee already submitted for {month} for this student.")

        # Validate fees
        if not year_level_fees:
            raise serializers.ValidationError("At least one year level fee must be selected.")

        # Calculate total amount
        total = 0
        for fee in year_level_fees:
            total += fee.amount
        data['total_amount'] = total

        # Apply late fee only for current or past months
        today = date.today()
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }

        fee_month_num = month_map.get(month)

        if fee_month_num is not None and (fee_month_num <= today.month):
            # If the fee is for current/past month and today is after the 15th
            data['late_fee'] = 25 if today.day > 15 else 0
        else:
            data['late_fee'] = 0

        # Calculate due amount
        due = total + data['late_fee'] - paid_amount
        data['due_amount'] = due if due > 0 else 0
        
        # Set payment status based on due amount
        data['payment_status'] = 'Paid' if data['due_amount'] == 0 else 'Unpaid'

        return data

    
    ### Added this as of 11June25 at 01:39 PM
    def create(self, validated_data):
        year_level_fees = validated_data.pop('year_level_fees')
        validated_data['payment_date'] = date.today()

        total_amount = validated_data.get('total_amount', 0)
        paid_amount = validated_data.get('paid_amount', 0)
        late_fee = validated_data.get('late_fee', 0)
        due_amount = validated_data.get('due_amount', 0)
        payment_mode = validated_data.get('payment_mode')
        is_cheque_cleared = validated_data.get('is_cheque_cleared', False)

        # Default status
        payment_status = 'Unpaid'
        
        if payment_mode == 'Cash' or payment_mode == 'Online':
            if paid_amount >= total_amount + validated_data.get('late_fee', 0):
                payment_status = 'Paid'
        elif payment_mode == 'Cheque':
            if is_cheque_cleared and paid_amount >= total_amount + late_fee:
                payment_status = 'Paid'
            else:
                payment_status = 'Unpaid'
        
        validated_data['payment_status'] = payment_status

        fee_record = FeeRecord.objects.create(**validated_data)
        fee_record.year_level_fees.set(year_level_fees)
        return fee_record


### Razorpay Functionality Added as of 10Jun25

### Added as of 12june25 at 02:20 PM
class FeeRecordRazorpaySerializer(serializers.ModelSerializer):
    student_id = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), source='student', write_only=True)
    year_level_fees = serializers.PrimaryKeyRelatedField(queryset=YearLevelFee.objects.all(), many=True)
    receipt_number = serializers.CharField(read_only=True)

    class Meta:
        model = FeeRecord
        fields = [
            'id', 'student_id', 'month', 'year_level_fees', 'total_amount', 'paid_amount', 'due_amount',
            'late_fee', 'payment_mode', 'payment_status', 'remarks', 'received_by',
            'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature_id', 'receipt_number'
        ]
        read_only_fields = ['total_amount', 'due_amount', 'late_fee', 'payment_status',
                            'razorpay_payment_id', 'razorpay_signature_id', 'receipt_number']

    
    # just added as of 16June25 at 12:29 PM
            # just added as of 16June25 at 12:29 PM

    
    def validate(self, data):       # corrected late fee logic for advanced fee payment
        student = data.get('student')
        month = data.get('month')
        year_level_fees = data.get('year_level_fees', [])
        paid_amount = data.get('paid_amount', Decimal("0.00"))

        if not year_level_fees:
            raise serializers.ValidationError("At least one year level fee must be selected.")

        if FeeRecord.objects.filter(student=student, month=month).exists():
            raise serializers.ValidationError(f"Fee already submitted for {month} month for this student.")

        # Calculate total fees
        total = sum(fee.amount for fee in year_level_fees)

        # Calculate late fee based on current or past month logic (same as cash serializer)
        month_map = {
            'January': 1, 'February': 2, 'March': 3, 'April': 4,
            'May': 5, 'June': 6, 'July': 7, 'August': 8,
            'September': 9, 'October': 10, 'November': 11, 'December': 12
        }
        today = date.today()
        fee_month_num = month_map.get(month)

        if fee_month_num is not None and fee_month_num <= today.month:
            late_fee = Decimal("25.00") if today.day > 15 else Decimal("0.00")
        else:
            late_fee = Decimal("0.00")

        due_amount = total + late_fee - paid_amount

        data['total_amount'] = total
        data['late_fee'] = late_fee
        data['due_amount'] = due_amount if due_amount > 0 else Decimal("0.00")

        # Set payment status based on due amount
        data['payment_status'] = 'Paid' if data['due_amount'] == 0 else 'Unpaid'

        # Extract Razorpay fields explicitly from input data
        data['razorpay_order_id'] = self.initial_data.get('razorpay_order_id')
        data['razorpay_payment_id'] = self.initial_data.get('razorpay_payment_id')
        data['razorpay_signature_id'] = self.initial_data.get('razorpay_signature_id')

        return data
    
        

    # just commented as of 13June25 at 04:23 PM as it is not saving Razorpay payment id,Razorpay signature id: in the FeeRecord DB
    
    def create(self, validated_data):      # just uncomment it as of 16June25 at 12:29 PM   
        year_level_fees = validated_data.pop('year_level_fees')
        validated_data['payment_date'] = date.today()

        total_amount = validated_data.get('total_amount', Decimal("0.00"))
        paid_amount = validated_data.get('paid_amount', Decimal("0.00"))
        late_fee = validated_data.get('late_fee', Decimal("0.00"))

        payment_status = 'Paid' if paid_amount >= (total_amount + late_fee) else 'Unpaid'
        validated_data['payment_status'] = payment_status

        fee_record = FeeRecord.objects.create(**validated_data)
        fee_record.year_level_fees.set(year_level_fees)
        return fee_record
    
    
    


    
   
    ### Added this as of 13June25 at 11:53 AM 
class RazorpayConfirmPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature_id = serializers.CharField()







# ********************OfficeStaffSerializer profile*******************************
class OfficeStaffSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(max_length=100, write_only=True)
    middle_name = serializers.CharField(max_length=100, write_only=True, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=100, write_only=True)
    password = serializers.CharField(max_length=100, write_only=True, required=False)
    email = serializers.EmailField(write_only=True)
    user_profile = serializers.ImageField(required=False, allow_null=True, write_only=True)

    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), many=True, required=False)
    teacher = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.all(), many=True, required=False)
    admissions = serializers.PrimaryKeyRelatedField(queryset=Admission.objects.all(), many=True, required=False)

    class Meta:
        model = OfficeStaff
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

        student_data = validated_data.pop("student", [])
        teacher_data = validated_data.pop("teacher", [])
        admissions_data = validated_data.pop("admissions", [])

        try:
            role, _ = Role.objects.get_or_create(name="office_staff")
        except MultipleObjectsReturned:
            raise serializers.ValidationError("Multiple roles named 'office_staff' found.")

        user = User.objects.filter(email=user_data["email"]).first()

        if user:
            if not user.role.filter(name="office_staff").exists():
                user.role.add(role)
                user.save()
            else:
                raise serializers.ValidationError("User with this email already exists and is an office staff.")
        else:
            user = User.objects.create_user(**user_data)
            user.role.add(role)
            user.save()

        office_staff = OfficeStaff.objects.create(user=user, **validated_data)
        office_staff.student.set(student_data)
        office_staff.teacher.set(teacher_data)
        office_staff.admissions.set(admissions_data)
        return office_staff

    def update(self, instance, validated_data):
        user = instance.user

        user.first_name = validated_data.pop("first_name", user.first_name)
        user.middle_name = validated_data.pop("middle_name", user.middle_name)
        user.last_name = validated_data.pop("last_name", user.last_name)
        user.email = validated_data.pop("email", user.email)
        if "password" in validated_data and validated_data["password"]:
            user.set_password(validated_data["password"])
        if "user_profile" in validated_data:
            user.user_profile = validated_data["user_profile"]

        user.save()

        instance.phone_no = validated_data.get("phone_no", instance.phone_no)
        instance.gender = validated_data.get("gender", instance.gender)
        instance.department = validated_data.get("department", instance.department)
        instance.save()

        if "student" in validated_data:
            instance.student.set(validated_data["student"])
        if "teacher" in validated_data:
            instance.teacher.set(validated_data["teacher"])
        if "admissions" in validated_data:
            instance.admissions.set(validated_data["admissions"])

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.update({
            "first_name": instance.user.first_name,
            "middle_name": instance.user.middle_name,
            "last_name": instance.user.last_name,
            "email": instance.user.email,
            "user_profile": instance.user.user_profile.url if instance.user.user_profile else None,
        })

        # Remove relational fields from the output
        representation.pop("student", None)
        representation.pop("teacher", None)
        representation.pop("admissions", None)

        return representation
    
    
    
    # ******************DocumentTypeSerializer*************************
    

# import json

class DocumentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentType
        fields = "__all__"


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'file']



class DocumentSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True, read_only=True)

    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=True,
        allow_empty=False
    )

    # Accepts list of IDs at POST/PUT time
    document_types = serializers.PrimaryKeyRelatedField(
        queryset=DocumentType.objects.all(),
        many=True,
        required=True,
        allow_empty=False
    )

    identities = serializers.ListField(
        child=serializers.CharField(),
        write_only=True
    )

    identities_read = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'document_types', 'identities', 'identities_read', 'files', 'uploaded_files',
            'student', 'teacher', 'guardian', 'office_staff', 'uploaded_at'
        ]

    def get_identities_read(self, obj):
        import json
        try:
            return json.loads(obj.identities) if obj.identities else []
        except:
            return []

    def to_representation(self, instance):
        """Customize the output to show document type names instead of just IDs."""
        representation = super().to_representation(instance)
        document_types = instance.document_types.all()
        representation['document_types'] = [
            {"id": dt.id, "name": dt.name} for dt in document_types
        ]
        return representation

    def create(self, validated_data):
        import json

        uploaded_files = validated_data.pop('uploaded_files')
        document_types = validated_data.pop('document_types')
        identities_list = validated_data.pop('identities')

        if len(document_types) != len(identities_list):
            raise serializers.ValidationError("Number of document_types and identities must match.")

        document = Document.objects.create(**validated_data)
        document.document_types.set(document_types)
        document.identities = json.dumps(identities_list)
        document.save()

        for uploaded_file in uploaded_files:
            File.objects.create(file=uploaded_file, document=document)

        return document

