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
        # 메인 레이아웃 안착 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '서버')]")))
        time.sleep(8) 

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # 돔 구조 상에 흩어진 모든 텍스트 요소를 브라우저 엔진 기준으로 한 번에 확보
        # 순서 꼬임과 렌더링 지연을 일괄 차단하기 위한 덩어리 획득
        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]
        
        print(f"📋 실시간 스캔된 전체 텍스트 라인 수: {len(lines)}개")

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            # 텍스트 라인 전체를 돌면서 서버 이름 근처의 값을 핀포인트 매칭
            for i, line in enumerate(lines):
                if line == target:
                    # 해당 서버 이름이 발견된 인덱스 기준, 아래쪽 15줄 범위를 정밀 돋보기 스캔
                    scan_zone = lines[i:i+16]
                    
                    for item in scan_zone:
                        # 1. 가격 추출: '원'이 포함되어 있고 '평균', '최고' 단어가 없는 순수 최저가 픽업
                        if '원' in item and current_price == "0원":
                            if '평균' not in item and '최고' not in item and len(item) < 12:
                                current_price = item
                        
                        # 2. 등락률 추출: '%' 기호가 포함된 순수 수치 픽업 ('상승권' 안내문 제외)
                        if '%' in item and change_status == "0%":
                            if '상승권' not in item and len(item) < 10:
                                change_status = item.replace('전일 대비', '').strip()
                    break

            # 만약 위 규칙으로 못 찾았다면, 포함 조건(in)으로 2차 광역 필터링
            if current_price == "0원":
                for i, line in enumerate(lines):
                    if target in line:
                        scan_zone = lines[max(0, i-2):i+15]
                        for item in scan_zone:
                            if '원' in item and current_price == "0원" and '평균' not in item and '최고' not in item and len(item) < 12:
                                current_price = item
                            if '%' in item and change_status == "0%" and '상승권' not in item:
                                change_status = item.replace('전일 대비', '').strip()
                        break

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [정밀 포착 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 0원 유실 방지 최종 안전벨트
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 돔 렌더링 텍스트에서 일부 서버 시세(0원)가 누락되었습니다.")
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
