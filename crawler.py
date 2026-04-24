import os
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
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--lang=ko-KR')
    
    # [핵심] 봇 차단 우회 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # 자동화 감지 우회 스크립트 실행
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    prices_data = []

    try:
        # 1. 인챈트랩 접속
        print("🚀 현장 접속 중: https://enchant-lab.com/market")
        driver.get("https://enchant-lab.com/market")
        
        # 2. 데이터 로딩 대기 (10초)
        time.sleep(10)

        # 3. [CCTV 촬영] 봇이 지금 뭘 보고 있는지 사진 찍기
        # 이 파일이 생성되면 깃허브 저장소에서 직접 눈으로 볼 수 있습니다.
        driver.save_screenshot("debug_screenshot.png")
        print("📸 디버그 스크린샷 저장 완료: debug_screenshot.png")

        # 4. 데이터 추출 로직 (형님이 기존에 쓰시던 파싱 코드 핵심부)
        # 예시: table 내부의 tr들을 찾습니다.
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        
        # [주의] 이 부분에 형님의 실제 데이터 파싱 로직을 채워넣으세요.
        # 만약 rows가 비어있으면 아래 리스트도 비게 됩니다.
        for row in rows:
            # 서버 이름과 가격을 찾는 로직...
            # prices_data.append({"source": "데포로쥬", "price": "2,956원", "status": "-2.3%"})
            pass

    except Exception as e:
        print(f"❌ 크롤링 중 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 5. 가짜 보고 차단 장치
    if not new_prices:
        print("🚨 [비상] enchant-lab에서 데이터를 한 줄도 못 가져왔습니다!")
        print("💡 저장소에 생성된 'debug_screenshot.png' 파일을 확인해 보세요.")
        exit(1) # 깃허브 액션에 빨간불을 띄웁니다.

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {
        "last_updated": current_time,
        "prices": new_prices
    }

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
