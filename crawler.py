import os
import json
import time
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def get_lineage_prices():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(15) # 컴포넌트 렌더링 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # [핵심 변경] /market/서버명 링크를 가진 모든 카드(a 태그)를 일괄 추출
        market_links = soup.find_all('a', href=True)
        
        for target in target_servers:
            for link in market_links:
                href_url = link['href']
                
                # 주소 검증 (예: /market/데포로쥬)
                if '/market/' in href_url and target in href_url:
                    # 카드 내부의 모든 텍스트 요소를 순서대로 정렬
                    card_text = link.get_text(separator="\n").split('\n')
                    card_text = [t.strip() for t in card_text if t.strip()]
                    
                    current_price = "0원"
                    change_status = "0%"
                    
                    # 카드 내부 텍스트에서 '원'과 '%'를 지능적으로 매칭
                    # 보통 첫 번째 나오는 '원'이 해당 서버의 최저가(실제 시세)입니다.
                    for text_item in card_text:
                        if '원' in text_item and current_price == "0원":
                            current_price = text_item
                        elif '%' in text_item:
                            change_status = text_item
                            
                    prices_data.append({
                        "source": target,
                        "price": current_price,
                        "status": change_status
                    })
                    print(f"🎯 [카드 정밀 타격 성공] {target} | 가격: {current_price} | 상태: {change_status}")
                    break # 찾았으면 해당 서버 탐색은 종료하고 다음 타겟 서버로 이동

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 5개 서버 중 하나라도 수집 실패(0원)했거나 비어있으면 안전하게 터뜨림
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 일부 타겟 서버 누락 또는 데이터 추출 에러가 발생했습니다.")
        print("="*50 + "\n")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
