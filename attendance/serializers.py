from rest_framework import serializers
from .models import *
from datetime import date
from django.db.models import Q
from .utils import validate_basic_attendance_rules

class StudentAttendanceSerializer(serializers.ModelSerializer):
    # ----- Input-only fields -----
    teacher_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    office_staff_id = serializers.IntegerField(write_only=True,required=False,allow_null=True)
    #teacher_id = serializers.PrimaryKeyRelatedField(queryset=Teacher.objects.all(),source="teacher",write_only=True,required=False,allow_null=True)
    #office_staff_id = serializers.PrimaryKeyRelatedField(queryset=OfficeStaff.objects.all(),source="office_staff",write_only=True,required=False,allow_null=True)
    year_level_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    status = serializers.CharField(required=False)

    P = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    A = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    L = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    # ----- Output-only fields -----
    student_name = serializers.CharField(
        source="student.user.get_full_name",
        read_only=True
    )
    teacher_name = serializers.CharField(
        source="teacher.user.get_full_name",
        read_only=True
    )
    office_staff_name = serializers.CharField(
    source="office_staff.user.get_full_name",
    read_only=True
    )

    class Meta:
        model = Attendance
        fields = ["id","student_name","teacher_name","office_staff_name","status","marked_at","teacher_id","office_staff_id","year_level_id","P","A","L",
                   "student", "teacher","office_staff","year_level",]
        read_only_fields = ["id", "student", "teacher","office_staff","year_level",]


    def validate(self, attrs):
        request = self.context.get("request")

        # If updating single record → skip bulk validation
        if request and request.method in ["PUT", "PATCH"]:
            return attrs

        marked_at = attrs.get("marked_at", date.today())
        validate_basic_attendance_rules(marked_at)

        teacher_id = attrs.get("teacher_id")
        office_staff_id = attrs.get("office_staff_id")
        year_level_id = attrs.get("year_level_id")

        if teacher_id and office_staff_id:
            raise serializers.ValidationError(
                "Provide either teacher_id or office_staff_id, not both."
            )
        if not teacher_id and not office_staff_id:
            raise serializers.ValidationError(
                "Either teacher_id or office_staff_id is required."
            )

        if not year_level_id:
            raise serializers.ValidationError({
                "year_level_id": "year_level_id is required."
            })

        target_year_level = YearLevel.objects.filter(id=year_level_id).first()
        if not target_year_level:
            raise serializers.ValidationError({
                "year_level_id": f"Invalid year level ID: {year_level_id}."
            })

        # Check Teacher-YearLevel match
        if teacher_id:
            teacher = Teacher.objects.filter(id=teacher_id).first()
            if not teacher:
                raise serializers.ValidationError({
                    "teacher_id": f"Invalid teacher ID: {teacher_id}."
                })

            if not TeacherYearLevel.objects.filter(
                    teacher=teacher,
                    year_level_id=year_level_id
            ).exists():
                teacher_name = teacher.user.get_full_name() if teacher.user else f"ID {teacher.id}"
                raise serializers.ValidationError({
                    "teacher_id": f"Teacher '{teacher_name}' is not assigned to year level '{target_year_level.level_name}' (ID: {year_level_id})."
                })
            attrs["teacher"] = teacher

        # Check OfficeStaff
        if office_staff_id:
            office_staff = OfficeStaff.objects.filter(id=office_staff_id).first()
            if not office_staff:
                raise serializers.ValidationError({
                    "office_staff_id": f"Invalid office staff ID: {office_staff_id}."
                })
            attrs["office_staff"] = office_staff

        allowed_statuses = {"P", "A", "L"}
        all_student_ids = []

        for status_code in allowed_statuses:
            all_student_ids.extend(attrs.get(status_code, []))

        if not all_student_ids:
            raise serializers.ValidationError(
                "At least one attendance status must be provided."
            )
        if len(all_student_ids) != len(set(all_student_ids)):
            raise serializers.ValidationError(
                "A student ID cannot appear in multiple status lists."
            )
        
        students = Student.objects.filter(id__in=all_student_ids, is_active=True)
        found_student_ids = set(students.values_list("id", flat=True))
        missing_student_ids = set(all_student_ids) - found_student_ids
        if missing_student_ids:
            raise serializers.ValidationError({
                "student_ids": [
                    f"Active student not found: {sid}"
                    for sid in missing_student_ids
                ]
            })

        for student in students:
            if not student.student_year_levels.filter(
                    level_id=year_level_id
            ).exists():
                actual_levels = [
                    f"{syl.level.level_name} (ID: {syl.level_id})"
                    for syl in student.student_year_levels.select_related("level").all()
                ]
                actual_levels_str = ", ".join(actual_levels) if actual_levels else "No year level assigned"
                student_name = student.user.get_full_name() if student.user else f"Student #{student.id}"
                raise serializers.ValidationError(
                    f"Student {student.id} ({student_name}) belongs to {actual_levels_str}, not '{target_year_level.level_name}' (ID: {year_level_id})."
                )
        # commented out the duplicate check for now, as it will not allow updation as required as of 21/9/2026    
        """
        # Duplicate check here (student specific)
        already_marked = Attendance.objects.filter(
            student_id__in=all_student_ids,
            marked_at=marked_at
        ).values_list("student_id", flat=True)

        if already_marked:
            raise serializers.ValidationError({
                "error": "Attendance already marked for this date.",
                "student_ids": list(already_marked)
            })
        """
        return attrs


