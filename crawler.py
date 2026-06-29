import os
import json
import time
import re
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
        # 탭 분리 페이지로 안 가고 메인 마켓 주소로 안전하게 진입
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(12) # 소스코드 내부 하이드레이션 데이터가 안착할 시간 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 겉화면 글자가 아닌, 백엔드 데이터가 심어진 html_source 원본 획득
        html_source = driver.page_source

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"

            # [정밀 타격 규칙] 
            # 형님이 주신 Next.js 스트리밍 데이터 구조 특체 타격
            # 예: "serverId":"데포로쥬","serverName":"데포로쥬","lowestPrice":1400,"averagePrice":1463...,"deltaPercent":-6
            pattern = rf'"{target}"[^}}]+'
            match = re.search(pattern, html_source)

            if match:
                chunk = match.group(0)
                
                # 1. 최저가(lowestPrice) 순수 숫자 추출 및 세자리 콤마 처리
                price_match = re.search(r'"lowestPrice"\s*:\s*(\d+)', chunk)
                if price_match:
                    price_num = int(price_match.group(1))
                    current_price = f"{price_num:,}원"

                # 2. 등락률(deltaPercent) 순수 숫자 추출 및 부호 복원
                delta_match = re.search(r'"deltaPercent"\s*:\s*([-\d.]+)', chunk)
                if delta_match:
                    delta_val = float(delta_match.group(1))
                    if delta_val > 0:
                        change_status = f"+{delta_val}%"
                    elif delta_val < 0:
                        change_status = f"{delta_val}%"
                    else:
                        change_status = "+0.0%"

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [백엔드 오피셜 분리] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 안전 홀딩 벨트
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [빌드 실패] 백엔드 스크립트 소스에서 시세(0원)를 낚아채지 못했습니다.")
        print("="*50 + "\n")
        exit(1)
        
    if len(new_prices) >= 2 and all(p['price'] == new_prices[0]['price'] for p in new_prices):
        print("\n🚨 [위험 감지] 서버 간 데이터 중복 복사 징후 발생.")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
