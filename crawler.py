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
        time.sleep(15) # 리액트/넥스트JS 컴포넌트 렌더링 완벽 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 브라우저의 현재 그려진 HTML 뼈대를 그대로 가져옵니다.
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # 1안: 개편된 카드형 레이아웃 내부 정밀 스캔 (형님이 보내주신 소스 구조 타격)
        # 보통 카드 UI들은 링크(a)나 특정 div 구조 묶음으로 서버명, 가격, 등락률을 같이 둡니다.
        cards = soup.find_all(['div', 'a'])
        
        for target in target_servers:
            matched = False
            
            # 모든 블록을 돌며 내가 찾는 서버 이름이 독립적으로 완벽히 들어있는 구역 추적
            for card in cards:
                # 너무 큰 상위 컨테이너는 패스하고 텍스트 구조가 명확한 카드 묶음만 선별
                card_text = card.get_text(separator="\n").split('\n')
                card_text = [t.strip() for t in card_text if t.strip()]
                
                # 카드 첫줄 부근에 서버명이 정확히 매칭되는지 검증
                if len(card_text) >= 2 and card_text[0] == target:
                    current_price = "0원"
                    change_status = "0%"
                    
                    # 해당 카드 컴포넌트 내부에서만 가격('원')과 등락률('%')을 정확히 조준합니다.
                    for text_item in card_text:
                        if '원' in text_item and current_price == "0원":
                            current_price = text_item
                        elif '%' in text_item and change_status == "0%":
                            change_status = text_item
                    
                    prices_data.append({
                        "source": target,
                        "price": current_price,
                        "status": change_status
                    })
                    print(f"🎯 [정밀 매칭 성공] {target} | 가격: {current_price} | 상태: {change_status}")
                    matched = True
                    break
            
            # 만약 위 구조로 안 잡혔을 때를 대비한 2차 백업 보정망 (텍스트 인접 노드 추적)
            if not matched:
                h3_tags = soup.find_all('h3')
                for h3 in h3_tags:
                    if h3.get_text().strip() == target:
                        # h3가 속한 부모 구역을 긁어 파싱
                        parent_block = h3.find_parent()
                        if parent_block:
                            block_texts = parent_block.get_text(separator="\n").split('\n")
                            block_texts = [b.strip() for b in block_texts if b.strip()]
                            
                            c_price = "0원"
                            c_status = "0%"
                            for bt in block_texts:
                                if '원' in bt and c_price == "0원": c_price = bt
                                if '%' in bt: c_status = bt
                                
                            prices_data.append({
                                "source": target,
                                "price": c_price,
                                "status": c_status
                            })
                            print(f"🎯 [백업 매칭 성공] {target} | 가격: {c_price} | 상태: {c_status}")
                            break

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 0원으로 꼬인 데이터가 수집되었거나 비어있다면 빌드 실패 처리하여 안전하게 홀딩
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 데이터 중복 복사 혹은 파싱 에러 징후가 발견되었습니다.")
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
