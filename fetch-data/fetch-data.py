import os
import requests
import mysql.connector
from datetime import datetime, timezone
import functions_framework
import xml.etree.ElementTree as ET  # defusedxml 제거 후 원래대로 복원
from xml.etree.ElementTree import fromstring, ParseError  # 추가

# 환경변수 유효성 검사 함수
def validate_environment():
    required_vars = ['DECODED_API_KEY', 'DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'DB_PORT']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        raise EnvironmentError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")

# 안전한 타입 변환 함수
def safe_cast(value, to_type, default=None):
    try:
        return to_type(value) if value is not None else default
    except (ValueError, TypeError):
        return default

# 데이터 수집 및 DB 저장 함수
def fetch_and_store_data(lawd_cd, current_year, current_month):
    print(f"fetch_and_store_data 호출: lawd_cd={lawd_cd}, current_year={current_year}, current_month={current_month}")  # 디버깅 로그
    endpoint = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    decoded_api_key = os.environ['DECODED_API_KEY']
    deal_ymd = f"{current_year}{current_month:02d}"
    page_no = 1
    total_inserted = 0

    # MySQL 데이터베이스 연결
    conn = None  # conn 변수 초기화
    try:
        conn = mysql.connector.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            port=int(os.environ['DB_PORT']),
            charset='utf8mb4',
            collation='utf8mb4_general_ci'
        )
        cursor = conn.cursor()
        
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
            try: # 수정
                root = ET.fromstring(response.content)
            except ParseError as e:
                print(f"XML 파싱 에러: {e}")
                try:
                    from xml.etree.ElementTree import XMLParser
                    parser = XMLParser(encoding='utf-8')
                    root = fromstring(response.content, parser=parser)
                except Exception as inner_e:
                    print(f"SimpleXMLTreeBuilder 사용 실패: {inner_e}")
                    return f"[에러] {lawd_cd} 지역 처리 실패: XML 파싱 실패"
            items = root.findall('.//item')
            if not items:
                print("No items found, breaking loop")  # 디버깅 로그
                break
            for item in items:
                # 거래 연도/월 확인
                deal_year = safe_cast(item.findtext('dealYear'), int)
                deal_month = safe_cast(item.findtext('dealMonth'), int)

                print(f"API에서 받은 deal_year: {deal_year}, deal_month: {deal_month}")  # 디버깅 로그

                if deal_year != current_year or deal_month != current_month:
                    print(f"필터링됨: deal_year={deal_year}, deal_month={deal_month}, current_year={current_year}, current_month={current_month}")  # 디버깅 로그
                    continue
                apt_dong = item.findtext('aptDong')
                apt_nm = item.findtext('aptNm')
                build_year = safe_cast(item.findtext('buildYear'), int)
                deal_amount = safe_cast(item.findtext('dealAmount'), lambda x: x.replace(',', '')) if item.find('dealAmount') is not None else None
                deal_day = safe_cast(item.findtext('dealDay'), int)
                exclu_use_ar = safe_cast(item.findtext('excluUseAr'), float)
                floor_val = safe_cast(item.findtext('floor'), int)
                sgg_cd = item.findtext('sggCd')
                umd_nm = item.findtext('umdNm')
                # 중복 데이터 검사
                cursor.execute('''
                    SELECT 1 FROM real_estate
                    WHERE dealYear = %s AND dealMonth = %s AND dealDay = %s
                    AND sggCd = %s AND aptNm = %s AND excluUseAr = %s
                    AND floor = %s AND aptDong = %s
                    LIMIT 1
                ''', (deal_year, deal_month, deal_day, sgg_cd, apt_nm, exclu_use_ar, floor_val, apt_dong))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO real_estate (
                            aptDong, aptNm, buildYear, dealAmount,
                            dealDay, dealMonth, dealYear, excluUseAr,
                            floor, sggCd, umdNm
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (apt_dong, apt_nm, build_year, deal_amount,
                          deal_day, deal_month, deal_year, exclu_use_ar,
                          floor_val, sgg_cd, umd_nm))
                    total_inserted += 1
            if len(items) < 1000:
                break
            page_no += 1
        conn.commit()
        return f"[성공] {lawd_cd} 지역: {total_inserted}건 저장"
    except Exception as e:
        if conn:
            conn.rollback()
        return f"[에러] {lawd_cd} 지역 처리 실패: {str(e)}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# Cloud Run Functions의 HTTP 진입점 함수
@functions_framework.http
def cloud_run_entry(request):
    """
    이 함수는 Cloud Run Functions에서 HTTP 요청을 받았을 때 호출되어
    데이터 수집/저장 로직을 수행한 후 결과를 반환합니다.
    """
    try:
        # 환경변수 유효성 검사
        validate_environment()

        # 처리할 지역(gu) 코드 리스트 (예제)
        gu_list = [
            '11110', '11140', '11170', '11200', '11215', '11230', '11260',
            '11290', '11305', '11320', '11350', '11380', '11410', '11440',
            '11470', '11500', '11530', '11545', '11560', '11590', '11620',
            '11650', '11680', '11710', '11740'
        ]

        # UTC 기준으로 현재 년도와 월을 가져옵니다.
        now = datetime.now(timezone.utc)
        current_year = now.year
        current_month = now.month

        print(f"cloud_run_entry: current_year={current_year}, current_month={current_month}")  # 디버깅 로그

        responses = []
        for gu_code in gu_list:
            print(f"cloud_run_entry: gu_code={gu_code}")  # 디버깅 로그
            result = fetch_and_store_data(gu_code, current_year, current_month)
            responses.append(result)
            
        # 모든 처리 결과를 HTTP 응답으로 반환
        return "\n".join(responses)
    except Exception as ex:
        print(f"cloud_run_entry 에러: {ex}")  # 디버깅 로그
        return f"Error: {ex}", 500