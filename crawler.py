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
    
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        print(f"🚀 현장 진입: {url}")
        driver.get(url)
        
        # 데이터 로딩 대기 (15초)
        time.sleep(15)

        # [핵심] 테이블의 모든 행(tr)을 가져옵니다.
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for row in rows:
            # 각 행의 칸(td)들을 리스트로 추출
            cells = row.find_elements(By.TAG_NAME, "td")
            
            # 데이터가 있는 유효한 행인지 확인 (최소 3칸 이상)
            if len(cells) >= 3:
                server_name = cells[0].text.strip()
                
                for target in target_servers:
                    if target in server_name:
                        # [정밀 타격] 인덱스를 지정해서 정확한 칸의 데이터를 가져옵니다
                        prices_data.append({
                            "source": target,
                            "price": cells[1].text.strip(), # 두 번째 칸: 현재 시세
                            "status": cells[2].text.strip() # 세 번째 칸: 변동폭(%)
                        })
                        print(f"✅ 수집 성공: {target} - {cells[1].text.strip()}")

    except Exception as e:
        print(f"❌ 현장 사고: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 데이터가 비어있으면 저장 중단 (가짜 보고 방지)
    if not new_prices:
        print("🚨 [비상] 데이터를 가져오지 못했습니다. 저장하지 않습니다.")
        exit(1)

    # 한국 시간(KST)으로 기록
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {
        "last_updated": current_time,
        "prices": new_prices
    }

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 [성공] {current_time} KST 업데이트 완료!")

if __name__ == "__main__":
    update_json()
