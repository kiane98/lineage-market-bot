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
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(15) # 내부 자바스크립트 완전 적재 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 브라우저의 전체 소스코드를 가져옵니다.
        page_source = driver.page_source

        # 타겟팅할 5개 서버
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # [치트키] Next.js 서버 데이터 청크(__next_f.push) 영역을 정규식으로 직접 슬라이싱합니다.
        # 화면의 활성화 상태(발라카스 온)에 상관없이 28개 전체 데이터가 숨겨진 텍스트 구역입니다.
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"

            # 서버 이름 기준으로 뒤에 오는 데이터 문자열 블록 매칭
            pattern = rf'"{target}"[^}}]+'
            match = re.search(pattern, page_source)

            if match:
                chunk = match.group(0)
                
                # 1. 최저가(lowestPrice) 숫자 데이터 정밀 추출
                price_match = re.search(r'"lowestPrice":\s*(\d+)', chunk)
                if price_match:
                    price_num = int(price_match.group(1))
                    current_price = f"{price_num:,}원"

                # 2. 등락률(deltaPercent) 숫자 데이터 정밀 추출 및 부호화
                delta_match = re.search(r'"deltaPercent":\s*([-\d.]+)', chunk)
                if delta_match:
                    delta_val = float(delta_match.group(1))
                    if delta_val > 0:
                        change_status = f"+{delta_val}%"
                    elif delta_val < 0:
                        change_status = f"{delta_val}%"
                    else:
                        change_status = "+0.0%"

            # [3차 방어선] 만약 난독화 때문에 실패한 경우를 대비해 화면에 있는 글자를 한 번 더 긁어보는 백업 로직
            if current_price == "0원":
                lines = driver.execute_script("return document.documentElement.innerText;").split('\n')
                for idx, line in enumerate(lines):
                    if line.strip() == target:
                        # 주변 10줄 스캔하여 매칭
                        sub_lines = lines[idx:idx+10]
                        for sl in sub_lines:
                            if '원' in sl and current_price == "0원": current_price = sl.strip()
                            if '%' in sl: change_status = sl.strip()
                        break

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [백엔드 완전 추출 성공] {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 5개 타겟 서버 중 데이터가 하나라도 유실(0원)되었다면 안전하게 홀딩 처리
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 개편된 백엔드 원본 소스에서 시세 검증이 누락되었습니다.")
        print("="*50 + "\n")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
