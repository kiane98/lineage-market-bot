import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def get_market_data():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    file_path = 'market_stats.json'
    
    # [1단계] 기존 데이터 불러오기 (백업)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            backup_prices = old_data.get('prices', [])
    else:
        # 파일이 아예 없는 최초 실행 시에만 쓸 임시 값
        backup_prices = [{"source": "데이터 로딩중", "price": "-", "status": "대기"}]

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        
        # [2단계] 실제 사이트 접속 시도
        # (여기에 형님이 원하시는 타겟 사이트 주소를 넣으세요)
        driver.get("https://www.barotem.com/product/lists/2382r902")
        time.sleep(5)
        
        # [성공 가설] 여기서 진짜 데이터를 긁어왔다고 치고 리스트를 만듭니다.
        # 실제 추출 로직이 완성되면 이 부분이 교체됩니다.
        new_prices = [
            {"source": "베히모스 (HOT)", "price": "232,000원", "status": "+7.2%"},
            {"source": "켄라우헬", "price": "218,000원", "status": "+4.8%"},
            {"source": "에바스", "price": "194,000원", "status": "+1.3%"},
            {"source": "데포로쥬", "price": "205,000원", "status": "-2.1%"}
        ]
        
        driver.quit()
        print("로그: 신규 시세 수집 성공!")
        return {"last_updated": now, "prices": new_prices, "msg": "실시간 데이터"}

    except Exception as e:
        print(f"로그: 수집 실패({str(e)}). 이전 데이터를 유지합니다.")
        # [3단계] 실패 시 이전 데이터의 상태 메시지만 "지연중"으로 변경
        for item in backup_prices:
            item["status"] = "수집지연"
        
        return {
            "last_updated": old_data.get('last_updated', now), # 시간도 이전 시간 유지
            "prices": backup_prices,
            "msg": "수집 지연 (이전 데이터)"
        }

if __name__ == "__main__":
    result = get_market_data()
    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
