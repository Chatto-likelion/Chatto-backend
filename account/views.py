from django.shortcuts import render

# Create your views here.
from django.contrib.auth.models import User
from django.contrib import auth
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import login

from account.request_serializers import SignInRequestSerializer, SignUpRequestSerializer, ProfileEditRequestSerializer

from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import logout

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.authentication import SessionAuthentication


from .serializers import (
    UserSerializer,
    UserProfileSerializer,
)
from .models import UserProfile


class SignUpView(APIView):
    @swagger_auto_schema(
        operation_id="회원가입",
        operation_description="회원가입을 진행합니다.",
        request_body=SignUpRequestSerializer,
        responses={201: UserProfileSerializer, 400: "Bad Request"},
    )
    def post(self, request):

        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid(raise_exception=True):
            user = User.objects.create_user(
                username = request.data.get("username"),
                email = request.data.get("email"),
                password = request.data.get("password"),
            )
    

        phone = request.data.get("phone")

        user_profile = UserProfile.objects.create(
            user=user, point=0, phone=phone
        )
        user_profile_serializer = UserProfileSerializer(instance=user_profile)
        return Response(user_profile_serializer.data, status=status.HTTP_201_CREATED)


class LogInView(APIView):
    @swagger_auto_schema(
        operation_id="로그인",
        operation_description="로그인을 진행합니다.",
        request_body=SignInRequestSerializer,
        responses={200: UserProfileSerializer, 404: "Not Found", 400: "Bad Request"},
    )
    def post(self, request):
        # query_params 에서 username, password를 가져온다.
        username = request.data.get("username")
        password = request.data.get("password")
        if username is None or password is None:
            return Response(
                {"message": "missing fields ['username', 'password'] in query_params"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user = User.objects.get(username=username)
            if not user.check_password(password):
                return Response(
                    {"message": "Password is incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            login(request, user)
            user_profile = UserProfile.objects.get(user=user)
            user_profile_serializer = UserProfileSerializer(instance=user_profile)
            return Response(user_profile_serializer.data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response(
                {"message": "User does not exist"}, status=status.HTTP_404_NOT_FOUND
            )


class LogoutView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="로그아웃",
        operation_description="로그아웃을 진행합니다.",
        responses={200: UserSerializer, 401: "Unauthorized"},
        security=[{'SessionCookie': []}], 
    )
    def post(self, request):

        if not request.user:
            return Response(
                {"detail": "인증자격 없음."},
                status = status.HTTP_401_UNAUTHORIZED
            )
        
        user = request.user
        data = UserSerializer(instance=user).data
        logout(request)
        response = Response(data, status=status.HTTP_200_OK)
        response.delete_cookie('sessionid')
        return response
    

class ProfileView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id="프로필 조회",
        operation_description="로그인한 사용자의 프로필을 조회합니다.",
        responses={200: UserProfileSerializer, 400: "Bad_Request", 401: "Unauthorized", 404: "Not_Found"},
    )
    def get(self, request, user_id):
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            user_profile_serializer = UserProfileSerializer(instance=user_profile)
            return Response(user_profile_serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"message": "UserProfile does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
    @swagger_auto_schema(
        operation_id = "프로필수정",
        operation_description = "로그인한 사용자의 프로필을 수정합니다.",
        request_body = ProfileEditRequestSerializer,
        responses={200: UserProfileSerializer, 400: "Bad_Request", 401: "Unauthorized", 404: "Not_Found"},
    )
    def put(self, request, user_id):
        user_profile = UserProfile.objects.get(user_id=user_id)
        user = User.objects.get(id=user_id)
        if not user:
            return Response(
                {"message": "User does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not user_profile:
            return Response(
                {"message": "UserProfile does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        user.username = request.data.get("username")
        user.email = request.data.get("email")
        user.set_password(request.data.get("password"))
        user_profile.phone = request.data.get("phone")
        user_profile.save()
        user.save()

        user_profile_serializer = UserProfileSerializer(instance=user_profile)
        return Response(user_profile_serializer.data, status=status.HTTP_200_OK)
