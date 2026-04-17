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
        def to_int(s): return int(''.join(filter(str.isdigit, s)))
        old_val, new_val = to_int(old_price_str), to_int(new_price_str)
        if old_val == 0: return "0.0%"
        change = ((new_val - old_val) / old_val) * 100
        sign = "+" if change > 0 else ""
        return f"{sign}{change:.1f}%"
    except: return "0.0%"

def get_market_data():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    file_path = 'market_stats.json'
    
    old_prices = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                for p in old_data.get('prices', []):
                    old_prices[p['source']] = p['price']
            except: pass

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    scraped_prices = []
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://enchant-lab.com/market") 
        time.sleep(20) # 3사 데이터 로딩까지 넉넉히 대기
        
        # 화면 스크롤로 하단 데이터 활성화
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(3)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 인챈트랩의 메인 테이블에서 상위 5개 서버 추출
        # 서버명 / 최저가 / 평균가 중 '평균가'가 3사 통합 데이터인 경우가 많음
        rows = soup.select("tr")
        
        count = 0
        for row in rows:
            if count >= 5: break
            
            cells = row.find_all("td")
            if len(cells) >= 3:
                name = cells[0].get_text(strip=True).replace('HOT', '').replace('NEW', '').strip()
                # 인챈트랩 테이블 구조상 보통 2번째가 최저가, 3번째가 평균가(3사 통합)
                avg_price = cells[2].get_text(strip=True)
                
                # 유효한 서버 이름인지 필터링 (숫자가 너무 많거나 짧으면 패스)
                if len(name) > 1 and any(char.isdigit() for char in avg_price):
                    clean_price = ''.join(filter(str.isdigit, avg_price))
                    if len(clean_price) >= 4:
                        scraped_prices.append({
                            "source": name,
                            "price": f"{int(clean_price):,}원"
                        })
                        count += 1
        driver.quit()
    except Exception as e:
        print(f"수집 실패: {e}")

    final_prices = []
    for item in scraped_prices:
        name, new_p = item["source"], item["price"]
        old_p = old_prices.get(name, new_p)
        status_text = calculate_change(old_p, new_p)
        final_prices.append({"source": name, "price": new_p, "status": status_text})

    return {"last_updated": now, "prices": final_prices}

if __name__ == "__main__":
    result = get_market_data()
    if result['prices']:
        with open('market_stats.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"3사 통합 데이터 {len(result['prices'])}건 반영 성공!")
