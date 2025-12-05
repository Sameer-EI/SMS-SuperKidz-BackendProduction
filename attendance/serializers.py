from rest_framework import serializers
from .models import *



# class AttendanceSessionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = AttendanceSession
#         fields = '__all__'


class StudentAttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAttendance
        fields = '__all__'
        
        

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
    office_staff_name = serializers.SerializerMethodField()

    class Meta:
        model = OfficeStaffAttendance
        fields = [
            'id',
            'date',
            'status',
            'office_staff',
            'office_staff_name',
        ]

    def get_office_staff_name(self, obj):
        return obj.office_staff.user.get_full_name() if obj.office_staff else None

    



