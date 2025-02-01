from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import os
from flask_cors import CORS
import datetime

load_dotenv()

app = Flask(__name__)
CORS(app)

# 데이터베이스 설정 (기존과 동일)
db_config = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'port': int(os.environ.get('DB_PORT')),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_general_ci'
}

# 법정동 코드 -> 구 이름 매핑 딕셔너리 (기존과 동일)
district_mapping = {
    '11680': '강남구',
    '11650': '서초구',
    '11710': '송파구',
    '11170': '용산구',
    '11200': '성동구',
    '11470': '양천구',
    '11560': '영등포구',
    '11110': '종로구',
    '11440': '마포구',
    '11590': '동작구',
    '11215': '광진구',
    '11740': '강동구',
    '11140': '중구',
    '11410': '서대문구',
    '11230': '동대문구',
    '11500': '강서구',
    '11290': '성북구',
    '11545': '금천구',
    '11620': '관악구',
    '11380': '은평구',
    '11530': '구로구',
    '11350': '노원구',
    '11305': '강북구',
    '11320': '도봉구',
    '11260': '중랑구'
}

def get_real_estate_data(q=None, min_price=None, max_price=None, start_date=None, end_date=None, limit=100, offset=0, sort_by='dealYear', sort_order='desc', column_filter=None, column_value=None):
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        query = '''
            SELECT *
            FROM real_estate
            WHERE 1=1
        '''
        params = []

        if q:
            sgg_codes = [code for code, district in district_mapping.items() if district == q]
            if sgg_codes:
                query += " AND sggCd IN ({})".format(','.join(['%s'] * len(sgg_codes)))
                params.extend(sgg_codes)

        if min_price:
            query += " AND CAST(REPLACE(SUBSTRING_INDEX(dealAmount, ',', 1), ',', '') AS UNSIGNED) >= %s"
            params.append(min_price)
        if max_price:
            query += " AND CAST(REPLACE(SUBSTRING_INDEX(dealAmount, ',', 1), ',', '') AS UNSIGNED) <= %s"
            params.append(max_price)

        if start_date:
            query += " AND STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') >= %s"
            params.append(start_date)
        if end_date:
            query += " AND STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') <= %s"
            params.append(end_date)

        # 컬럼 필터 조건 추가
        if column_filter and column_value:
            query += f" AND {column_filter} = %s"
            params.append(column_value)

        if sort_by == 'dealAmount':
            query += " ORDER BY CAST(REPLACE(SUBSTRING_INDEX(dealAmount, ',', 1), ',', '') AS UNSIGNED) {}".format(sort_order.upper())
        else:
            query += " ORDER BY {} {}".format(sort_by, sort_order.upper())

        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        print("Executing query:", query)
        print("With parameters:", params)
        cursor.execute(query, params)
        data = cursor.fetchall()
        print("Successfully fetched data.")
        
    except Error as e:
        print(f"Error while connecting to MariaDB or fetching data: {e}")
        data = []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("Database connection closed.")

    return data

@app.route('/api/search', methods=['GET'])
def api_search():
    q = request.args.get('q')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    sort_by = request.args.get('sort_by', 'dealYear')
    sort_order = request.args.get('sort_order', 'desc')
    column_filter = request.args.get('column_filter') # 컬럼 필터
    column_value = request.args.get('column_value') # 컬럼 필터 값

    real_estate_data = get_real_estate_data(q, min_price, max_price, start_date, end_date, limit, offset, sort_by, sort_order, column_filter, column_value)
    return jsonify(real_estate_data)

@app.route('/')
def index():
    real_estate_data = get_real_estate_data(limit=20)  # 기본 데이터 (limit=20으로 변경)
    return render_template('index.html', properties=real_estate_data, district_mapping=district_mapping)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
