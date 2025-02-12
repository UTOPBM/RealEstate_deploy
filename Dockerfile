FROM python:3.9-slim-buster
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install gunicorn  # 👈 gunicorn 명시적으로 다시 설치! (기존 수정 사항 유지)
COPY . .
# 👈 요기!! app.py 를 실제 앱 파일 이름으로 확인!
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
EXPOSE 8080
CMD gunicorn --bind 0.0.0.0:8080 app:app  # 👈 CMD 명령어를 쉘 형식으로 변경! (JSON 배열 괄호 [] 제거)