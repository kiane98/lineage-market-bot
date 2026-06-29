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
        time.sleep(15) # 리액트 메모리 데이터 완벽 로딩 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 화면이 아니라 숨겨진 페이지 소스코드 텍스트 전체를 타격
        html_source = driver.page_source

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"

            # [정밀 타격 정규식 규칙]
            # 형님이 보내주신 원본 소스를 보면 "serverId":"데포로쥬"... "lowestPrice":1490 형태 외에도
            # 난독화 문자열 사이에 "데포로쥬", "1,490원", "+1.7%" 구조가 1열로 인접하여 배치되어 있습니다.
            # 서버이름 기준 뒤쪽 500글자를 잘라내어 해당 구역 안에서만 매칭시킵니다 (중복 완전 차단).
            idx = html_source.find(f'"{target}"')
            if idx != -1:
                chunk = html_source[idx:idx+600]
                
                # 1. 시세 가격 추출 (난독화된 따옴표나 숫자를 일괄 포착)
                # lowestPrice 뒤에 붙는 순수 숫자 또는 문자열 형태의 시세값 포착
                price_match = re.search(r'"lowestPrice"\s*:\s*"?(\d+)"?', chunk)
                if price_match:
                    price_num = int(price_match.group(1))
                    current_price = f"{price_num:,}원"
                else:
                    # 백업: 문자열 내에 콤마가 포함된 가격 텍스트가 있을 경우 강제 매칭
                    text_price_match = re.search(r'([\d,]+원)', chunk)
                    if text_price_match:
                        current_price = text_price_match.group(1)

                # 2. 등락률 변동값 추출
                # deltaPercent 속성값 또는 부호(+, -)가 포함된 독립 백분율 매칭
                delta_match = re.search(r'"deltaPercent"\s*:\s*"?([-\d.]+)"?', chunk)
                if delta_match:
                    delta_val = float(delta_match.group(1))
                    if delta_val > 0:
                        change_status = f"+{delta_val}%"
                    elif delta_val < 0:
                        change_status = f"{delta_val}%"
                    else:
                        change_status = "+0.0%"
                else:
                    # 백업: % 기호가 들어간 문자열 추출
                    text_delta_match = re.search(r'([+-][\d.]+\%)', chunk)
                    if text_delta_match:
                        change_status = text_delta_match.group(1)

            # [최종 방어선] 정규식이 완전히 빗나갔을 경우를 대비한 완전 일치 텍스트 크롤링 백업
            if current_price == "0원":
                lines = driver.execute_script("return document.documentElement.innerText;").split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == target:
                        for sub in lines[i:i+15]:
                            if '원' in sub and current_price == "0원" and '평균' not in sub and '최고' not in sub:
                                current_price = sub.strip()
                            if '%' in sub and change_status == "0%" and '상승권' not in sub:
                                change_status = sub.strip()
                        break

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [소스 매칭 가로채기 성공] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 누락(0원) 방지 최종 안전장치
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n🚨 [최종 빌드 실패] 데이터 추출 중 0원 누락이 발견되었습니다.")
        exit(1)
        
    # 중복 복사 완전 방어 벨트: 가격이나 상태가 전부 똑같이 카피되었다면 오염 데이터로 인지하고 차단
    if len(new_prices) >= 2:
        all_same_price = all(p['price'] == new_prices[0]['price'] for p in new_prices)
        all_same_status = all(p['status'] == new_prices[0]['status'] for p in new_prices)
        if all_same_price or all_same_status:
            print("\n🚨 [위험 감지] 서버 간 데이터 중복 복사 징후가 포착되어 빌드를 안전하게 다운시킵니다.")
            exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
