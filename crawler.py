import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def get_market_data():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 로봇 차단을 피하기 위한 유저 에이전트 설정
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    
    targets = [
        {"name": "아이템매니아", "url": "https://www.itemmania.com/portal/market/list.html?gamecode=121&servercode=17004", "selector": ".item_price"},
        {"name": "아이템베이", "url": "https://www.itembay.com/item/sell/game-3828/server-30383", "selector": ".price_txt"},
        {"name": "바로템", "url": "https://www.barotem.com/product/lists/2382r902", "selector": ".item_price"}
    ]
    
    prices = []
    for site in targets:
        try:
            driver.get(site["url"])
            driver.implicitly_wait(10) # 요소가 나타날 때까지 최대 10초 대기
            time.sleep(3) # 추가 로딩 대기
            
            # 지정된 선택자에서 텍스트(가격) 추출
            element = driver.find_element(By.CSS_SELECTOR, site["selector"])
            price_text = element.text.strip()
            
            prices.append({
                "source": site["name"],
                "price": price_text,
                "status": "정상"
            })
        except Exception as e:
            prices.append({
                "source": site["name"],
                "price": "확인 불가",
                "status": "보안/오류"
            })
            
    driver.quit()
    return prices

# 결과 저장 및 실행
try:
    current_stats = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "prices": get_market_data()
    }

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(current_stats, f, ensure_ascii=False, indent=4)
    print("형님, 시세 데이터 수집 완료했습니다!")
except Exception as e:
    print(f"공장 가동 중 에러 발생: {e}")
