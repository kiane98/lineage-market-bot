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
    
    # 봇 차단 우회용 헤더 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        print(f"🚀 현장 잠입: {url}")
        driver.get(url)
        
        # 리액트 로딩 대기 (15초)
        time.sleep(15)

        # 테이블 행 추출
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            
            # 최소 4칸 이상 있어야 등락폭(%)까지 가져올 수 있습니다.
            if len(cells) >= 4:
                server_name = cells[0].text.strip()
                
                for target in target_servers:
                    if target in server_name:
                        # [정밀 매칭]
                        # cells[1]: 현재가 (예: 2,800원)
                        # cells[2]: 전일가 (예: 2,850원) -> 지금 status에 잘못 들어가는 값
                        # cells[3]: 등락폭 (예: -1.7%) -> 우리가 진짜 원하는 값
                        
                        current_price = cells[1].text.strip()
                        change_status = cells[3].text.strip() # 4번째 칸(인덱스 3) 타겟팅
                        
                        prices_data.append({
                            "source": target,
                            "price": current_price,
                            "status": change_status
                        })
                        print(f"✅ 수집 성공: {target} | {current_price} | {change_status}")

    except Exception as e:
        print(f"❌ 현장 사고 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    if not new_prices:
        print("🚨 [비상] 데이터를 수집하지 못했습니다. 저장을 중단합니다.")
        exit(1)

    # 한국 시간(KST)으로 기록
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {
        "last_updated": current_time,
        "prices": new_prices
    }

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 [최종 성공] {current_time} KST 업데이트 완료!")

if __name__ == "__main__":
    update_json()
