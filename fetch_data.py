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
                cursor.execute('''
                    SELECT 1
                    FROM real_estate
                    WHERE dealYear = %s AND dealMonth = %s AND dealDay = %s AND sggCd = %s AND aptNm = %s AND excluUseAr = %s AND floor = %s
                ''', (dealYear, dealMonth, dealDay, sggCd, aptNm, excluUseAr, floor))

                if cursor.fetchone() is None:
                    cursor.execute('''
                        INSERT INTO real_estate (aptDong, aptNm, buildYear, dealAmount, dealDay, dealMonth, dealYear, excluUseAr, floor, sggCd, umdNm, reg_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (aptDong, aptNm, buildYear, dealAmount, dealDay, dealMonth, dealYear, excluUseAr, floor, sggCd, umdNm, now))
                    print(f"데이터 삽입: {aptNm}, {dealYear}-{dealMonth}-{dealDay}")
                else:
                    print(f"중복 데이터 존재: {aptNm}, {dealYear}-{dealMonth}-{dealDay}")

            except Exception as e:
                print(f"데이터 삽입 오류: {e}, 데이터: {ET.tostring(item, encoding='unicode')}")

        conn.commit()
        conn.close()
        print(f"{lawd_cd} 코드, {deal_ymd} 데이터 저장 완료.")

    except requests.exceptions.RequestException as e:
        print(f"API 호출 중 오류 발생: {e}")
    except ET.ParseError as e:
        print(f"XML 파싱 오류 발생: {e}")

if __name__ == "__main__":
    gu_list = [
        '11110', '11140', '11170', '11200', '11215', '11230', '11260', '11290', '11305',
        '11320', '11350', '11380', '11410', '11440', '11470', '11500', '11530', '11545',
        '11560', '11590', '11620', '11650', '11680', '11710', '11740'
    ]

    start_year = 2023
    current_year = datetime.now().year
    current_month = datetime.now().month

    for year in range(start_year, current_year + 1): # 2020년부터 현재 년도까지
        end_month = 12 if year < current_year else current_month # 현재 년도 이전은 12월까지, 현재 년도는 현재 월까지
        for month in range(1, end_month + 1):
            deal_ymd = f'{year}{month:02}'
            print(f"Fetching data for year: {year}, month: {month}") # 현재 년도, 월 출력
            for gu_code in gu_list:
                fetch_and_store_data(gu_code, deal_ymd)