import os
import json
import time
from datetime import datetime, timedelta, timezone # 시간 설정용 임포트
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def get_lineage_prices():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new') # 최신 헤드리스 모드
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 봇 차단 우회 및 한글 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # 드라이버 안정성 확보
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as driver_err:
        print(f"⚠️ 기본 크롬 드라이버 실행 실패, 웹드라이버 매니저 시도: {driver_err}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # 자동화 감지 우회 스크립트 추가
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(20) # 로딩 대기 시간 20초로 상향

        # [원인 분석용 로그] 접속한 페이지의 타이틀을 무조건 출력
        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 모든 행(tr) 추출
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        
        # [원인 분석용 로그] 테이블을 찾았는지 여부 출력
        if not rows:
            print("⚠️ [위험] 페이지에 table tr 태그가 존재하지 않습니다. (Cloudflare 차단 또는 레이아웃 변경)")
            # 디버깅을 위해 현재 페이지의 텍스트 일부 출력
            page_text = driver.find_element(By.TAG_NAME, "body").text[:300]
            print(f"📄 [화면 텍스트 일부]:\n{page_text}")
            
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
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # [핵심] 데이터가 없으면 명확하게 에러 로그를 찍고 exit(1)로 터뜨림
    if not new_prices:
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 리니지 시세 데이터 수집에 실패했습니다.")
        print("💡 원인 분석: 위 로그에서 '현재 접속된 페이지 제목'과 '화면 텍스트'를 확인하세요.")
        print("="*50 + "\n")
        exit(1) # 다시 exit(1)을 살려서 깃허브 액션을 빨간불로 만듭니다.

    # 무조건 한국 시간(UTC+9)으로 고정
    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
