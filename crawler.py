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

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        
        wait = WebDriverWait(driver, 25)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(8) 

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                print(f"🔄 [{target}] 버튼 엘리먼트 자바스크립트 강제 클릭 시도...")
                
                # 자바스크립트 오타(.strip()) 완벽 수정 및 트림 처리 안전 보강
                js_click_cmd = f"""
                const elements = Array.from(document.querySelectorAll('button, div, span, a'));
                const targetBtn = elements.find(el => {{
                    const txt = el.innerText ? el.innerText.trim() : '';
                    return txt === '{target}';
                }});
                if (targetBtn) {{
                    targetBtn.click();
                    return true;
                }}
                return false;
                """
                
                click_success = driver.execute_script(js_click_cmd)
                if not click_success:
                    print(f"⚠️ [{target}] JS 클릭 실패, 기본 XPATH로 2차 클릭 시도...")
                    button_xpath = f"//button[text()='{target}'] | //div[text()='{target}'] | //span[text()='{target}']"
                    server_btn = driver.find_element(By.XPATH, button_xpath)
                    driver.execute_script("arguments[0].click();", server_btn)

                # 클릭 후 대시보드가 새 서버 데이터로 리렌더링될 때까지 충분히 대기
                time.sleep(5.0)

                # 데이터가 바뀐 순간의 텍스트 덤프 획득
                body_text = driver.find_element(By.TAG_NAME, "body").text
                lines = [l.strip() for l in body_text.split('\n') if l.strip()]

                # 화면 텍스트 내에서 해당 서버 이름 주위 정밀 스캔 (스캔 영역 하단으로 대폭 확장)
                for i, line in enumerate(lines):
                    if line == target or target in line:
                        scan_zone = lines[max(0, i-4):i+30]
                        
                        for item in scan_zone:
                            # 1. 최저가 추출 ('평균', '최고' 단어 제외)
                            if '원' in item and current_price == "0원":
                                if '평균' not in item and '최고' not in item and len(item) < 12:
                                    current_price = item
                            
                            # 2. 등락률 변동치 추출 ('상승권' 안내 텍스트 제외)
                            if '%' in item and change_status == "0%":
                                if '상승권' not in item and len(item) < 10:
                                    change_status = item.replace('전일 대비', '').strip()
                        break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 수집 중 부분 예외 발생: {item_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [결과 기록] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 0원 누락 리스크 방지 안전장치
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [빌드 실패] 일부 서버 시세(0원)가 정상적으로 수집되지 못했습니다.")
        print("="*50 + "\n")
        exit(1)
        
    # 데이터 오염(전부 같은 값 복사됨) 방지 차단 장치
    if len(new_prices) >= 2:
        all_same_price = all(p['price'] == new_prices[0]['price'] for p in new_prices)
        all_same_status = all(p['status'] == new_prices[0]['status'] for p in new_prices)
        if all_same_price or all_same_status:
            print("\n🚨 [위험 감지] 서버 간 데이터 중복 복사 현상이 발견되어 빌드를 홀딩합니다.")
            exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
