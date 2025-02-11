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

def create_database_if_not_exists():
    """데이터베이스가 없으면 생성하는 함수"""
    db_config_no_db = db_config.copy() # database 정보 제외한 설정 복사
    db_name = db_config_no_db.pop('database') # database 정보 따로 저장하고 설정에서 제거

    conn = None  # conn 변수를 None으로 초기화
    try:
        conn = mysql.connector.connect(**db_config_no_db) # database 정보 없이 연결
        cursor = conn.cursor()

        print(f"Database name to create: {db_name}") # 추가: 데이터베이스 이름 확인 출력

        # CHARACTER SET 및 COLLATE 제거하고 기본 데이터베이스 생성 시도
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        conn.commit()
        print(f"데이터베이스 '{db_name}'가 생성되었거나 이미 존재합니다.")

    except mysql.connector.Error as err:
        print(f"데이터베이스 생성 실패: {err}")
    finally:
        if conn:
            conn.close()

def create_table():
    conn = mysql.connector.connect(**db_config)  # MariaDB 연결 (이제 DB가 있다고 가정)
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
            reg_date VARCHAR(255),
            INDEX idx_real_estate (dealYear, dealMonth, dealDay, sggCd, aptNm, excluUseAr, floor, aptDong)
        ) CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci  # 테이블 charset 및 collation 명시적 지정
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_database_if_not_exists() # 데이터베이스 생성 함수 먼저 호출
    create_table()
    print("데이터베이스 테이블 생성 완료.")
