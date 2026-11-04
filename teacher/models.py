from django.db import models
from authentication.models import User
from django.utils import timezone

# from director.models import YearLevel


# Create your models here.

class TeacherManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def all_including_inactive(self):
        return super().get_queryset()



class Teacher(models.Model):
    CADRE_CHOICES = [
        ('PRT', 'PRT'),
        ('TGT', 'TGT'),
        ('PGT', 'PGT'),
    ]

    user = models.OneToOneField(User, on_delete=models.DO_NOTHING)
    phone_no = models.CharField(max_length=15,null=True,blank=True)
    gender = models.CharField(max_length=10,null=True,blank=True)
    adhaar_no = models.BigIntegerField(null=True,blank=True,unique=True)
    pan_no = models.CharField(max_length=20,null=True,blank=True,unique=True)
    qualification = models.CharField(max_length=250,null=True,blank=True)
    cadre = models.CharField(max_length=10, choices=CADRE_CHOICES, null=True, blank=True)
    subject = models.ForeignKey('director.Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='teachers')
    joining_date = models.DateField(auto_now_add=True,null=True,blank=True)  #added as of 19Sep25 at 03:00 PM
    is_active = models.BooleanField(default=True)

    year_levels = models.ManyToManyField('director.YearLevel', through='TeacherYearLevel')
    
    objects = TeacherManager()
    def __str__(self):
        full_name = f"{self.user.first_name} {self.user.last_name}".strip() if self.user else f"Teacher {self.id}"
        parts = []
        if self.cadre:
            parts.append(self.cadre)
        if self.subject:
            parts.append(self.subject.subject_name)
        suffix = f" ({' - '.join(parts)})" if parts else ""
        return f"{full_name}{suffix}".strip()

    class Meta:
        db_table = "teacher"
        indexes = [models.Index(fields=['is_active'])]



class TeacherYearLevel(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    year_level = models.ForeignKey('director.YearLevel', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('teacher', 'year_level')

    def __str__(self):  
        return f"{self.teacher} - {self.year_level}"   



class SubstituteAssignment(models.Model):
    absent_teacher = models.ForeignKey(Teacher, related_name='absent_assignments', on_delete=models.CASCADE)
    substitute_teacher = models.ForeignKey(Teacher, related_name='substitute_assignments', on_delete=models.CASCADE)
    year_level = models.ForeignKey('director.YearLevel', on_delete=models.CASCADE)
    period = models.CharField(max_length=100)
    day_of_week = models.CharField(max_length=20, null=True, blank=True)
    reason = models.CharField(max_length=150, default="Casual Leave / Absent", blank=True, null=True)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"Sub: {self.substitute_teacher} for {self.absent_teacher} on {self.date} ({self.period})"

