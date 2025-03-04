from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error
import os
from flask_cors import CORS
import datetime
from datetime import timedelta
import json

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

def format_price(amount):
    amount = int(amount.replace(',', ''))
    billion = amount // 10000
    million = amount % 10000
    result = ''
    if billion > 0:
        result += f'{billion}억 '
    if million > 0:
        result += f'{million:,}만원'
    elif billion > 0:
        result += '원'
    return result

def parse_price(price_str):
    # 모든 쉼표 제거
    price_str = price_str.replace(',', '')
    
    # '억'과 '만원' 처리
    total = 0
    if '억' in price_str:
        parts = price_str.split('억')
        total = int(parts[0].strip()) * 10000
        if len(parts) > 1 and parts[1].strip() and '만원' in parts[1]:
            total += int(parts[1].replace('만원', '').strip())
    else:
        total = int(price_str.replace('만원', '').replace('원', '').strip())
    
    return total

def calculate_price_change(cursor, apt_nm, exclu_use_ar, deal_amount, deal_date):
    periods = [
        (90, "3개월"),
        (180, "6개월"),
        (365, "1년"),
        (730, "2년"),
        (1095, "3년")
    ]
    try:
        current_amount = parse_price(deal_amount)
        deal_date = datetime.datetime.strptime(deal_date, '%Y-%m-%d')
        changes = []
        
        for days, period_name in periods:
            start_date = deal_date - timedelta(days=days)
            
            cursor.execute("""
                SELECT 
                    dealAmount,
                    STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') as deal_date
                FROM real_estate
                WHERE aptNm = %s 
                AND excluUseAr = %s
                AND STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') 
                    BETWEEN %s AND %s
                ORDER BY ABS(DATEDIFF(
                    STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d'),
                    %s
                )) ASC
                LIMIT 1
            """, (apt_nm, exclu_use_ar, start_date.strftime('%Y-%m-%d'), deal_date.strftime('%Y-%m-%d'), start_date.strftime('%Y-%m-%d')))
            
            result = cursor.fetchone()
            if result:
                old_amount = float(result['dealAmount'].replace(',', ''))
                percent_change = ((current_amount - old_amount) / old_amount) * 100
                amount_change = current_amount - old_amount
                old_date = result['deal_date'].strftime('%Y-%m-%d')
                
                change_class = 'price-increase' if percent_change > 0 else 'price-decrease'
                sign = '+' if percent_change > 0 else ''
                
                changes.append(f'<span class="price-change-period">{period_name}: {old_date}<br>'
                             f'<span class="{change_class}">{format_price(str(int(old_amount)))} → {format_price(str(int(current_amount)))}<br>'
                             f'{sign}{percent_change:.1f}% ({sign}{format_price(str(abs(int(amount_change))))})</span></span>')
            else:
                changes.append(f'<span class="price-change-period">{period_name}: 데이터 없음</span>')
        
        return '<div class="price-change-cell">' + ''.join(changes) + '</div>' if changes else '-'
    except Exception as e:
        print(f"Error in calculate_price_change: {e}")
        return '-'
    
    return '-'

