from django.urls import path,include
from .views import *
from director.views import Director_Dashboard_Summary


from rest_framework.routers import DefaultRouter



router = DefaultRouter()

router.register(r'country', CountryView)
router.register(r'states', StateView)
router.register(r'city', CityView)
router.register(r'addresses', AddressView)
router.register(r'Period', PeriodView)
router.register(r'classPeriod', ClassPeriodView)
router.register(r'director', DirectorView)
router.register(r'banking_details', BankingDetailView)
router.register(r'terms', TermView)
router.register(r'admission',AdmissionView)
router.register(r'officestaff',OfficeStaffView)
router.register(r'DocumentType',DocumentTypeView)

router.register(r'File',FileView),
router.register(r'Document',DocumentView),
router.register(r'subject',subjectView),
# router.register(r'class-periods', ClassPeriodView),
router.register(r'fee-types', FeeTypeView) # whole code commented as of 06June25 at 12:30 PM
router.register(r'year-level-fee', YearLevelFeeView, basename='year-level-fee')
router.register(r'fee-record', FeeRecordView, basename='fee-record') #
# router.register(r'submit_fee',FeeSubmitView, basename='submit_fee')


urlpatterns = [
    path("year-levels/", YearLevelView),
    path("year-level/<int:id>/", YearLevelView),
    path("school-years/", SchoolYearView),
    path("school-year/<int:pk>/", SchoolYearView),
    path("departments/", DepartmentView),
    path("department/<int:pk>/", DepartmentView),
    path("classroom-types/", ClassRoomTypeView),
    path("classroom-type/<int:pk>/", ClassRoomTypeView),
    path("roles/", RoleView, name="roleDetails"),
    path("role/<int:pk>/", RoleView, name="roleDetails"),
    path("director-dashboard/", Director_Dashboard_Summary),
    path("teacher-dashboard/<int:id>/", teacher_dashboard),
    path("guardian-dashboard/<int:id>/", guardian_dashboard),
    path("student_dashboard/<int:id>/", student_dashboard),
    path('office-staff-dashboard/', office_staff_dashboard),
    # path('office-staff-dashboard/<int:id>/', office_staff_dashboard),
    # path("student-dashboard/<int:id>/", student_dashboard),
    path("director/fee-summary/", director_fee_summary),
    path('income_filter/', guardian_income_distribution),
    path('livelihood_filter/', livelihood_distribution),
    path('', include(router.urls)),
    # path('submit-fee/', FeeView.as_view(), name='submit-fee'),
    # path("fee_submission/<int:student_id>/", FeeSubmissionView.as_view(), name='fee-submission'),
    
    # As of 25June25 at 12:35
    path('student-category-dashboard/', student_category, name='student-category'),
    path('income-distribution-dashboard/', guardian_income_distribution, name='guardian-income-distribution'), 
    path("fee-dashboard/", fee_dashboard, name="fee-dashboard-summary"),    # complete dashboard
]









