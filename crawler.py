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
        
        # 기본 페이지 로딩 대기
        wait = WebDriverWait(driver, 15)
        
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                # 1단계: 스크린샷 상단에 배치된 서버 버튼(텍스트 매칭)을 찾아 강제 클릭
                # 버튼 내 공백이 있을 수 있으므로 contains 구문으로 유연하게 타격합니다.
                button_xpath = f"//button[contains(text(), '{target}')] | //div[contains(text(), '{target}')]"
                server_btn = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                
                # 자바스크립트를 이용해 정확하고 안전하게 클릭 이벤트를 발생시킵니다.
                driver.execute_script("arguments[0].click();", server_btn)
                time.sleep(2.5) # 버튼 클릭 후 아래쪽 시세 카드판이 갱신되는 시간 대기

                # 2단계: 클릭 후 갱신된 화면의 HTML 소스를 긁어 BeautifulSoup으로 분석
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                # 화면 전체 텍스트에서 '원'과 '%' 추출
                all_text = soup.get_text(separator="\n").split('\n')
                all_text = [t.strip() for t in all_text if t.strip()]

                # 스크린샷 구조상 클릭된 서버의 정보는 메인 대형 뷰어 영역에 배치됩니다.
                # 해당 텍스트 데이터 뭉치 안에서 알맞은 가격과 변동률을 찾아냅니다.
                for item in all_text:
                    if '원' in item and current_price == "0원" and len(item) < 15:
                        current_price = item
                    if '%' in item and change_status == "0%" and ('+' in item or '-' in item or '0' in item):
                        change_status = item

            except Exception as click_err:
                print(f"⚠️ {target} 서버 버튼 클릭 또는 파싱 중 에러 발생: {click_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [화면 클릭 타격 성공] {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 5개 타겟 서버 중 단 하나라도 가격 수집이 누락(0원)되면 안전하게 빌드를 정지시킵니다.
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 서버 클릭 후 가격 데이터를 받아오지 못했습니다. 버튼 바인딩 확인이 필요합니다.")
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
