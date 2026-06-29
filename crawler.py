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
        
        wait = WebDriverWait(driver, 20)
        
        # 1단계: 형님이 보내주신 스크린샷 상단에 고정된 [전체 28] 또는 [서버 순서] 버튼 영역 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '전체') or contains(text(), '서버')]")))
        time.sleep(3)
        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # [치트키 활성화] 
        # 화면에 데이터를 강제로 바인딩시키기 위해 상단 정렬 버튼그룹([전체 28] 또는 [서버 순서])을 강제로 찾아 클릭 이벤트를 발생시킵니다.
        try:
            trigger_xpath = "//button[contains(text(), '전체')] | //div[contains(text(), '전체')] | //button[contains(text(), '서버 순서')] | //div[contains(text(), '서버 순서')]"
            trigger_btn = driver.find_element(By.XPATH, trigger_xpath)
            driver.execute_script("arguments[0].click();", trigger_btn)
            print("⚡ [데이터 깨우기] 상단 전체/소팅 필터 버튼 클릭 완료 (데이터 강제 로딩 트리거)")
            time.sleep(5) # 데이터가 돔 트리에 완전히 풀리는 시간 확보
        except Exception as e:
            print(f"⚠️ 트리거 버튼 클릭 패스 (이미 활성화되었을 수 있음): {e}")

        # 2단계: 데이터가 강제 로딩된 상태의 브라우저 전체 텍스트 정적 복사
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]
        
        print(f"📋 실시간 스캔된 전체 텍스트 라인 수: {len(lines)}개 (활성화 확인용)")

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # 3단계: 족집게 순회 탐색
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            for i, line in enumerate(lines):
                if line == target or target in line:
                    # 서버 이름 기준 위아래 25줄 범위를 샅샅이 뒤져 최저가와 등락률 매칭
                    scan_zone = lines[max(0, i-5):i+25]
                    
                    for item in scan_zone:
                        # 가격 포착 ('평균', '최고' 단어를 엄격히 배제하여 최저가 핀포인트 수집)
                        if '원' in item and current_price == "0원":
                            if '평균' not in item and '최고' not in item and len(item) < 12:
                                current_price = item
                        
                        # 등락률 포착 ('상승권' 문구 제외 및 부호가 들어간 것 필터링)
                        if '%' in item and change_status == "0%":
                            if '상승권' not in item and len(item) < 10:
                                change_status = item.replace('전일 대비', '').strip()
                    break

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [정밀 매칭 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 누락 방지 최종 마감벨트
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 비동기 데이터 탭 로딩 텍스트에서 일부 시세(0원)가 유실되었습니다.")
        print("="*50 + "\n")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
