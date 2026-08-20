import os
import json
import time
import re
from urllib.parse import quote
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

def parse_server_data(text, target):
    """전체 텍스트에서 해당 서버명 주변의 가격 및 등락률을 정규식으로 안전하게 추출"""
    price = "0원"
    status = "0%"

    # 1. 서버명이 등장하는 위치 탐색
    if target not in text:
        return price, status

    # 서버명 이후 300자 내외 구역 슬라이싱
    target_idx = text.find(target)
    chunk = text[target_idx:target_idx + 400]

    # 가격 패턴: 1~4자리 숫자(쉼표 포함) + 원 (예: 1,850원, 700원)
    price_matches = re.findall(r'(\d{1,3}(?:,\d{3})*원)', chunk)
    for p in price_matches:
        # '평균 2,091원' 등 라벨이 붙은 가격을 거르고 순수 최저/기준 가격 타겟팅
        p_clean = p.replace(',', '').replace('원', '')
        if p_clean.isdigit() and int(p_clean) > 0:
            price = p
            # 첫 번째 발견된 가격이 보통 해당 서버의 기준 시세
            break

    # 등락률 패턴: (+/-)숫자.% (예: +14.8%, -11.4%, +0.0%, 0%)
    status_matches = re.findall(r'([+-]?\d+(?:\.\d+)?%)', chunk)
    if status_matches:
        status = status_matches[0]

    return price, status

def get_lineage_prices():
    target_servers = ["파아그리오", "안타라스", "글루디오", "군터", "데포로쥬"]
    prices_data = []

    driver = get_driver()

    try:
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"

            try:
                encoded_target = quote(target)
                direct_url = f"https://enchant-lab.com/market/{encoded_target}"
                print(f"🌐 [{target}] 다이렉트 주소 이동 시도 ➔ https://enchant-lab.com/market/{target}")

                # 페이지 이동
                driver.get(direct_url)

                # 페이지 렌더링 완료 대기 (최대 12초)
                try:
                    WebDriverWait(driver, 12).until(
                        EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{target}')]"))
                    )
                except Exception:
                    pass

                # 리액트 상태 업데이트 안정화 대기
                time.sleep(4.0)

                body_text = driver.find_element(By.TAG_NAME, "body").text

                # 1차 정규식 파싱 시도
                current_price, change_status = parse_server_data(body_text, target)

                # 만약 파싱 실패 시, 줄 단위 백업 탐색
                if current_price == "0원":
                    lines = [l.strip() for l in body_text.split('\n') if l.strip()]
                    for i, line in enumerate(lines):
                        if target in line:
                            scan_zone = lines[max(0, i-2):min(len(lines), i+25)]
                            for item in scan_zone:
                                if '원' in item and current_price == "0원":
                                    if '평균' not in item and '최고' not in item and len(item) < 12:
                                        current_price = item
                                if '%' in item and change_status == "0%":
                                    if '상승' not in item and len(item) < 10:
                                        change_status = item.replace('전일 대비', '').strip()
                            break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 처리 중 예외 발생: {item_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [수집 기록 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

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
