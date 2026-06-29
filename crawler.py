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
    last_processed_price = "" # 이전 서버의 가격을 기억하여 중복 렉 방지
    last_processed_status = "" # 이전 서버의 등락률을 기억하여 중복 렉 방지

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        
        wait = WebDriverWait(driver, 20)
        # 상단 서버 정렬 탭 컴포넌트가 확실히 뜰 때까지 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '서버')]")))
        time.sleep(5) 

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                print(f"🔄 [{target}] 버튼 조준 및 클릭...")
                
                # 서버 이름 글씨를 가진 정확한 버튼 타격
                button_xpath = f"//button[text()='{target}'] | //div[text()='{target}'] | //span[text()='{target}']"
                server_btn = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                driver.execute_script("arguments[0].click();", server_btn)
                
                # [스마트 렉 방어선] 화면이 새 서버 데이터로 리렌더링될 때까지 충분히 대기
                time.sleep(5.0)

                # 1. 등락률(%) 정밀 타격
                # 메인 시세판 영역에서 서버 이름 주변이나 등락률 기호(%)가 포함된 엘리먼트를 직접 낚아챕니다.
                try:
                    status_element = driver.find_element(By.XPATH, f"//*[contains(text(), '{target}')]/..//*[contains(text(), '%')] | //*[contains(text(), '{target}')]/following-sibling::*[contains(text(), '%')]")
                    status_raw = status_element.text.strip()
                    if status_raw and '상승권' not in status_raw:
                        change_status = status_raw.replace('전일 대비', '').strip()
                except Exception:
                    # 광역 % 태그 매칭 백업
                    try:
                        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '%')]")
                        for el in elements:
                            txt = el.text.strip()
                            if txt and '상승권' not in txt and txt != last_processed_status:
                                change_status = txt.replace('전일 대비', '').strip()
                                break
                    except Exception:
                        pass

                # 2. 최저가(원) 정밀 타격
                # '최저가' 글자 바로 뒤나 아래에 배치된 가격 숫자를 핀포인트로 조준합니다.
                try:
                    price_element = driver.find_element(By.XPATH, "//*[contains(text(), '최저가')]/following-sibling::*[contains(text(), '원')] | //*[contains(text(), '최저가')]/..//*[contains(text(), '원')]")
                    price_raw = price_element.text.strip()
                    if price_raw and price_raw != "0원":
                        current_price = price_raw
                except Exception:
                    # 광역 원 태그 매칭 백업
                    try:
                        elements = driver.find_elements(By.XPATH, "//*[contains(text(), '원')]")
                        for el in elements:
                            txt = el.text.strip()
                            if '원' in txt and len(txt) < 12 and txt != "0원":
                                current_price = txt
                                break
                    except Exception:
                        pass

            except Exception as item_err:
                print(f"⚠️ {target} 서버 수집 중 에러: {item_err}")

            # 최종 수집된 데이터를 이전 기록에 박아두어 다음 루프 때 중복 검증용으로 씁니다.
            last_processed_price = current_price
            last_processed_status = change_status

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [정밀 매칭 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

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
        
    # 등락률 복사 버그 최종 차단 장치
    if len(new_prices) >= 2 and all(p['status'] == new_prices[0]['status'] for p in new_prices):
        print("\n🚨 [위험 감지] 등락률이 갱신되지 못하고 모두 동일한 값으로 중복 수집되었습니다. 빌드를 중단합니다.")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
