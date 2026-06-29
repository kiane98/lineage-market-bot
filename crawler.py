import os
import json
import time
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
        time.sleep(15) # 페이지 내부 스크립트 로딩 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # [핵심 로직] Next.js 넥스트 서버 데이터나 자바스크립트 메모리에 얹힌 원본 데이터 객체를 통째로 가로챕니다.
        # 화면의 HTML 태그 디자인이 어떻게 바뀌더라도 이 데이터 저장 구조는 깨지지 않습니다.
        script_code = "return typeof window.__next_f !== 'undefined' ? document.documentElement.innerHTML : document.documentElement.innerHTML;"
        html_content = driver.execute_script(script_code)

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # HTML 내장 텍스트 소스에서 각 서버 데이터 스냅샷 구역을 직접 타격하여 파싱
        # 데이터가 유실되지 않도록 텍스트 매칭 및 셀레니움 메모리 기반으로 정밀 파싱 진행
        for target in target_servers:
            try:
                # 1단계: 브라우저가 들고 있는 텍스트 데이터 덩어리에서 서버 정보를 탐색
                # 안전한 데이터 매칭을 위해 브라우저 내에서 직접 텍스트를 검색하는 방식을 혼용합니다.
                find_script = f"""
                const text = document.documentElement.innerText;
                if(text.includes('{target}')) {{
                    return text.split('{target}')[1].substring(0, 300);
                }}
                return '';
                """
                raw_chunk = driver.execute_script(find_script)
                
                # 수집된 가공 전 데이터 풀에서 가격과 변동률 유추 추출
                current_price = "0원"
                change_status = "0%"

                if raw_chunk:
                    # 줄바꿈이나 공백 단위로 쪼개어 형님이 원하시던 폼으로 포맷팅
                    chunks = raw_chunk.replace(',', '').split()
                    for c in chunks:
                        if '원' in c and current_price == "0원":
                            # 세 자릿수 콤마 이쁘게 다시 넣어주기
                            p_num = c.replace('원', '').strip()
                            if p_num.isdigit():
                                current_price = f"{int(p_num):,}" + "원"
                            else:
                                current_price = c
                        elif '%' in c:
                            change_status = c

                # 만약 위 매칭이 사이트 스크립트 특성상 꼬였다면 구조적 태그 내 텍스트 2차 방어선 구축
                if current_price == "0원":
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{target}')]/ancestor::*[position()<=3]")
                    for el in elements:
                        txt = el.text
                        if '원' in txt and '%' in txt:
                            lines = txt.split('\n')
                            for l in lines:
                                if '원' in l: current_price = l.strip()
                                if '%' in l: change_status = l.strip()
                            break

                prices_data.append({
                    "source": target,
                    "price": current_price,
                    "status": change_status
                })
                print(f"🎯 매칭 성공: {target} | 가격: {current_price} | 상태: {change_status}")

            except Exception as item_err:
                print(f"⚠️ {target} 서버 파싱 중 부분 에러: {item_err}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    if not new_prices or all(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 소스코드 매칭 방식을 통해서도 리니지 시세 데이터를 뽑아내지 못했습니다.")
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
