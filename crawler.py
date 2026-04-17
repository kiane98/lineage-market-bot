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
    """전일 대비 상승률 계산 로직"""
    try:
        def to_int(s):
            return int(''.join(filter(str.isdigit, s)))
        
        old_val = to_int(old_price_str)
        new_val = to_int(new_price_str)
        
        if old_val == 0: return "0.0%"
        
        change = ((new_val - old_val) / old_val) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"
    except:
        return "0.0%"

def get_market_data():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    file_path = 'market_stats.json'
    
    # [1단계] 기존 장부(JSON) 읽어오기 (상승률 계산용)
    old_prices = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                for p in old_data.get('prices', []):
                    old_prices[p['source']] = p['price']
            except:
                pass

    # [2단계] 크롬 브라우저 세팅 (보안 우회)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    # [3단계] 고정 출연 서버 리스트 (PD님 컨펌 라인업)
    target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]
    found_data = {}

    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://enchant-lab.com/market") 
        time.sleep(20) # 인챈트랩 보안 및 데이터 로딩 충분히 대기
        
        # 화면 스크롤 (숨겨진 데이터 활성화)
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 페이지 내 모든 행(tr)을 훑으며 타겟 서버 탐색
        rows = soup.find_all("tr")
        for row in rows:
            row_text = row.get_text(strip=True)
            for target in target_servers:
                # 서버 이름이 포함되어 있고, 아직 수집 전이라면
                if target in row_text and target not in found_data:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 3:
                        # 보통 3번째 셀이 3사 통합 평균가(Avg)
                        avg_text = cells[2].get_text(strip=True)
                        clean_digit = ''.join(filter(str.isdigit, avg_text))
                        
                        if len(clean_digit) >= 4:
                            found_data[target] = f"{int(clean_digit):,}원"
        
        driver.quit()
    except Exception as e:
        print(f"크롤링 현장 사고 발생: {e}")

    # [4단계] 데이터 정제 및 상승률 합산
    final_prices = []
    for name in target_servers:
        # 새로 긁어온 가격이 없으면 장부 가격 유지, 둘 다 없으면 "점검중"
        new_p = found_data.get(name, old_prices.get(name, "점검중"))
        old_p = old_prices.get(name, new_p)
        
        status_text = calculate_change(old_p, new_p)
        
        final_prices.append({
            "source": name,
            "price": new_p,
            "status": status_text
        })

    return {"last_updated": now, "prices": final_prices}

if __name__ == "__main__":
    result = get_market_data()
    
    # 결과 파일 저장
    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        
    print(f"--- 수집 완료: {result['last_updated']} ---")
    for item in result['prices']:
        print(f"서버: {item['source']} | 가격: {item['price']} | 등락: {item['status']}")