class StudentAttendancePercentSerializer(serializers.Serializer):
    student_name = serializers.CharField()
    class_name = serializers.CharField()
    monthly_percentage = serializers.FloatField()
    yearly_percentage = serializers.FloatField()
    
    
class HolidaySerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True, allow_blank=False)
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    class Meta:
        model = Holiday
        fields = '__all__'

    def validate(self, data):
        start = data["start_date"]
        end = data["end_date"]

        if start > end:
            raise serializers.ValidationError("Start date must be before end date.")

        # max 45 days check
        if (end - start).days > 45:
            raise serializers.ValidationError("Holiday duration cannot exceed 45 days.")

        # optional: prevent overlapping holidays.
        qs = Holiday.objects.filter(
            start_date__lte=end,
            end_date__gte=start
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Holiday dates overlap with another holiday.")

        return data

        
class SchoolHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolHoliday
        fields = ['id', 'title', 'date', 'description']
        
class SchoolEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolEvent
        fields = ['id', 'title', 'start_date', 'end_date', 'description']


class OfficeStaffAttendanceSerializer(serializers.ModelSerializer):
    marked_at = serializers.DateField(required=False)
    P = serializers.ListField(child=serializers.IntegerField(), required=False)
    A = serializers.ListField(child=serializers.IntegerField(), required=False)
    L = serializers.ListField(child=serializers.IntegerField(), required=False)
    status = serializers.CharField(required=False)

    office_staff_name = serializers.CharField(source="office_staff.user.get_full_name", read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id',
            'marked_at',
            'status',
            'office_staff',
            'office_staff_name','P','A','L'
        ]
        read_only_fields = ["id",'office_staff_name','office_staff']


    def validate(self, attrs):
        request = self.context.get("request")

        if request and request.method in ["PUT", "PATCH"]:
            marked_at = attrs.get("marked_at", self.instance.marked_at)
            validate_basic_attendance_rules(marked_at)
            return attrs
    
        marked_at = attrs.get("marked_at") or date.today()
        validate_basic_attendance_rules(marked_at)

        present = attrs.get("P", [])
        absent = attrs.get("A", [])
        leave = attrs.get("L", [])

        all_ids = present + absent + leave

        if not all_ids:
            raise serializers.ValidationError(
                "At least one office staff ID must be provided."
            )

        if len(all_ids) != len(set(all_ids)):
            raise serializers.ValidationError(
                "A staff ID cannot appear in multiple status lists."
            )
        
        existing_staff_ids = set(
            OfficeStaff.objects.filter(id__in=all_ids)
            .values_list("id", flat=True)
        )

        missing_ids = set(all_ids) - existing_staff_ids

        if missing_ids:
            raise serializers.ValidationError({
                "error": "Some office staff IDs do not exist.",
                "missing_ids": list(missing_ids)
            })


        # DB duplicate safety check
        already_marked = Attendance.objects.filter(
            office_staff_id__in=all_ids,
            marked_at=marked_at
        ).values_list("office_staff_id", flat=True)

        if already_marked:
            raise serializers.ValidationError({
                "error": "Attendance already marked for some staff.",
                "office_staff_name": list(OfficeStaff.objects.filter(id__in=already_marked).values_list("user__first_name", flat=True))
            })

        attrs["marked_at"] = marked_at
        return attrs


class TeacherAttendanceSerializer(serializers.ModelSerializer):
    marked_at = serializers.DateField(required=False)
    P = serializers.ListField(child=serializers.IntegerField(), required=False)
    A = serializers.ListField(child=serializers.IntegerField(), required=False)
    L = serializers.ListField(child=serializers.IntegerField(), required=False)
    status = serializers.CharField(required=False)

    teacher_name = serializers.CharField(source="teacher.user.get_full_name", read_only=True)
    
    class Meta:
        model = Attendance
        fields = [
            'id',
            'marked_at',
            'status',
            'teacher',
            'teacher_name','P','A','L'
        ]
        read_only_fields = ["id","teacher_name",'teacher']

    def validate(self, attrs):
        request = self.context.get("request")

        if request and request.method in ["PUT", "PATCH"]:
            marked_at = attrs.get("marked_at", self.instance.marked_at)
            validate_basic_attendance_rules(marked_at)
            return attrs

        marked_at = attrs.get("marked_at") or date.today()
        validate_basic_attendance_rules(marked_at)

        present = attrs.get("P", [])
        absent = attrs.get("A", [])
        leave = attrs.get("L", [])

        all_ids = present + absent + leave

        # At least one teacher required
        if not all_ids:
            raise serializers.ValidationError(
                "At least one teacher ID must be provided."
            )

        # Prevent duplicate IDs across lists
        if len(all_ids) != len(set(all_ids)):
            raise serializers.ValidationError(
                "A teacher ID cannot appear in multiple status lists."
            )

        # Check teacher existence
        existing_teacher_ids = set(
            Teacher.objects.filter(id__in=all_ids)
            .values_list("id", flat=True)
        )

        missing_ids = set(all_ids) - existing_teacher_ids
        if missing_ids:
            raise serializers.ValidationError({
                "error": "Some teacher IDs do not exist.",
                "missing_ids": list(missing_ids)
            })

        # Duplicate attendance check
        already_marked = Attendance.objects.filter(
            teacher_id__in=all_ids,
            marked_at=marked_at,
            student__isnull=True
        ).values_list("teacher_id", flat=True)

        if already_marked:
            raise serializers.ValidationError({
                "error": "Attendance already marked for some teachers.",
                "teacher_name": list(Teacher.objects.filter(id__in=already_marked).values_list("user__first_name", flat=True))
            })

        attrs["marked_at"] = marked_at
        return attrs

#serializers for Attendance Register API
class AttendanceRegisterStudentSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    roll_number = serializers.CharField(allow_null=True)
    term_percentage = serializers.FloatField()
    status = serializers.CharField(allow_null=True)
    attendance_id = serializers.IntegerField(allow_null=True)


class AttendanceRegisterSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    leave = serializers.IntegerField()
    unmarked = serializers.IntegerField()


class StudentAttendanceRegisterSerializer(serializers.Serializer):
    year_level_id = serializers.IntegerField()
    class_name = serializers.CharField()
    date = serializers.DateField()
    is_school_day = serializers.BooleanField()
    holiday_reason = serializers.CharField(allow_null=True)

    summary = AttendanceRegisterSummarySerializer()

    students = AttendanceRegisterStudentSerializer(many=True)


#Attendance Defaulters

class AttendanceDefaulterSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    roll_number = serializers.CharField(allow_null=True)
    class_name = serializers.CharField()
    year_level_id = serializers.IntegerField()
    term_percentage = serializers.FloatField()
    days_present = serializers.IntegerField()
    days_absent = serializers.IntegerField()
    days_leave = serializers.IntegerField()
    total_working_days = serializers.IntegerField()
    guardian_name = serializers.CharField(allow_null=True)
    guardian_phone = serializers.CharField(allow_null=True)


class AttendanceDefaultersResponseSerializer(serializers.Serializer):
    threshold = serializers.FloatField()
    total_defaulters = serializers.IntegerField()
    defaulters = AttendanceDefaulterSerializer(many=True)

#Notification to parents about attendance defaulters
class NotifyParentSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    notification_type = serializers.CharField()
    custom_message = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True
    )


#Heatmap serializers


class AttendanceHeatMapItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    status = serializers.CharField()


class AttendanceHeatMapTermSummarySerializer(serializers.Serializer):
    percentage = serializers.FloatField()
    present_days = serializers.IntegerField()
    absent_days = serializers.IntegerField()
    leave_days = serializers.IntegerField()
    total_working_days = serializers.IntegerField()


class StudentAttendanceHeatMapSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    roll_number = serializers.CharField(allow_null=True)
    class_name = serializers.CharField()
    term_summary = AttendanceHeatMapTermSummarySerializer()
    heat_map = AttendanceHeatMapItemSerializer(many=True)

