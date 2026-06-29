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
    # 최신 셀레니움에서는 --headless=new 모드가 더 안정적입니다.
    chrome_options.add_argument('--headless=new') 
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 봇 차단 우회 및 한글 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # GitHub Actions 환경 충돌 방지를 위한 드라이버 선언 예외 처리
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # 자동화 감지 우회 스크립트 추가
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        
        # [수정] 낮 시간대 레이턴시나 Cloudflare 지연을 고려해 대기 시간을 20초로 약간 상향
        time.sleep(20) 

        # 차단/로딩 여부 디버깅용 로그
        print(f"🌐 현재 접속된 페이지 제목: {driver.title}")

        # 모든 행(tr) 추출
        rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
        
        if not rows:
            print("⚠️ 테이블 행(tr)을 찾지 못했습니다. 차단되었거나 로딩 실패 상태입니다.")
            
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
        print(f"❌ 크롤링 내부 에러: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # [핵심 수정] 데이터 수집 실패 시 처리 로직 변경
    if not new_prices:
        print("🚨 이번 턴 데이터 수집 실패! 기존 데이터를 유지하고 종료합니다.")
        # exit(1)을 지우고 return으로 끝내서 GitHub Actions가 빨간불로 터지는 것을 방지합니다.
        return 

    # 무조건 한국 시간(UTC+9)으로 고정
    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
