import os
import json
import time
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        
        wait = WebDriverWait(driver, 20)
        # 상단 서버 목록 레이아웃이 로딩될 때까지 안전하게 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '서버')]")))
        time.sleep(5) 

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                print(f"🔄 [{target}] 버튼 탐색 및 클릭 시도...")
                
                # 형님 말씀대로 글씨를 정확히 알아보고 조준하는 XPATH 규칙입니다.
                button_xpath = f"//button[text()='{target}'] | //div[text()='{target}'] | //span[text()='{target}']"
                server_btn = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                
                # 확실하게 클릭 조작 수행
                driver.execute_script("arguments[0].click();", server_btn)
                
                # [핵심 보정] 리액트 화면이 완전히 새 서버 시세판으로 리렌더링될 때까지 4.5초 정지 대기 (지연 방어)
                time.sleep(4.5) 

                # 클릭 후 새롭게 동적 반영된 겉화면 텍스트만 추출
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                # [핀포인트 추출 구역 설정]
                # 화면에서 엉뚱하게 다른 서버 시세를 긁지 않도록, 클릭된 서버 이름이 박혀있는 대형 시세 대시보드 구역만 격리 타격합니다.
                main_zone = soup.find(lambda tag: tag.name in ['h2', 'h3', 'div'] and target in tag.get_text() and ('원' in tag.parent.get_text() or '%' in tag.parent.get_text()))
                
                if not main_zone:
                    # 백업용 광역 검색
                    main_zone = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'p'] and target in tag.get_text())

                if main_zone:
                    # 해당 서버 데이터가 노출되는 카드 박스 부모 엘리먼트 획득
                    box_container = main_zone.parent.parent if main_zone.parent else main_zone
                    box_text = box_container.get_text(separator="\n").split('\n')
                    box_text = [b.strip() for b in box_text if b.strip()]
                    
                    print(f"📊 [{target}] 활성화 카드 실시간 텍스트 데이터 블록: {box_text}")

                    # 카드 안에서 '최저가' 글자 바로 옆 라인이나 텍스트를 검증해서 시세 추출
                    for idx, text_item in enumerate(box_text):
                        if '최저가' in text_item and idx + 1 < len(box_text):
                            if '원' in box_text[idx+1]:
                                current_price = box_text[idx+1]
                        
                        if '원' in text_item and current_price == "0원" and len(text_item) < 12:
                            current_price = text_item
                            
                        if '%' in text_item and change_status == "0%":
                            change_status = text_item

                # 만약 박스 특정 추출이 실패했다면 최후방 텍스트 인접 서치 가동
                if current_price == "0원":
                    all_lines = soup.get_text(separator="\n").split('\n')
                    all_lines = [l.strip() for l in all_lines if l.strip()]
                    for i, line in enumerate(all_lines):
                        if line == target:
                            for sub in all_lines[i:i+12]:
                                if '원' in sub and current_price == "0원" and len(sub) < 12:
                                    current_price = sub
                                if '%' in sub and change_status == "0%":
                                    change_status = sub
                            break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 클릭 제어 실패 또는 타임아웃: {item_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [추출 마감 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 0원 유실 방지 최종 스토퍼
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 갱신된 화면 텍스트 타겟팅에서 누락이 발견되었습니다.")
        print("="*50 + "\n")
        exit(1)
        
    # 복사 에러 최종 스토퍼: 모든 서버 시세가 하나로 복사되었다면 데이터 오염으로 판단하고 빌드를 정지시킵니다.
    if len(new_prices) >= 2 and all(p['price'] == new_prices[0]['price'] for p in new_prices):
        print("\n🚨 [위험 감지] 서버 시세가 리렌더링되지 못하고 동일 금액으로 중복 수집되었습니다.")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
