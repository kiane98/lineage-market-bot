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
        time.sleep(15) # 내부 데이터 변수 완전 적재 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # [마스터키] 브라우저 page_source 내부 텍스트 소스 전체를 문자열로 확보
        html_source = driver.page_source

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # 제공자 소스코드에서 각 서버별 데이터 스냅샷(JSON 객체 형태의 텍스트)을 정밀 타격
        # 예시 구조: {"serverId":"데포로쥬","serverName":"데포로쥬","lowestPrice":1490,"averagePrice":1506,...,"deltaPercent":1.7}
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"

            # 정규식 조건: 서버이름 뒤에 따라오는 데이터 문자열을 최소 범위로 정확히 가두어 긁어냅니다.
            # Next.js 내부 데이터 청크가 어떤 특수기호로 쪼개지든 값을 유연하게 찾아내는 마감 처리입니다.
            pattern = rf'"{target}"[^}}]+'
            match = re.search(pattern, html_source)

            if match:
                chunk = match.group(0)
                
                # 1. 최저가(lowestPrice) 값 추출 및 세 자릿수 콤마 전처리
                # 제공자가 화면에 "1,506원" 평균가를 띄우더라도 백엔드 순수 최저가 숫자인 1490원 등을 정확히 타격합니다.
                price_match = re.search(r'"lowestPrice":\s*(\d+)', chunk)
                if price_match:
                    price_num = int(price_match.group(1))
                    current_price = f"{price_num:,}원"

                # 2. 등락률(deltaPercent) 값 추출 및 부호 규격 복원 (+ / -)
                delta_match = re.search(r'"deltaPercent":\s*([-\d.]+)', chunk)
                if delta_match:
                    delta_val = float(delta_match.group(1))
                    if delta_val > 0:
                        change_status = f"+{delta_val}%"
                    elif delta_val < 0:
                        change_status = f"{delta_val}%"
                    else:
                        change_status = "+0.0%"

            # [백업 방어선] 정규식이 가끔 공백 문자로 놓치면 브라우저 자바스크립트 엔진 내부 검색 가동
            if current_price == "0원":
                try:
                    js_find = f"""
                    const scripts = Array.from(document.querySelectorAll('script'));
                    for (let s of scripts) {{
                        const content = s.textContent;
                        if (content.includes('{target}')) {{
                            const pIdx = content.indexOf('"lowestPrice"', content.indexOf('{target}'));
                            if (pIdx !== -1) {{
                                const num = content.substring(pIdx).match(/\\d+/)[0];
                                return num;
                            }}
                        }}
                    }}
                    return '';
                    """
                    fallback_num = driver.execute_script(js_find)
                    if fallback_num and fallback_num.isdigit():
                        current_price = f"{int(fallback_num):,}원"
                except Exception:
                    pass

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [백엔드 데이터 완전 분리] {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 5개 타겟 서버 중 단 하나라도 수집이 누락(0원)되거나 실패하면 빌드를 홀딩시켜 구 버전 작동 상태 유지
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 리액트 원본 데이터 영역에서 가격 파싱 검증이 실패했습니다.")
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
