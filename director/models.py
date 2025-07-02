import random
import string
import uuid
from django.db import models
# from authentication.models import User
# from student.models import Student, Guardian,StudentYearLevel
from .utils import Document_folder 
from teacher.models import Teacher 
from django.utils.timezone import now





class Role(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        db_table = "Role"


class Country(models.Model):
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"
        db_table = "Country"


class State(models.Model):
    name = models.CharField(max_length=120)
    country = models.ForeignKey(Country, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "State"
        verbose_name_plural = "States"
        db_table = "State"


class City(models.Model):
    name = models.CharField(max_length=120)
    state = models.ForeignKey(State, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "City"
        verbose_name_plural = "Cities"
        db_table = "City"


class Address(models.Model):
    user = models.ForeignKey("authentication.User", on_delete=models.DO_NOTHING)
    house_no = models.IntegerField(null=True, blank=True)
    habitation = models.CharField(max_length=100,null=True, blank=True)
    ward_no = models.IntegerField(null=True, blank=True)
    zone_no = models.IntegerField(null=True, blank=True)
    block = models.CharField(max_length=100,null=True, blank=True)
    district = models.CharField(max_length=100,null=True, blank=True)
    division = models.CharField(max_length=100,null=True, blank=True)
    area_code = models.IntegerField(null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.DO_NOTHING)
    state = models.ForeignKey(State, on_delete=models.DO_NOTHING)
    city = models.ForeignKey(City, on_delete=models.DO_NOTHING)
    address_line = models.CharField(max_length=250,null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.address_line}"

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        db_table = "Address"


class Director(models.Model):
    user = models.OneToOneField("authentication.User", on_delete=models.SET_NULL,null=True)
    phone_no = models.CharField(max_length=250, null=True, blank=True)
    gender = models.CharField(max_length=50,null=True, blank=True)

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = "Director"
        verbose_name_plural = "Directors"
        db_table = "Director"


class BankingDetail(models.Model):
    account_no = models.BigIntegerField( )
    # account_no = models.BigIntegerField(primary_key=True, unique=True)
    ifsc_code = models.CharField(max_length=225)
    holder_name = models.CharField(max_length=255)
    user = models.OneToOneField("authentication.User", on_delete=models.DO_NOTHING)

    # def __str__(self):
    #     return str(self.account_no)
    def __str__(self):      # added as of 06May25 at 02:23 PM
        return f"{self.holder_name} ({self.account_no})"


    class Meta:
        verbose_name = "Banking Detail"
        verbose_name_plural = "Banking Details"
        db_table = "BankingDetail"


class SchoolYear(models.Model):
    year_name = models.CharField(max_length=250)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False)

    def __str__(self):
        return self.year_name

    class Meta:
        verbose_name = "School Year"
        verbose_name_plural = "School Years"
        db_table = "SchoolYear"


# 


class Term(models.Model):
    year = models.ForeignKey(SchoolYear, on_delete=models.DO_NOTHING)
    term_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"{self.year} - Term {self.term_number}"

    class Meta:
        verbose_name = "Term"
        verbose_name_plural = "Terms"
        db_table = "Term"


class Period(models.Model):
    year = models.ForeignKey(SchoolYear, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=250)
    start_period_time = models.TimeField()
    end_period_time = models.TimeField()

    def __str__(self):
        return f"{self.start_period_time} - {self.end_period_time} - {self.name}"

    # def __str__(self):
    #     return f"{self.year} - {self.name}"
    class Meta:
        verbose_name = "Period"
        verbose_name_plural = "Periods"
        db_table = "Period"


class Department(models.Model):
    department_name = models.CharField(max_length=250, null=False)

    def __str__(self):
        return self.department_name

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        db_table = "Department"


class Subject(models.Model):
    department = models.ForeignKey(Department, on_delete=models.DO_NOTHING)
    subject_name = models.CharField(max_length=250, null=False)

    def __str__(self):
        return f"{self.department} - {self.subject_name}"

    class Meta:
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"
        db_table = "Subject"


class ClassRoomType(models.Model):
    name = models.CharField(max_length=250, null=False)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Class Room Type"
        verbose_name_plural = "Class Room Types"
        db_table = "ClassRoomType"


class ClassRoom(models.Model):
    room_type = models.ForeignKey(ClassRoomType, on_delete=models.DO_NOTHING)
    room_name = models.CharField(max_length=200)
    capacity = models.IntegerField()

    def __str__(self):
        return f"{self.room_type} - {self.room_name}"

    class Meta:
        verbose_name = "Class Room"
        verbose_name_plural = "Class Rooms"
        db_table = "ClassRoom"


class ClassPeriod(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING)
    teacher = models.ForeignKey("teacher.Teacher", on_delete=models.DO_NOTHING)
    term = models.ForeignKey(Term, on_delete=models.DO_NOTHING)
    start_time = models.ForeignKey(
        Period, on_delete=models.DO_NOTHING, related_name="start_time"
    )  
    end_time = models.ForeignKey(
        Period, on_delete=models.DO_NOTHING, related_name="end_time"
    )
    classroom = models.ForeignKey(ClassRoom, on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=250)
   


    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "ClassPeriod"
        verbose_name_plural = "ClassPeriods"
        db_table = "ClassPeriod"







class Admission(models.Model):
    enrollment_no = models.CharField( max_length=20,blank=True, null=True)
    student = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    admission_date = models.DateField(auto_now_add=True)
    previous_school_name = models.CharField(max_length=200)
    previous_standard_studied = models.CharField(max_length=200)
    tc_letter = models.CharField(max_length=200)
    guardian = models.ForeignKey(Guardian, on_delete=models.DO_NOTHING)
    year_level = models.ForeignKey('YearLevel', on_delete=models.SET_NULL, null=True, blank=True)
    # year_level = models.ForeignKey('YearLevel', on_delete=models.DO_NOTHING)

    school_year = models.ForeignKey(SchoolYear, on_delete=models.DO_NOTHING)
    emergency_contact_no = models.CharField(max_length=100)
    entire_road_distance_from_home_to_school = models.CharField(max_length=100)
    obtain_marks = models.FloatField()
    total_marks = models.FloatField()
    previous_percentage = models.FloatField(blank=True, null=True)  # Allow null/blank since auto-calculated

    # def save(self, *args, **kwargs):
    #     if self.total_marks > 0:
    #         self.previous_percentage = (self.obtain_marks / self.total_marks) * 100
    #     else:
    #         self.previous_percentage = 0  
    #     super().save(*args, **kwargs)
    def save(self, *args, **kwargs):
        if not self.enrollment_no:
            current_year = now().year
            prefix = str(current_year)
            
            last_admission = Admission.objects.filter(enrollment_no__startswith=prefix).order_by('-enrollment_no').first()
            
            if last_admission and last_admission.enrollment_no:
                last_seq_num = int(last_admission.enrollment_no.split('-')[-1])
                new_seq_num = last_seq_num + 1
            else:
                new_seq_num = 1
            
            self.enrollment_no = f"{prefix}-{new_seq_num:04d}"

        if self.total_marks > 0:
            self.previous_percentage = (self.obtain_marks / self.total_marks) * 100
        else:
            self.previous_percentage = 0

        super().save(*args, **kwargs)

        
    def __str__(self):
     return f"Admission of {self.student} (Guardian: {self.guardian}) - YearLevel: {self.year_level if self.year_level else 'None'}"
    



    class Meta:
        db_table = "Admission"



from django.db import models
import random
import string


class FeeType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Fee Type"
        verbose_name_plural = "Fee Types"
        db_table = "FeeType"


class YearLevel(models.Model):
    level_name = models.CharField(max_length=250)
    level_order = models.IntegerField()

    def __str__(self):
        return f"{self.level_name}"


    class Meta:
        verbose_name = "Year Level"
        verbose_name_plural = "Year Levels"
        db_table = "YearLevel"

class YearLevelFee(models.Model):
    year_level = models.ForeignKey(YearLevel, on_delete=models.CASCADE)
    fee_type = models.ForeignKey(FeeType, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.year_level} - {self.fee_type.name} - {self.amount}"

    class Meta:
        verbose_name = "Year Level Fee"
        verbose_name_plural = "Year Level Fees"
        db_table = "YearLevelFee"

class FeeRecord(models.Model):
    student = models.ForeignKey("student.Student", on_delete=models.CASCADE)
    MONTH_CHOICES = [
        ("July", "July"), ("August", "August"), ("September", "September"),
        ("October", "October"), ("November", "November"), ("December", "December"),
        ("January", "January"), ("February", "February"), ("March", "March"),
        ("April", "April"), ("May", "May"), ("June", "June"),
    ]
    month = models.CharField(max_length=20, choices=MONTH_CHOICES)
    year_level_fees = models.ManyToManyField(YearLevelFee)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=8, decimal_places=2)
    due_amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_date = models.DateField(auto_now_add=True)
    payment_mode = models.CharField(max_length=20, choices=[('Cash', 'Cash'), ('Online', 'Online'), ('Cheque', 'Cheque')])
    is_cheque_cleared = models.BooleanField(default=False)  # Added as of 11June25 at 12:39 PM
    receipt_number = models.CharField(max_length=10, unique=True, editable=False, blank=True, auto_created=True)
    late_fee = models.DecimalField(max_digits=8, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=[('Paid', 'Paid'), ('Unpaid', 'Unpaid')])
    remarks = models.TextField(blank=True, null=True)
    received_by = models.CharField(max_length=100, null=True,blank=True)      # modified 24June25
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature_id = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.month}"

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = self.generate_unique_receipt_number()
        super().save(*args, **kwargs)

    def generate_unique_receipt_number(self):
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not FeeRecord.objects.filter(receipt_number=code).exists():
                return code

    class Meta:
        verbose_name = "Fee Record"
        verbose_name_plural = "Fee Records"
        db_table = "FeeRecord"








