import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_lineage_prices():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    # 일반 유저처럼 보이게 하는 핵심 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    prices_data = []

    try:
        # 1. 타겟 사이트 접속
        driver.get("https://enchant-lab.com/market")
        
        # 2. 데이터가 로딩될 때까지 최대 15초 대기 (동적 페이지 대응)
        # 시세 숫자가 들어있는 특정 클래스나 요소를 기다립니다.
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table"))) 

        # 3. 데이터 추출
        # 형님의 사이트 구조에 맞게 5대 서버 데이터를 긁어옵니다.
        # (이 부분은 형님이 기존에 잘 쓰시던 파싱 로직을 여기 넣으시면 됩니다)
        # 예: rows = driver.find_elements(By.CSS_SELECTOR, "tr") ...

    except Exception as e:
        print(f"🚨 현장 사고 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 데이터가 비어있으면 절대 저장하지 않고 에러를 뱉음 (가짜 보고 방지)
    if not new_prices:
        print("🚨 [비상] enchant-lab에서 데이터를 한 줄도 못 가져왔습니다!")
        exit(1) 

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {
        "last_updated": current_time,
        "prices": new_prices
    }

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ [성공] 24일자 신규 시세 송출 완료: {current_time}")

if __name__ == "__main__":
    update_json()
