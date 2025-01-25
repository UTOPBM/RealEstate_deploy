from flask import Flask, render_template
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import os
from flask_cors import CORS  # flask-cors 추가

load_dotenv()

app = Flask(__name__)
CORS(app)  # 모든 경로에 대해 CORS 허용

# 데이터베이스 설정
db_config = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'port': int(os.environ.get('DB_PORT')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

# 법정동 코드 -> 구 이름 매핑 딕셔너리 (라우트 함수 위에 위치)
district_mapping = {
    '11110': '종로구',
    '11140': '중구',
    '11170': '용산구',
    '11200': '성동구',
    '11215': '광진구',
    '11230': '동대문구',
    '11260': '중랑구',
    '11290': '성북구',
    '11305': '강북구',
    '11320': '도봉구',
    '11350': '노원구',
    '11380': '은평구',
    '11410': '서대문구',
    '11440': '마포구',
    '11470': '양천구',
    '11500': '강서구',
    '11530': '구로구',
    '11545': '금천구',
    '11560': '영등포구',
    '11590': '동작구',
    '11620': '관악구',
    '11650': '서초구',
    '11680': '강남구',
    '11710': '송파구',
    '11740': '강동구'
}
def get_real_estate_data(limit=100):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute('''
            SELECT * FROM real_estate 
            ORDER BY dealYear DESC, dealMonth DESC, dealDay DESC
            LIMIT %s
        ''', (limit,))

        data = cursor.fetchall()
        print("Successfully connected to database and fetched data.")  # 성공 로그 추가
    except Error as e:
        print(f"Error while connecting to MariaDB: {e}")  # 에러 로그 상세하게 출력
        data = []  # 또는 적절한 에러 처리
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Database connection closed.")
    return data
def get_real_estate_data(limit=100):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT * FROM real_estate 
        ORDER BY dealYear DESC, dealMonth DESC, dealDay DESC
        LIMIT %s
    ''', (limit,))
    
    data = cursor.fetchall()
    conn.close()
    return data

@app.route('/')  # 단 한 번만 정의
def index():
    real_estate_data = get_real_estate_data(limit=100)
    return render_template(
        'index.html', 
        properties=real_estate_data,
        district_mapping=district_mapping  # 매핑 데이터 전달
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)