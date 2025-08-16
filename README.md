# Chatto Backend

## 1. 가상환경 설정

```
# 가상 환경 생성
python -m venv .venv

# 맥에서 파이썬 못찾으면
python3 -m venv .venv

# Windows에서 터미널이 cmd라면
.venv\Scripts\activate.bat

# Windows에서 터미널이 git bash라면
source .venv/Scripts/activate

# Mac OS
source .venv/bin/activate
```

## 2. requirments.txt 파일 설치

```
pip install -r requirments.txt
```

## 3. 실행

```
python manage.py runserver
```

## DB가 수정된 경우

```
python manage.py makemigrations
python manage.py migrate
```

## Swagger에서 Token 입력 방식

```
Bearer ${access_token}

### ex
Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzE1OTYzOTk5LCJpYXQiOjE3MTU5NjIxOTksImp0aSI6IjU0YTkzNTA2NTIyYTQ5YmNiNTQyZjVlZDEwMGFiYmQ0IiwidXNlcl9pZCI6M30.EnsnJQGT86rN2aWz5QFFADVD0lIAIyC32jJ7rKigU1E
```

## gemini 사용하기 위한 명령어

```
pip install -U google-genai
```
