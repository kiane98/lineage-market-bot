import os
import json
import time
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def get_lineage_prices():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new') # 최신 헤드리스 모드 적용
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 봇 차단 우회 및 한글 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # [수정] GitHub Actions의 설치된 크롬 경로를 직접 지정하는 안정적인 드라이버 선언
    try:
        # 먼저 시스템에 설치된 크롬 드라이버 시도
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        # 실패 시 웹드라이버 매니저 사용
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options=chrome_options)
    
    # 자동화 감지 우회 스크립트 추가
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(15) # 리액트 로딩 대기

        # [차단 확인용 덤프] 페이지가 정상적으로 안 긁힐 때 원인을 알기 위해 타이틀 출력
        print(f"🌐 현재 페이지 제목: {driver.title}")

        # 모든 행(tr) 추출
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        
        # 만약 테이블이 안 잡혔다면 페이지 소스 일부 출력 (디버깅용)
        if not rows:
            print("⚠️ 테이블 행(tr)을 찾지 못했습니다. 차단되었거나 로딩 실패일 수 있습니다.")
            
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if not cells: continue
            
            server_name = cells[0].text.strip()
            for target in target_servers:
                if target in server_name:
                    current_price = "0원"
                    change_status = "0%"

                    for cell in cells:
                        val = cell.text.strip()
                        if '원' in val and current_price == "0원":
                            current_price = val
                        elif '%' in val:
                            change_status = val

                    prices_data.append({
                        "source": target,
                        "price": current_price,
                        "status": change_status
                    })
                    print(f"🎯 매칭 성공: {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    if not new_prices:
        print("🚨 데이터 수집 실패! (데이터가 비어있습니다)")
        # Actions 디버깅을 위해 강제 종료하지 않고 빈 데이터라도 저장하거나 에러 로그를 남깁니다.
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
