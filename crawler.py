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

def parse_server_zone(lines, target):
    """전체 텍스트 줄 목록에서 해당 서버 구역을 찾아 최저가 및 등락률 추출"""
    price = "0원"
    status = "0%"

    for i, line in enumerate(lines):
        if line == target or line.strip() == target:
            # 서버명 아래 1~15줄 탐색
            zone = lines[i+1 : min(len(lines), i+15)]
            for item in zone:
                # 다른 서버명을 만나면 탐색 중단
                if item in ["파아그리오", "안타라스", "글루디오", "군터", "데포로쥬", "켄라우헬", "에바", "하딘", "발라카스", "오렌"]:
                    break

                # 1. 가격 추출 ('원' 포함, '평균'/'최고' 제외)
                if '원' in item and price == "0원":
                    if '평균' not in item and '최고' not in item:
                        digits = re.sub(r'[^\d]', '', item)
                        if digits and int(digits) > 0:
                            price = item.strip()

                # 2. 등락률 추출 ('%' 포함)
                if '%' in item and status == "0%":
                    if '상승' not in item:
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

        # 전체 목록 로딩 대기
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            pass

        # 렌더링 완료 대기 및 전체 리스트 확보
        time.sleep(5.0)

        body_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in body_text.split('\n') if l.strip()]

        for target in target_servers:
            price, status = parse_server_zone(lines, target)

            # 백업: 전체 텍스트 내 정규식 탐색
            if price == "0원" and target in body_text:
                t_idx = body_text.find(target)
                chunk = body_text[t_idx : t_idx + 350]
                p_match = re.findall(r'(\d{1,3}(?:,\d{3})*원)', chunk)
                for p in p_match:
                    p_clean = p.replace(',', '').replace('원', '')
                    if p_clean.isdigit() and int(p_clean) > 0:
                        price = p
                        break
                s_match = re.search(r'([+-]?\d+(?:\.\d+)?%)', chunk)
                if s_match:
                    status = s_match.group(1)

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
