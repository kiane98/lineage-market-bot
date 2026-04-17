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
    # 더 최신 브라우저인 척 위장 강화
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    scraped_prices = []
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://gamebit.co.kr/lineage") 
        time.sleep(15) # 보안 통과를 위해 대기 시간을 15초로 늘림
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.select("table tbody tr") 
        
        target_servers = ["베히모스", "에바", "데포로쥬", "판도라", "켄라우헬"]
        
        found_dict = {}
        for row in rows:
            cols = row.select("td")
            if len(cols) >= 3:
                raw_name = cols[0].get_text(strip=True)
                price_val = cols[2].get_text(strip=True)
                
                for target in target_servers:
                    if target in raw_name: # 이름이 포함만 되어도 OK
                        found_dict[target] = price_val + "원"
        
        for target in target_servers:
            if target in found_dict:
                scraped_prices.append({"source": target, "price": found_dict[target]})
                
        driver.quit()
    except Exception as e:
        print(f"수집 실패 로그: {e}")

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
    print(f"최종 수집 개수: {len(result['prices'])}")
