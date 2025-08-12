from django.shortcuts import render

# Create your views here.
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from account.request_serializers import(
    SignInRequestSerializer, 
    SignUpRequestSerializer, 
    ProfileEditRequestSerializer, 
    TokenRefreshRequestSerializer,
    CreditPurchaseRequestSerializer,
    CreditUsageRequestSerializer,
)

from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    CreditPurchaseSerializer,
    CreditUsageSerializer,
)
from .models import (
    UserProfile,
    CreditPurchase,
    CreditUsage,
)

from rest_framework_simplejwt.tokens import RefreshToken



def set_token_on_response_cookie(user, status_code):
    token = RefreshToken.for_user(user)
    user_profile = UserProfile.objects.get(user=user)
    serialized_data = UserProfileSerializer(instance=user_profile).data
    response = Response(serialized_data, status=status_code)
    response.set_cookie("refresh_token", value = str(token))
    response.set_cookie("access_token", value = str(token.access_token))
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

        UserProfile.objects.create(
            user=user, 
            point=0, 
            phone=request.data.get("phone")
        )

        response = set_token_on_response_cookie(user, status.HTTP_201_CREATED)
        return response


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
        response.set_cookie("access_token", value=str(new_access_token))
        return response
    

class CreditPurchaseView(APIView):
    @swagger_auto_schema(
        operation_id="크레딧 구매",
        operation_description="크레딧을 구매합니다.",
        request_body=CreditPurchaseRequestSerializer,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={201: CreditPurchaseSerializer, 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        serializer = CreditPurchaseRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(status=status.HTTP_400_BAD_REQUEST)

        credit_purchase = CreditPurchase.objects.create(
            user=author,
            amount=serializer.validated_data["amount"],
            payment=serializer.validated_data["payment"],
        )

        user_profile = UserProfile.objects.get(user=author)
        
        user_profile.credit += serializer.validated_data["amount"]
        user_profile.save()

        serializer = CreditPurchaseSerializer(instance=credit_purchase)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_id="크레딧 구매 내역 조회",
        operation_description="로그인한 사용자의 크레딧 구매 내역을 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: CreditPurchaseSerializer(many=True), 401: "Unauthorized"},
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        credit_purchases = CreditPurchase.objects.filter(user=author)
        serializer = CreditPurchaseSerializer(instance=credit_purchases, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class CreditUsageView(APIView):
    @swagger_auto_schema(
        operation_id="크레딧 사용",
        operation_description="크레딧을 사용합니다.",
        request_body=CreditUsageRequestSerializer,
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={201: CreditUsageSerializer, 400: "Bad Request", 401: "Unauthorized"},
    )
    def post(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        serializer = CreditUsageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "wrong request format"}, status=status.HTTP_400_BAD_REQUEST)

        user_profile = UserProfile.objects.get(user=author)
        
        if user_profile.credit < serializer.validated_data["amount"]:
            return Response({"detail": "Insufficient credit"}, status=status.HTTP_400_BAD_REQUEST)

        user_profile.credit -= serializer.validated_data["amount"]
        user_profile.save()

        credit_usage = CreditUsage.objects.create(
            user=author,
            amount=serializer.validated_data["amount"],
            usage=serializer.validated_data["usage"],
            purpose=serializer.validated_data["purpose"],
        )

        serializer = CreditUsageSerializer(instance=credit_usage)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        operation_id="크레딧 사용 내역 조회",
        operation_description="크레딧 사용 내역을 조회합니다.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER, 
                description="access token", 
                type=openapi.TYPE_STRING),
        ],
        responses={200: CreditUsageSerializer, 401: "Unauthorized"},
    )
    def get(self, request):
        author = request.user
        if not author.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        credit_usages = CreditUsage.objects.filter(user=author)
        serializer = CreditUsageSerializer(instance=credit_usages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

