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
        old_val = int(old_price_str.replace(',', '').replace('원', ''))
        new_val = int(new_price_str.replace(',', '').replace('원', ''))
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
        # 인챈트랩 시세 페이지로 조준 변경
        driver.get("https://enchant-lab.com/market") 
        time.sleep(15) # 페이지 로딩 및 보안 통과 대기
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 인챈트랩의 시세 테이블 구조를 파싱 (서버명과 가격 추출)
        # ※ 인챈트랩 구조에 맞춘 정밀 타격 로직
        target_servers = ["베히모스", "에바", "데포로쥬", "판도라", "켄라우헬"]
        found_data = {}

        # 모든 테이블 행을 훑음
        rows = soup.find_all("tr")
        for row in rows:
            text = row.get_text()
            for target in target_servers:
                if target in text:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        # 가격이 포함된 셀을 찾아 숫자만 추출 (보통 2번째나 3번째 셀)
                        for cell in cells:
                            val = cell.get_text(strip=True)
                            if "원" in val or (val.replace(',', '').isdigit() and len(val) > 3):
                                # "원"이 없으면 붙여주고, 있으면 그대로 사용
                                final_val = val if "원" in val else f"{val}원"
                                found_data[target] = final_val
                                break

        for target in target_servers:
            if target in found_data:
                scraped_prices.append({"source": target, "price": found_data[target]})
                
        driver.quit()
    except Exception as e:
        print(f"인챈트랩 수집 실패: {e}")

    final_prices = []
    for item in scraped_prices:
        name = item["source"]
        new_p = item["price"]
        old_p = old_prices.get(name, new_p)
        status_text = calculate_change(old_p, new_p)
        final_prices.append({"source": name, "price": new_p, "status": status_text})

    return {"last_updated": now, "prices": final_prices}

if __name__ == "__main__":
    result = get_market_data()
    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"인챈트랩에서 {len(result['prices'])}개 서버 정보 획득 완료!")
