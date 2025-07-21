from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView,TokenRefreshView
from .views import UserView



urlpatterns = [
    # path("users/", views.UserView, name="custom_user_list"),
    path('users/', UserView.as_view(), name='user-registration'),
    # path("user/<int:pk>/", views.UserView, name="custom_user_detail"),
    path("change_password/", views.ChangePasswordView),
    path("login/", views.LoginView),
    path("logout/", views.LogOutView),
    path('refreshtoken/',TokenRefreshView.as_view(),name='token_refresh'),
    path("otp/", views.SendOtpView),
    path("reset_password/", views.ForgotPasswordView),

]





