import os
import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def calculate_change(old_price_str, new_price_str):
    try:
        # "232,000원" -> 232000 (숫자로 변환)
        old_val = int(old_price_str.replace(',', '').replace('원', ''))
        new_val = int(new_price_str.replace(',', '').replace('원', ''))
        
        if old_val == 0: return "0.0%"
        
        change = ((new_val - old_val) / old_val) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"
    except:
        return "0.0%"

def get_market_data():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    file_path = 'market_stats.json'
    
    # [1단계] 어제 데이터 불러오기 (백업 및 비교용)
    old_prices = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                # 서버명을 키로 해서 어제 가격 저장
                for p in old_data.get('prices', []):
                    old_prices[p['source']] = p['price']
            except: pass

    # [2단계] 오늘 시세 긁어오기 (현재는 기준 사이트에서 긁어온다고 가정)
    # 실제 추출 로직이 작동하기 전까지 형님이 보여주신 최신 시세를 '오늘 시세'로 세팅
    current_market_prices = [
        {"source": "베히모스 (HOT)", "price": "232,000원"},
        {"source": "켄라우헬", "price": "218,000원"},
        {"source": "에바스", "price": "194,000원"},
        {"source": "데포로쥬", "price": "205,000원"}
    ]

    # [3단계] 상승률 자동 계산
    final_prices = []
    for item in current_market_prices:
        name = item["source"]
        new_p = item["price"]
        old_p = old_prices.get(name, new_p) # 어제 기록 없으면 오늘 가격과 같다고 간주
        
        status_text = calculate_change(old_p, new_p)
        final_prices.append({
            "source": name,
            "price": new_p,
            "status": status_text
        })

    return {"last_updated": now, "prices": final_prices}

if __name__ == "__main__":
    result = get_market_data()
    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print("상승률 계산 및 업데이트 완료!")
