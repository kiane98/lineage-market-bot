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
    
    # [1단계] 기존 장부 읽기 (어제 시세와 비교하기 위함)
    old_prices = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                for p in old_data.get('prices', []):
                    old_prices[p['source']] = p['price']
            except: pass

    # [2단계] 위장 브라우저 세팅 (경비 로봇 속이기)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    scraped_prices = []
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://gamebit.co.kr/lineage") 
        time.sleep(12) # 현장 상황(로딩)을 고려해 좀 더 넉넉히 대기
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.select("table tbody tr") 
        
        # [형님의 특명] 거래량 상위 5대 서버 정밀 조준
        target_servers = ["베히모스", "에바", "데포로쥬", "판도라", "켄라우헬"]
        
        found_data = {}
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 3:
                server_name = cols[0].get_text(strip=True)
                for target in target_servers:
                    # 서버 이름이 정확히 일치하거나 포함되어 있는지 확인
                    if target in server_name:
                        price_val = cols[2].get_text(strip=True) 
                        found_data[target] = price_val + "원"
                        break
        
        # 우리가 원하는 순서대로 리스트 재구성
        for target in target_servers:
            if target in found_data:
                scraped_prices.append({"source": target, "price": found_data[target]})
                
        driver.quit()
    except Exception as e:
        print(f"현장 수집 중 사고 발생: {e}")
        # 실패 시 비상용 데이터 없이 빈 리스트로 반환 (형님 요청 사항)

    # [3단계] 상승률 계산 및 최종 보고서 작성
    final_prices = []
    for item in scraped_prices:
        name = item["source"]
        new_p = item["price"]
        old_p = old_prices.get(name, new_p) # 어제 기록 없으면 오늘 가격 기준
        
        status_text = calculate_change(old_p, new_p)
        final_prices.append({
            "source": name,
            "price": new_p,
            "status": status_text
        })

    return {"last_updated": now, "prices": final_prices}

if __name__ == "__main__":
    result = get_market_data()
    # 수집된 서버 개수 출력 (로그 확인용)
    print(f"보고 완료: 총 {len(result['prices'])}개 서버의 진짜 시세를 획득했습니다.")
    
    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