def get_real_estate_data(q=None, min_price=None, max_price=None, start_date=None, end_date=None, limit=100, offset=0, sort_by='dealYear', sort_order='desc', **kwargs):
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

        # 필터 파라미터 처리
        for key, value in kwargs.items():
            if key.startswith('filter_') and value:
                column = key.replace('filter_', '')
                if column == 'district':
                    query += " AND sggCd IN (SELECT sggCd FROM real_estate WHERE %s = %s)"
                    params.extend([column, value])
                elif column == 'dealDate':
                    year, month, day = value.split('-')
                    query += " AND dealYear = %s AND dealMonth = %s AND dealDay = %s"
                    params.extend([year, month, day])
                else:
                    query += f" AND {column} = %s"
                    params.append(value)

        if sort_by == 'dealAmount':
            query += " ORDER BY CAST(REPLACE(SUBSTRING_INDEX(dealAmount, ',', 1), ',', '') AS UNSIGNED) {}".format(sort_order.upper())
        else:
            query += " ORDER BY STR_TO_DATE(reg_date, '%Y-%m-%d') DESC, dealYear DESC, dealMonth DESC, dealDay DESC"

        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        data = cursor.fetchall()
        
        # Format the data
        for row in data:
            row['dealAmount'] = format_price(row['dealAmount'])
        
        return data
        
    except Error as e:
        print(f"Error while connecting to MariaDB or fetching data: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/search', methods=['GET'])
def api_search():
    # 기본 파라미터 추출
    q = request.args.get('q')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    sort_by = request.args.get('sort_by', 'dealYear')
    sort_order = request.args.get('sort_order', 'desc')

    # 필터 파라미터 추출
    filter_params = {
        key: value for key, value in request.args.items()
        if key.startswith('filter_') and value
    }

    real_estate_data = get_real_estate_data(
        q=q,
        min_price=min_price,
        max_price=max_price,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        **filter_params
    )
    return jsonify(real_estate_data)

@app.route('/api/apartment-search')
def apartment_search():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])

    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        # 아파트 이름으로 검색하여 고유한 아파트와 면적 조합 찾기
        cursor.execute("""
            SELECT DISTINCT aptNm, excluUseAr
            FROM real_estate
            WHERE aptNm LIKE %s
            ORDER BY aptNm, excluUseAr
            LIMIT 10
        """, (f"%{query}%",))
        
        results = cursor.fetchall()
        return jsonify(results)

    except Error as e:
        print(f"Error while searching apartments: {e}")
        return jsonify([])
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/price-changes')
def price_changes():
    apartments = request.args.get('apartments', '[]')
    period_days = int(request.args.get('period', 1095))  # Default to 3 years (1095 days)
    if period_days > 1095:  # 최대 3년
        period_days = 1095
    conn = None
    cursor = None
    
    try:
        apartments = json.loads(apartments)
        if not apartments:
            return jsonify([])

        end_date = datetime.datetime.now()
        #start_date = end_date - timedelta(days=period_days)
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        results = []
        for apt in apartments:
            apt_data = json.loads(apt)
            
            price_changes_info = {}
            
            #Calculate for different periods.
            periods = {
                '1주': 7,
                '2주': 14,
                '1달': 30,
                '3달': 90,
                '6개월': 180,
                '1년': 365,
                '2년': 730,
                '3년': 1095,
            }

            for period_name, days in periods.items():
                start_date = end_date - timedelta(days=days)
                 # 특정 아파트와 면적에 대한 거래 기록 조회
                cursor.execute("""
                    SELECT 
                        dealAmount,
                        STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') as deal_date
                    FROM real_estate
                    WHERE aptNm = %s 
                    AND excluUseAr = %s
                    AND STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') 
                        BETWEEN %s AND %s
                    ORDER BY deal_date
                """, (apt_data['aptNm'], apt_data['excluUseAr'], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

                prices = cursor.fetchall()
                
                #find the nearest price
                closest_price = None
                closest_diff = float('inf')
                for price in prices:
                    diff = abs((end_date - price['deal_date']).days - days)
                    if diff < closest_diff:
                        closest_diff = diff
                        closest_price = price

                current_price_query = """
                SELECT dealAmount,
                    STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') as deal_date
                    FROM real_estate
                    WHERE aptNm = %s 
                    AND excluUseAr = %s
                    ORDER BY deal_date DESC
                    LIMIT 1
                """

                cursor.execute(current_price_query, (apt_data['aptNm'], apt_data['excluUseAr']))
                current_price_result = cursor.fetchone()

                if current_price_result and closest_price:
                    current_price = float(current_price_result['dealAmount'].replace(',', ''))
                    old_price = float(closest_price['dealAmount'].replace(',', ''))
                    
                    if old_price != 0:
                      percent_change = ((current_price - old_price) / old_price) * 100
                    else :
                      percent_change = 0

                    price_changes_info[period_name] = {
                       'percent_change' : round(percent_change, 1),
                       'old_price' : old_price,
                       'old_date' : closest_price['deal_date'].strftime('%Y-%m-%d'),
                       'current_price' : current_price,
                       'current_date' : current_price_result['deal_date'].strftime('%Y-%m-%d')
                    }
                else:
                  price_changes_info[period_name] = {
                       'percent_change' : None,
                       'old_price' : None,
                       'old_date' : None,
                       'current_price' : None,
                       'current_date' : None
                    }

            results.append({
                'aptNm': apt_data['aptNm'],
                'excluUseAr': apt_data['excluUseAr'],
                'price_changes' : price_changes_info
            })
        
        return jsonify(results)

    except Error as e:
        print(f"Error while fetching price changes: {e}")
        return jsonify([])
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
    apartments = request.args.get('apartments', '[]')
    period_days = int(request.args.get('period', 30))
    if period_days > 1095:  # 최대 3년
        period_days = 1095
    conn = None
    cursor = None
    
    try:
        apartments = json.loads(apartments)
        if not apartments:
            return jsonify([])

        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        results = []
        for apt in apartments:
            apt_data = json.loads(apt)
            
            # 특정 아파트와 면적에 대한 거래 기록 조회
            cursor.execute("""
                SELECT 
                    dealAmount,
                    STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') as deal_date
                FROM real_estate
                WHERE aptNm = %s 
                AND excluUseAr = %s
                AND STR_TO_DATE(CONCAT(dealYear, '-', LPAD(dealMonth, 2, '0'), '-', LPAD(dealDay, 2, '0')), '%Y-%m-%d') 
                    BETWEEN %s AND %s
                ORDER BY deal_date
            """, (apt_data['aptNm'], apt_data['excluUseAr'], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            
            prices = cursor.fetchall()
            results.append({
                'aptNm': apt_data['aptNm'],
                'excluUseAr': apt_data['excluUseAr'],
                'prices': [{
                    'amount': float(price['dealAmount'].replace(',', '')),
                    'date': price['deal_date'].strftime('%Y-%m-%d')
                } for price in prices]
            })
        
        return jsonify(results)

    except Error as e:
        print(f"Error while fetching price changes: {e}")
        return jsonify([])
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/api/price-change', methods=['GET'])
def get_price_change():
    apt_nm = request.args.get('apt_nm')
    exclu_use_ar = request.args.get('exclu_use_ar')
    deal_amount = request.args.get('deal_amount')
    deal_date = request.args.get('deal_date')
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        
        price_change = calculate_price_change(cursor, apt_nm, float(exclu_use_ar), deal_amount, deal_date)
        return jsonify({'priceChange': price_change})
        
    except Error as e:
        print(f"Error while fetching price change: {e}")
        return jsonify({'priceChange': '-'})
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/')
def index():
    real_estate_data = get_real_estate_data(limit=20)  # 기본 데이터 (limit=20으로 변경)
    return render_template('index.html', properties=real_estate_data, district_mapping=district_mapping)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080)) # ✅ PORT 환경 변수 값 사용, 없으면 8080 기본값
    app.run(host='0.0.0.0', port=port, debug=True) # ✅ 수정된 port 변수 사용
