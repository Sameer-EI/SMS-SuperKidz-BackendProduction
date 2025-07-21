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
    class Meta:
        model = Holiday
        fields = '__all__'
    
    



