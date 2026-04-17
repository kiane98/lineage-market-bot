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
        time.sleep(20) # 데이터 로딩 대기
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # [수정] 인챈트랩의 'HOT' 서버와 일반 서버 리스트를 모두 포함하는 더 넓은 범위 조준
        # 서버 이름과 시세가 들어있는 모든 행을 찾습니다.
        all_rows = soup.select("tr")
        
        found_data = []
        for row in all_rows:
            # 텍스트 내에 '원'과 숫자가 포함된 행 위주로 탐색
            row_text = row.get_text(separator=' ', strip=True)
            if '원' in row_text and any(char.isdigit() for char in row_text):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    # 첫 번째 칸에서 서버명 추출 (HOT/NEW 텍스트 제거)
                    name = cells[0].get_text(strip=True).replace('HOT', '').replace('NEW', '').strip()
                    
                    # 가격 후보들 중 가장 적절한 평균가 추출
                    price_val = ""
                    for cell in cells:
                        c_text = cell.get_text(strip=True)
                        clean_digit = ''.join(filter(str.isdigit, c_text))
                        if len(clean_digit) >= 4: # 1,000원 단위 이상만 가격으로 인정
                            price_val = f"{int(clean_digit):,}원"
                            # 보통 3사 평균가는 뒤쪽 셀에 있으므로 계속 갱신하며 마지막 것을 선택하거나 특정 순서 지정
                    
                    if name and price_val and name not in [d['source'] for d in found_data]:
                        found_data.append({"source": name, "price": price_val})

        # 핫 지수 순서대로 상위 5개만 컷!
        scraped_prices = found_data[:5]
        driver.quit()
    except Exception as e:
        print(f"수집 오류: {e}")

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
        print(f"총 {len(result['prices'])}개 서버(5대장 포함) 수집 완료!")
