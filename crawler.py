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
    
    # 봇 차단 우회 및 한글 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(15) # 리액트 로딩 대기

        # 모든 행(tr) 추출
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells: continue
            
            server_name = cells[0].text.strip()
            for target in target_servers:
                if target in server_name:
                    # [지능형 추출] 칸 번호에 의존하지 않고 내용으로 찾습니다.
                    current_price = "0원"
                    change_status = "0%"

                    # 모든 칸을 훑으며 데이터 성격에 맞춰 할당
                    for cell in cells:
                        val = cell.text.strip()
                        if '원' in val and current_price == "0원":
                            # 첫 번째로 만나는 '원'이 현재가
                            current_price = val
                        elif '%' in val:
                            # '%'가 들어있는 칸이 우리가 찾는 등락폭
                            change_status = val

                    prices_data.append({
                        "source": target,
                        "price": current_price,
                        "status": change_status
                    })
                    print(f"🎯 매칭 성공: {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    if not new_prices:
        print("🚨 데이터 수집 실패!")
        exit(1)

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 최종 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
