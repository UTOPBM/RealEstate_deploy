from dotenv import load_dotenv
load_dotenv()
import mysql.connector
import os

db_config = {  # MariaDB 접속 설정 (환경 변수 사용)
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'port': int(os.environ.get('DB_PORT')),
    'collation': 'utf8mb4_general_ci'  # collation 설정 추가
}

def create_table():
    conn = mysql.connector.connect(**db_config)  # MariaDB 연결
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS real_estate (
            id INT AUTO_INCREMENT PRIMARY KEY,
            aptDong TEXT,
            aptNm TEXT,
            buildYear INT,
            dealAmount VARCHAR(255),
            dealDay INT,
            dealMonth INT,
            dealYear INT,
            excluUseAr REAL,
            floor INT,
            sggCd VARCHAR(255),
            umdNm TEXT,
            reg_date VARCHAR(255)
        ) CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci  # 테이블 charset 및 collation 명시적 지정
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()
    print("데이터베이스 테이블 생성 완료.")