from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import *
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, BlacklistMixin
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.core.cache import cache
from rest_framework.views import APIView




class UserView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data, context={'request': request})
        # serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "User created successfully.",
                "user": {
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "roles": [role.name for role in user.role.all()]
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ChangePasswordView(request):
    current_password = request.data.get("current_password")
    Change_Password = request.data.get("change_password")
    email = request.data.get("email")

    serialized = ChangePasswordSerializer(data=request.data)

    if serialized.is_valid():

        user = authenticate(email=email, password=current_password)

        if user is not None:

            user.set_password(Change_Password)
            user.save()
            return Response({"Message": " Changed password Successfully"})

        return Response({"Message ": " Invalid Password"})
    return Response(serialized.errors, status=400)


from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import LoginSerializers  # adjust import if needed

@api_view(["POST"])
def LoginView(request):
    if request.method == "POST":
        email = request.data.get("email")
        password = request.data.get("password")

        serializer = LoginSerializers(data=request.data, context={'request': request})

        if serializer.is_valid():

            user = authenticate(email=email, password=password)

            if user is None:
                return Response(
                    {"Message": "Invalid Credentials"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh_token = str(refresh)

            user_roles = user.role.all()
            role_names = [role.name for role in user_roles]

            # Build full name
            full_name = f"{user.first_name} {user.middle_name or ''} {user.last_name}".strip()

            # Build user_profile URL
            profile_url = None
            if user.user_profile:
                request = request  # from outer scope
                profile_url = request.build_absolute_uri(user.user_profile.url)


            # Assuming only one role per user
            role_name = role_names[0] if role_names else None

            role_id = None
            role_key = None

            if role_name == "teacher":
                try:
                    teacher = Teacher.objects.get(user=user)
                    role_id = teacher.id
                    role_key = "teacher_id"
                except Teacher.DoesNotExist:
                    pass

            elif role_name == "student":
                try:
                    student = Student.objects.get(user=user)
                    role_id = student.id
                    role_key = "student_id"
                except Student.DoesNotExist:
                    pass

            elif role_name == "guardian":
                try:
                    guardian = Guardian.objects.get(user=user)
                    role_id = guardian.id
                    role_key = "guardian_id"
                except Guardian.DoesNotExist:
                    pass

            elif role_name == "director":
                try:
                    director = Director.objects.get(user=user)
                    role_id = director.id
                    role_key = "director_id"
                except Director.DoesNotExist:
                    pass
            elif role_name=='office staff':
                try:
                  staf=OfficeStaff.objects.get(user=user)
                  role_id=staf.id
                  role_key="staff_id"
                except OfficeStaff.DoesNotExist:
                    pass


            response_data = {
                    "Message": "User logged in successfully",
                    "Access Token": access,
                    "Refresh Token": refresh_token,
                    "User ID": user.id,
                    "Roles": role_names,
                    "name": full_name,
                    "user_profile": profile_url or None,
                }

            if role_key:
                response_data[role_key] = role_id

            return Response(response_data, status=status.HTTP_200_OK)

        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




@api_view(["POST"])
def LogOutView(request):
    if request.method == "POST":

        serializer = LogoutSerializers(data=request.data)

        if serializer.is_valid():
            refresh_token = serializer.validated_data.get("refresh_token")

            if refresh_token:
                refresh = RefreshToken(refresh_token)
                refresh.blacklist()

                return Response(
                    {"Message": "LogOut Successfuly"}, status=status.HTTP_200_OK
                )

            return Response(
                {"error": "Refresh token not provide"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"Error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def SendOtpView(request):

    email_serialzer = OtpSerializers(data=request.data)

    if email_serialzer.is_valid():
        email = email_serialzer.validated_data["email"]
        otp = get_random_string(length=6, allowed_chars="1234567890")
        cache.set(email, otp, timeout=300)

        if email is not None:
            from django.conf import settings

            send_mail(
                "Reset your Password",
                f"Your Otp for Forgot Password {otp}",
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return Response(
                {"Message": "Otp Sent to your Email"}, status=status.HTTP_200_OK
            )
        return Response({"Message": "Invalid Email"}, status=status.HTTP_204_NO_CONTENT)

    return Response(email_serialzer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def ForgotPasswordView(request):
    serializer_data = ForgotSerializers(data=request.data)

    if serializer_data.is_valid():
        email = serializer_data.validated_data["email"]
        otp = serializer_data.validated_data["otp"]
        new_password = serializer_data.validated_data["new_password"]

        cached_otp = cache.get(email)

        if cached_otp == otp:
            try:
                user = User.objects.get(email=email)

            except User.DoesNotExist:

                return Response(
                    {"error": "User Not Found"}, status=status.HTTP_404_NOT_FOUND
                )

            user.set_password(new_password)
            user.save()
            cache.delete(email)

            return Response(
                {"Message": "Forgot otp Successfull"}, status=status.HTTP_200_OK
            )
        return Response({"Message": "Invalid OTP "}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer_data.errors, status=status.HTTP_400_BAD_REQUEST)
