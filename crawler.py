import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def get_lineage_prices():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--lang=ko-KR')
    
    # 일반 유저인 척 속이는 봇 차단 우회 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # 자동화 감지 무력화 스크립트
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        # 1. 인챈트랩 마켓 접속
        url = "https://enchant-lab.com/market"
        print(f"🚀 현장 진입: {url}")
        driver.get(url)
        
        # 2. 동적 로딩 대기 (형님, 넉넉하게 15초 잡았습니다)
        time.sleep(15)

        # [디버깅용] 현재 화면 사진 찍기 (작동 확인용)
        driver.save_screenshot("debug_screenshot.png")

        # 3. 데이터 파싱 로직 (enchant-lab 테이블 구조 정밀 타격)
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for row in rows:
            text = row.text.strip()
            if not text: continue
            
            for server in target_servers:
                if server in text:
                    # 텍스트 예시: "데포로쥬 3,198원 -1.1%"
                    parts = text.split()
                    if len(parts) >= 3:
                        prices_data.append({
                            "source": parts[0],
                            "price": parts[1],
                            "status": parts[2]
                        })
                        print(f"✅ 수집 성공: {parts[0]} - {parts[1]}")

    except Exception as e:
        print(f"❌ 크롤링 중 현장 사고: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 4. 데이터가 없으면 저장을 중단하여 '가짜 업데이트' 방지
    if not new_prices:
        print("🚨 [비상] 데이터를 한 줄도 못 가져왔습니다. 소스 코드를 재점검하세요.")
        exit(1) # 깃허브 액션에 빨간불을 띄웁니다.

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {
        "last_updated": current_time,
        "prices": new_prices
    }

    # 5. 최종 JSON 저장
    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 [성공] {current_time} KST 시세 업데이트 완료!")

if __name__ == "__main__":
    update_json()
