from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . views import *


router = DefaultRouter()
router.register(r'teacher', TeacherView)
router.register(r'teacheryearlevel', TeacherYearLevelView)



urlpatterns = [
    path('', include(router.urls)),   
]