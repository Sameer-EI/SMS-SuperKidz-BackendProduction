from django.db import models
from director.models import *
from student.models import Student
from teacher.models import *


class Holiday(models.Model):
    title = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        if self.start_date == self.end_date:
            return f"{self.title} ({self.start_date})"
        return f"{self.title} ({self.start_date} to {self.end_date})"

    
    
class StudentAttendance(models.Model):
    STATUS_CHOICES = [
        ('P', 'Present'),
        ('A', 'Absent'),
        ('L', 'Leave'),
        ('H','Holiday') # remove it in future
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES)
    marked_at = models.DateField()
    teacher=models.ForeignKey(Teacher,on_delete=models.CASCADE,null=True,blank=True)
    year_level=models.ForeignKey(YearLevel,on_delete=models.CASCADE)


    def __str__(self):
        return f"{self.student} -{self.status}"
    
    class Meta:
        unique_together = ('student', 'marked_at')
        
class SchoolHoliday(models.Model):
    title = models.CharField(max_length=100)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    
class SchoolEvent(models.Model):
    title = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} ({self.start_date} to {self.end_date})"


class OfficeStaffAttendance(models.Model):
    office_staff = models.ForeignKey(OfficeStaff, on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=10, choices=[('Present', 'Present'), ('Absent', 'Absent'), ('Leave', 'Leave')])

    class Meta:
        unique_together = ('office_staff', 'date')

    def __str__(self):
        return f"{self.office_staff} - {self.date} - {self.status}"
    