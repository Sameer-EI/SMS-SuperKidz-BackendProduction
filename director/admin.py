from django.contrib import admin
from director.models import *

# Register your models here.

admin.site.register(
    [
        Director,
        Subject,
        Term,
        Period,
        ClassRoom,
        YearLevel,
        SchoolYear,
        ClassRoomType,
        Department,
        ClassPeriod,
        Role,
        Admission,
        BankingDetail,
        FeeType,
        YearLevelFee,
        FeeRecord,
        File,
        Document,
        DocumentType,
        OfficeStaff,
        City,
        State,
        Country,
        Address
    ]
)
