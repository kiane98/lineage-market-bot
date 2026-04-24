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
    
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        print(f"🚀 현장 진입: {url}")
        driver.get(url)
        
        # 데이터 로딩 대기
        time.sleep(15)

        # 테이블 행들을 가져옴
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for row in rows:
            # 칸별로 쪼개서 정확히 가져오기
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                server_name = cells[0].text.strip()
                for target in target_servers:
                    if target in server_name:
                        # [핵심] 인덱스를 지정해서 정확한 칸의 데이터를 가져옵니다
                        prices_data.append({
                            "source": target,
                            "price": cells[1].text.strip(), # 두 번째 칸: 가격
                            "status": cells[2].text.strip() # 세 번째 칸: 변동폭(%)
                        })
                        print(f"✅ 수집 성공: {target}")

    except Exception as e:
        print(f"❌ 현장 사고: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    if not new_prices:
        print("🚨 [비상] 데이터를 가져오지 못했습니다.")
        exit(1)

    # 깃허브 서버 시간이 아닌 한국 시간으로 기록
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {
        "last_updated": current_time,
        "prices": new_prices
    }

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 [성공] {current_time} 업데이트 완료!")

if __name__ == "__main__":
    update_json()
