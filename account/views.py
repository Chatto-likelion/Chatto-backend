from django.shortcuts import render

# Create your views here.
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth import login

from account.request_serializers import SignInRequestSerializer, SignUpRequestSerializer, ProfileEditRequestSerializer, TokenRefreshRequestSerializer

from .serializers import (
    UserSerializer,
    UserProfileSerializer,
)
from .models import UserProfile

from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework_simplejwt.views import TokenRefreshView


def set_token_on_response_cookie(user, status_code):
    token = RefreshToken.for_user(user)
    user_profile = UserProfile.objects.get(user=user)
    serialized_data = UserProfileSerializer(instance=user_profile).data
    response = Response(serialized_data, status=status_code)
    response.set_cookie("refresh_token", value = str(token), httponly=True)
    response.set_cookie("access_token", value = str(token.access_token), httponly=True)
    return response


class SignUpView(APIView):
    @swagger_auto_schema(
        operation_id="회원가입",
        operation_description="회원가입을 진행합니다.",
        request_body=SignUpRequestSerializer,
        responses={201: UserProfileSerializer, 400: "Bad Request"},
    )
    def post(self, request):
        user_serializer = UserSerializer(data=request.data)
        if user_serializer.is_valid() and request.data.get("password") == request.data.get("password_confirm"):
            user = User.objects.create_user(
                username = request.data.get("username"),
                email = request.data.get("email"),
                password = request.data.get("password"),
            )
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        user_profile = UserProfile.objects.create(
            user=user, 
            point=0, 
            phone=request.data.get("phone")
        )

        user_profile_serializer = UserProfileSerializer(instance=user_profile)
        return Response(user_profile_serializer.data, status=status.HTTP_201_CREATED)


class LogInView(APIView):
    @swagger_auto_schema(
        operation_id="로그인",
        operation_description="로그인을 진행합니다.",
        request_body=SignInRequestSerializer,
        responses={200: UserProfileSerializer, 400: "Bad Request", 404: "Not Found"},
    )
    def post(self, request):
        if not SignInRequestSerializer(data=request.data).is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(username=request.data.get("username"))
            if not user.check_password(request.data.get("password")):
                return Response(status=status.HTTP_400_BAD_REQUEST,)
            response = set_token_on_response_cookie(user, status.HTTP_200_OK)
            return response

        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class LogOutView(APIView):
    @swagger_auto_schema(
        operation_id="로그아웃",
        operation_description="로그아웃합니다.",
        request_body=TokenRefreshRequestSerializer,
        responses={204: "No Content", 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        if not TokenRefreshRequestSerializer(data=request.data).is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
        except:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class ProfileView(APIView):
    @swagger_auto_schema(
        operation_id="프로필 조회",
        operation_description="로그인한 사용자의 프로필을 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: UserProfileSerializer, 401: "Unauthorized", 404: "Not Found"},
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        try:
            user_profile = UserProfile.objects.get(user=author)
            user_profile_serializer = UserProfileSerializer(instance=user_profile)
            return Response(user_profile_serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
    @swagger_auto_schema(
        operation_id = "프로필수정",
        operation_description = "로그인한 사용자의 프로필을 수정합니다.",
        request_body = ProfileEditRequestSerializer,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: UserProfileSerializer, 400: "Bad Request", 401: "Unauthorized", 404: "Not Found"},
    )
    def put(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        user_profile = UserProfile.objects.get(user=author)
        user = author
        if not user_profile:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        user.username = request.data.get("username")
        user.email = request.data.get("email")
        user.set_password(request.data.get("password"))
        user_profile.phone = request.data.get("phone")
        user_profile.save()
        user.save()

        user_profile_serializer = UserProfileSerializer(instance=user_profile)
        return Response(user_profile_serializer.data, status=status.HTTP_200_OK)

class TokenRefreshView(APIView):
    @swagger_auto_schema(
        operation_id="토큰 재발급",
        operation_description="access 토큰을 재발급 받습니다.",
        request_body=TokenRefreshRequestSerializer,
        responses={200: UserProfileSerializer},
    )
    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            RefreshToken(refresh_token).verify()
        except:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
            
        new_access_token = str(RefreshToken(refresh_token).access_token)
        response = Response({"detail": "token refreshed"}, status=status.HTTP_200_OK)
        response.set_cookie("access_token", value=str(new_access_token), httponly=True)
        return response