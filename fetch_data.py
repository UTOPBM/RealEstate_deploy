# real_estate_crawler_modified.py
from dotenv import load_dotenv
load_dotenv()
import requests
import xml.etree.ElementTree as ET
import mysql.connector
from datetime import datetime
import os

# 환경변수 유효성 검사
def validate_environment():
    required_vars = ['DECODED_API_KEY', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_PORT']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        raise EnvironmentError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")

def safe_cast(value, to_type, default=None):
    """안전한 타입 변환 함수"""
    try:
        return to_type(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def fetch_and_store_data(lawd_cd, year, month): # year, month 파라미터 추가
    """지역 코드별 데이터 수집 및 저장 함수"""
    endpoint = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    decoded_api_key = os.environ['DECODED_API_KEY']
    deal_ymd = f"{year}{month:02d}" # 파라미터로 받은 year, month 사용

    # 페이징 처리
    page_no = 1
    total_inserted = 0

    try:
        conn = mysql.connector.connect(**{
            'host': os.environ['DB_HOST'],
            'user': os.environ['DB_USER'],
            'password': os.environ['DB_PASSWORD'],
            'database': os.environ['DB_NAME'],
            'port': int(os.environ['DB_PORT']),
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_general_ci'
        })
        cursor = conn.cursor()

        # Create a set to store unique record identifiers
        inserted_records = set()
        batch_data = []

        while True:
            params = {
                'serviceKey': decoded_api_key,
                'LAWD_CD': lawd_cd,
                'DEAL_YMD': deal_ymd,
                'numOfRows': '1000',
                'pageNo': str(page_no),
                'dataType': 'XML'
            }

            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            root = ET.fromstring(response.content)

            items = root.findall('.//item')
            if not items:
                break

            for item in items:
                # 거래 월 검증
                deal_year = safe_cast(item.findtext('dealYear'), int)
                deal_month = safe_cast(item.findtext('dealMonth'), int)
                deal_day = safe_cast(item.findtext('dealDay'), int)

                if deal_year != year or deal_month != month: # 파라미터로 받은 year, month 와 비교
                    continue

                if deal_day != day:
                    continue

                # 필드 추출 (기존 코드와 동일)
                apt_dong = item.findtext('aptDong')
                apt_nm = item.findtext('aptNm')
                build_year = safe_cast(item.findtext('buildYear'), int)
                deal_amount = safe_cast(item.findtext('dealAmount'), lambda x: x.replace(',', '')) if item.find('dealAmount') is not None else None
                deal_day = safe_cast(item.findtext('dealDay'), int)
                exclu_use_ar = safe_cast(item.findtext('excluUseAr'), float)
                floor = safe_cast(item.findtext('floor'), int)
                sgg_cd = item.findtext('sggCd')
                umd_nm = item.findtext('umdNm')

                # Create a unique identifier for the record
                record_id = f"{deal_year}-{deal_month}-{deal_day}-{sgg_cd}-{apt_nm}-{exclu_use_ar}-{floor}-{apt_dong}"

                # Check if the record has already been inserted
                if record_id not in inserted_records:
                    # Add the record to the set of inserted records
                    inserted_records.add(record_id)

                    batch_data.append((
                        apt_dong, apt_nm, build_year, deal_amount,
                        deal_day, deal_month, deal_year, exclu_use_ar,
                        floor, sgg_cd, umd_nm
                    ))

            # 다음 페이지 확인 (기존 코드와 동일)
            if len(items) < 1000:
                break
            page_no += 1

        # Execute batch insert
        if batch_data:
            cursor.executemany('''
                INSERT INTO real_estate (
                    aptDong, aptNm, buildYear, dealAmount,
                    dealDay, dealMonth, dealYear, excluUseAr,
                    floor, sggCd, umdNm
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', batch_data)
            conn.commit()
            total_inserted = len(batch_data)

        if total_inserted > 0:
            print(f"[성공] {lawd_cd} 지역 {year}-{month:02d}: {total_inserted}건 저장") # 로그 변경
        else:
            print(f"[성공] {lawd_cd} 지역 {year}-{month:02d}: 0건 저장")

    except Exception as e:
        print(f"[에러] {lawd_cd} 지역 {year}-{month:02d} 처리 실패: {str(e)}") # 로그 변경
        conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    validate_environment()

    gu_list = [
        '11110', '11140', '11170', '11200', '11215', '11230', '11260', '11290', '11305',
        '11320', '11350', '11380', '11410', '11440', '11470', '11500', '11530', '11545',
        '11560', '11590', '11620', '11650', '11680', '11710', '11740'
    ]

    start_year = 2019
    now = datetime.now()
    current_year = now.year
    current_month = now.month

    print(f"▦▦▦ 오늘({current_year}년 {current_month}월) 아파트 실거래가 수집 시작 ▦▦▦") # 시작 메시지 변경

    year = current_year
    month = current_month
    day = now.day

    print(f"▶▶▶ {year}년 {month}월 {day}일 데이터 수집 시작") # 월별 시작 메시지 추가
    for gu_code in gu_list:
        fetch_and_store_data(gu_code, year, month) # year, month 파라미터 전달
    print(f"◀◀◀ {year}년 {month}월 {day}일 데이터 수집 완료") # 월별 완료 메시지 추가

    print("▦▦▦ 오늘 데이터 수집 완료 ▦▦▦") # 완료 메시지 변경