class OfficeStaff(models.Model):
    user = models.OneToOneField("authentication.User", on_delete=models.SET_NULL, null=True)
    phone_no = models.CharField(max_length=20)
    gender = models.CharField(max_length=20)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    date_joined = models.DateField(auto_now_add=True)
    student = models.ManyToManyField("student.Student", blank=True, related_name="managed_by_staff")
    teacher = models.ManyToManyField("teacher.Teacher", blank=True, related_name="managed_by_staff")
    admissions = models.ManyToManyField(Admission, blank=True, related_name="handled_by_staff")

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.department})"

    class Meta:
        verbose_name = "Office Staff"
        verbose_name_plural = "Office Staff"
        db_table = "OfficeStaff"
        
        

class DocumentType(models.Model):
    name = models.CharField(max_length=100)
    

    def __str__(self):
        return self.name

    class Meta:
        db_table = "DocumentType"
        
        
        

class Document(models.Model):
    document_types = models.ManyToManyField(DocumentType)
    identities = models.CharField(max_length=1000, blank=True, null=True)
    
    student = models.ForeignKey("student.Student", on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey("teacher.Teacher", on_delete=models.SET_NULL, null=True, blank=True)
    guardian = models.ForeignKey("student.Guardian", on_delete=models.SET_NULL, null=True, blank=True)
    office_staff = models.ForeignKey(OfficeStaff, on_delete=models.SET_NULL, null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        entity = self.student or self.teacher or self.guardian or self.office_staff
        return f"{self.document_types.name} - {entity}"

    class Meta:
        db_table = "Document"
        
class File(models.Model):
    file = models.FileField(upload_to=Document_folder) 
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='files', null=True)
 
    

    def __str__(self):
        return f"File {self.id} - {self.file.name}"

    class Meta:
        db_table = "File"