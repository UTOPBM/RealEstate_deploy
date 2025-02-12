# remove_duplicates.py
from dotenv import load_dotenv
load_dotenv()
import mysql.connector
import os

db_config = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'port': int(os.environ.get('DB_PORT')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

def remove_duplicate_data():
    """중복 데이터 삭제 함수"""
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # 중복 데이터 찾기 (id가 가장 작은 레코드를 제외하고)
        cursor.execute('''
            DELETE FROM real_estate
            WHERE id NOT IN (
                SELECT min_id
                FROM (
                    SELECT MIN(id) as min_id
                    FROM real_estate
                    GROUP BY dealYear, dealMonth, dealDay, sggCd, aptNm, excluUseAr, floor, aptDong
                ) as tmp
            )
        ''')

        conn.commit()
        print(f"[성공] 중복 데이터 {cursor.rowcount}건 삭제 완료")

    except Exception as e:
        print(f"[에러] 중복 데이터 삭제 실패: {str(e)}")
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    remove_duplicate_data()