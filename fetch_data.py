from dotenv import load_dotenv
load_dotenv()
import requests
import xml.etree.ElementTree as ET
import mysql.connector
from datetime import datetime
import os

decoded_api_key = os.environ.get('DECODED_API_KEY') # 환경 변수에서 API 키 로드

db_config = {  # MariaDB 접속 설정 (환경 변수 사용)
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'database': os.environ.get('DB_NAME'),
    'port': int(os.environ.get('DB_PORT')),
    'collation': 'utf8mb4_general_ci'  # collation 설정 추가 (fetch_data.py에도 추가!)
}

def fetch_and_store_data(lawd_cd, deal_ymd):

    endpoint = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
    params = {
        'serviceKey': decoded_api_key,
        'LAWD_CD': lawd_cd,
        'DEAL_YMD': deal_ymd,
        'numOfRows': '1000',
        'pageNo': '1',
        'dataType': 'XML'
    }

    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.text)

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        now = datetime.now().strftime('%Y-%m-%d')

        for item in root.findall('.//item'):
            aptDong = item.find('aptDong').text if item.find('aptDong') is not None else None
            aptNm = item.find('aptNm').text if item.find('aptNm') is not None else None
            buildYear = int(item.find('buildYear').text) if item.find('buildYear') is not None and item.find('buildYear').text.isdigit() else None
            dealAmount = item.find('dealAmount').text.replace(',', '').strip() if item.find('dealAmount') is not None else None
            dealDay = int(item.find('dealDay').text) if item.find('dealDay') is not None and item.find('dealDay').text.isdigit() else None
            dealMonth = int(item.find('dealMonth').text) if item.find('dealMonth') is not None and item.find('dealMonth').text.isdigit() else None
            dealYear = int(item.find('dealYear').text) if item.find('dealYear') is not None and item.find('dealYear').text.isdigit() else None
            excluUseAr = float(item.find('excluUseAr').text) if item.find('excluUseAr') is not None else None
            floor = int(item.find('floor').text) if item.find('floor') is not None and item.find('floor').text.isdigit() else None
            sggCd = item.find('sggCd').text if item.find('sggCd') is not None else None
            umdNm = item.find('umdNm').text if item.find('umdNm') is not None else None

            try:
                insert_query = '''
                    INSERT INTO real_estate (aptDong, aptNm, buildYear, dealAmount, dealDay, dealMonth, dealYear, excluUseAr, floor, sggCd, umdNm)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                insert_data = (aptDong, aptNm, buildYear, dealAmount, dealDay, dealMonth, dealYear, excluUseAr, floor, sggCd, umdNm)

                cursor.execute('''
                    SELECT 1
                    FROM real_estate
                    WHERE dealYear = %s AND dealMonth = %s AND dealDay = %s AND sggCd = %s AND aptNm = %s AND excluUseAr = %s AND floor = %s
                ''', (dealYear, dealMonth, dealDay, sggCd, aptNm, excluUseAr, floor))
                duplicate_check_result = cursor.fetchall()

                print(f"중복 확인 쿼리 파라미터: dealYear={dealYear}, dealMonth={dealMonth}, dealDay={dealDay}, sggCd={sggCd}, aptNm={aptNm}, excluUseAr={excluUseAr}, floor={floor}") # 파라미터 로그 출력
                if not duplicate_check_result: # fetchall() 결과를 사용하여 중복 데이터 확인
                    cursor.execute(insert_query, insert_data)
                    print(f"데이터 삽입: {aptNm}, {dealYear}-{dealMonth}-{dealDay}")
                else:
                    print(f"중복 데이터 존재: {aptNm}, {dealYear}-{dealMonth}-{dealDay}")
            except Exception as insert_e:
                print(f"데이터 삽입 쿼리 오류: {insert_e}, 쿼리: {insert_query}, 데이터: {insert_data}")
                item_str = ET.tostring(item, encoding='unicode') # ET.tostring 결과를 변수에 저장
                print(f"오류 발생 item: {item_str}") # 변수를 print 함수에 사용

            except Exception as e:
                print(f"데이터 처리 오류: {e}, 데이터: {ET.tostring(item, encoding='unicode')}") # 오류 메시지 변경

        try:
            conn.commit()
            print(f"{lawd_cd} 코드, {deal_ymd} 데이터 저장 완료.")
        except Exception as commit_e:
            print(f"커밋 오류: {commit_e}") # 커밋 오류 로깅
        finally:
            conn.close()

    except requests.exceptions.RequestException as req_e:
        print(f"API 호출 중 오류 발생: {req_e}")
    except ET.ParseError as parse_e:
        print(f"XML 파싱 오류 발생: {parse_e}")

if __name__ == "__main__":
    gu_list = [
        '11110', '11140', '11170', '11200', '11215', '11230', '11260', '11290', '11305',
        '11320', '11350', '11380', '11410', '11440', '11470', '11500', '11530', '11545',
        '11560', '11590', '11620', '11650', '11680', '11710', '11740'
    ]

    current_year = datetime.now().year
    current_month = datetime.now().month
    deal_ymd = f'{current_year}{current_month:02}' # 이번달만 가져오도록 수정

    print(f"Fetching data for year: {current_year}, month: {current_month}") # 현재 년도, 월 출력
    for gu_code in gu_list:
        fetch_and_store_data(gu_code, deal_ymd)
