# /Users/kimjaehyeon/Desktop/프로젝트/부동산 프로젝트 재시작/Dockerfile

# Python 3.9 런타임 사용
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# Flask 앱 실행 (gunicorn 사용)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]