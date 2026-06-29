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
    target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

    try:
        # 숨겨진 버튼을 찾지 않고, 주소 뒤에 서버명을 직접 붙여서 대시보드를 강제 호출합니다.
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                # 예: https://enchant-lab.com/market/켄라우헬
                direct_url = f"https://enchant-lab.com/market/{target}"
                print(f"🌐 [{target}] 다이렉트 주소 이동 시도 ➔ {direct_url}")
                driver.get(direct_url)
                
                # 리액트 렌더링 및 통계 대시보드가 그려질 때까지 대기
                wait = WebDriverWait(driver, 20)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(6.5) # 안전하게 시세판이 갱신되는 시간 확보

                # 겉화면 텍스트를 긁어 배열로 해체
                body_text = driver.find_element(By.TAG_NAME, "body").text
                lines = [l.strip() for l in body_text.split('\n') if l.strip()]

                # 화면 내에 해당 서버 명칭이 포함된 메인 대시보드 구역 스캔
                for i, line in enumerate(lines):
                    if line == target or target in line:
                        # 텍스트 발견 지점 주변 30줄을 타겟팅
                        scan_zone = lines[max(0, i-4):i+30]
                        
                        for item in scan_zone:
                            # 1. 최저가 픽업 ('평균', '최고' 단어 제외)
                            if '원' in item and current_price == "0원":
                                if '평균' not in item and '최고' not in item and len(item) < 12:
                                    current_price = item
                            
                            # 2. 등락률 픽업 ('상승권' 문구 제외)
                            if '%' in item and change_status == "0%":
                                if '상승권' not in item and len(item) < 10:
                                    change_status = item.replace('전일 대비', '').strip()
                        break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 페이지 강제 로딩 중 예외 발생: {item_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [수집 기록 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 치명적 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 누락 데이터 방어선
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [빌드 실패] 주소 직타 매칭에서 일부 서버 시세(0원)가 유실되었습니다.")
        print("="*50 + "\n")
        exit(1)
        
    # 중복 복사 방어선
    if len(new_prices) >= 2:
        all_same_price = all(p['price'] == new_prices[0]['price'] for p in new_prices)
        all_same_status = all(p['status'] == new_prices[0]['status'] for p in new_prices)
        if all_same_price or all_same_status:
            print("\n🚨 [위험 감지] 서버 간 데이터 동일 중복 수집 징후가 발견되어 빌드를 안전 홀딩합니다.")
            exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
