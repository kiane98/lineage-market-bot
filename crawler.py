import os
import json
import time
import re
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--lang=ko-KR')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(options=chrome_options)

    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

def parse_server_data(lines, target):
    """
    화면 텍스트 구조:
    [서버명]
    평균 1,963원 · HEAT 49.6
    1,835원   <-- 실제 현재가
    -3.2%     <-- 실제 등락률
    """
    price = "0원"
    status = "0%"

    all_servers = [
        "안타라스", "파아그리오", "글루디오", "아스테어", "오렌", "크리스터", 
        "에바", "데포로쥬", "발라카스", "사이하", "하딘", "발센", "어레인", 
        "세바스챤", "하이네", "가드리아", "이실로테", "캐스톨", "오웬", "린델", 
        "켄라우헬", "아툰", "데컨", "마프르", "군터", "질리언", "로엔그린", 
        "듀크데필", "케레니스", "조우", "아인하사드"
    ]

    for i, line in enumerate(lines):
        if line.strip() == target:
            # 대상 서버명 다음 라인부터 다음 서버명이 나오기 전까지 슬라이스
            card_lines = []
            for sub_line in lines[i+1 : min(len(lines), i+15)]:
                clean = sub_line.strip()
                if clean in all_servers and clean != target:
                    break
                card_lines.append(clean)

            # 슬라이스된 구역 내 파싱
            for item in card_lines:
                # 1. 가격 추출 ('평균', '최고' 단어가 들어간 줄은 엄격히 제외)
                if '원' in item and price == "0원":
                    if '평균' not in item and '최고' not in item:
                        # 숫자와 쉼표, 원만 남겨서 가격 형태인지 검증
                        digits = re.sub(r'[^\d]', '', item)
                        if digits and int(digits) > 0 and len(digits) <= 6:
                            price = item

                # 2. 등락률 추출 (+, -, % 패턴)
                if '%' in item and status == "0%":
                    if '상승' not in item and '하락' not in item:
                        match = re.search(r'([+-]?\d+(?:\.\d+)?%)', item)
                        if match:
                            status = match.group(1)

            break

    return price, status

def get_lineage_prices():
    target_servers = ["파아그리오", "안타라스", "글루디오", "군터", "데포로쥬"]
    prices_data = []

    driver = get_driver()

    try:
        main_url = "https://enchant-lab.com/market"
        print(f"🌐 [마켓 통합 페이지] 1회 접속 시도 ➔ {main_url}")
        driver.get(main_url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            pass

        time.sleep(5.0)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]

        for target in target_servers:
            price, status = parse_server_data(lines, target)

            prices_data.append({
                "source": target,
                "price": price,
                "status": status
            })
            print(f"📢 [수집 기록 완료] {target} ➔ 가격: {price} | 상태: {status}")

    except Exception as e:
        print(f"❌ 크롤링 치명적 에러: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()

    failed_items = [p['source'] for p in new_prices if p['price'] == "0원"]
    if failed_items:
        print("\n" + "="*50)
        print(f"🚨 [빌드 실패] 시세 수집 누락 서버: {', '.join(failed_items)}")
        print("="*50 + "\n")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')

    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
