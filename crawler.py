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
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '서버')]")))
        time.sleep(5) 

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                print(f"🔄 [{target}] 버튼 탐색 및 클릭 시도...")
                
                button_xpath = f"//button[text()='{target}'] | //div[text()='{target}'] | //span[text()='{target}']"
                server_btn = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                
                driver.execute_script("arguments[0].click();", server_btn)
                time.sleep(4.5) # 컴포넌트 리렌더링 충분한 대기 시간

                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                # 타겟 서버 정보가 들어있는 메인 카드 뷰어 존 격리 추적
                main_zone = soup.find(lambda tag: tag.name in ['h2', 'h3', 'div'] and target in tag.get_text() and ('원' in tag.parent.get_text() or '%' in tag.parent.get_text()))
                
                if not main_zone:
                    main_zone = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'p'] and target in tag.get_text())

                if main_zone:
                    box_container = main_zone.parent.parent if main_zone.parent else main_zone
                    box_text = box_container.get_text(separator="\n").split('\n')
                    box_text = [b.strip() for b in box_text if b.strip()]
                    
                    print(f"📊 [{target}] 활성화 카드 내역: {box_text}")

                    for idx, text_item in enumerate(box_text):
                        if '최저가' in text_item and idx + 1 < len(box_text):
                            if '원' in box_text[idx+1]:
                                current_price = box_text[idx+1]
                        
                        if '원' in text_item and current_price == "0원" and len(text_item) < 12:
                            current_price = text_item
                            
                        # [오타 보정 핵심 수정] '상승권' 같은 야매 텍스트를 건너뛰고, 진짜 부호(+, -)나 숫자가 섞인 등락률만 수집
                        if '%' in text_item and change_status == "0%":
                            if any(char in text_item for char in ['+', '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']) and '상승권' not in text_item:
                                change_status = text_item

                # 최후방 백업 서치 레이아웃
                if current_price == "0원":
                    all_lines = soup.get_text(separator="\n").split('\n')
                    all_lines = [l.strip() for l in all_lines if l.strip()]
                    for i, line in enumerate(all_lines):
                        if line == target:
                            for sub in all_lines[i:i+12]:
                                if '원' in sub and current_price == "0원" and len(sub) < 12:
                                    current_price = sub
                                if '%' in sub and change_status == "0%" and '상승권' not in sub:
                                    change_status = sub
                            break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 제어 렉/실패: {item_err}")

            # 최종 상태 값 이쁘게 정리 (예: '전일 대비 +1.7%' -> '+1.7%')
            if '전일 대비' in change_status:
                change_status = change_status.replace('전일 대비', '').strip()

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n🚨 [최종 빌드 실패] 수집 유실 누락 데이터가 감지되었습니다.")
        exit(1)
        
    if len(new_prices) >= 2 and all(p['price'] == new_prices[0]['price'] for p in new_prices):
        print("\n🚨 [위험 감지] 서버 시세 중복 복사 버그가 발견되어 빌드를 홀딩합니다.")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
