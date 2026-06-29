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
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')
    
    # 봇 차단 우회 및 한글 설정
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as driver_err:
        print(f"⚠️ 기본 크롬 드라이버 실행 실패, 웹드라이버 매니저 시도: {driver_err}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(20) # 리액트 카드 컴포넌트 렌더링 완벽 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 서버 이름 태그(h3) 탐색
        server_elements = driver.find_elements(By.TAG_NAME, "h3")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for elem in server_elements:
            server_name = elem.text.strip()
            
            if any(target in server_name for target in target_servers):
                matched_target = next(target for target in target_servers if target in server_name)
                
                # [그물망 텍스트 추출] 
                # h3 기준으로 상위 5단계 조상 div까지 범위를 넓혀 카드 전체 구역의 텍스트를 일괄 수집합니다.
                card_text = []
                try:
                    # 상위 4~5단계 부모 div를 타겟팅하여 카드 내부를 전부 포괄
                    large_container = elem.find_element(By.XPATH, "./ancestor::div[position() <= 5]")
                    card_text = large_container.text.split('\n')
                except Exception:
                    # 예외 발생 시 주변 상위 텍스트 일괄 파싱
                    card_text = elem.find_element(By.XPATH, "..").text.split('\n')

                current_price = "0원"
                change_status = "0%"

                # 디버깅용 수집 로그 (어떤 텍스트가 잡혔는지 분석)
                print(f"🔍 [{matched_target}] 구역 내부에서 수집된 텍스트 목록: {card_text}")

                # 추출한 텍스트 배열에서 '원'과 '%' 추출
                for txt in card_text:
                    txt_clean = txt.strip()
                    if '원' in txt_clean and current_price == "0원":
                        current_price = txt_clean
                    elif '%' in txt_clean:
                        change_status = txt_clean

                prices_data.append({
                    "source": matched_target,
                    "price": current_price,
                    "status": change_status
                })
                print(f"🎯 매칭 성공: {matched_target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    if not new_prices:
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 개편된 카드 컴포넌트 내부에서 데이터를 뽑아내지 못했습니다.")
        print("💡 원인 분석: 위 로그의 '수집된 텍스트 목록'에 '원'과 '%'가 제대로 찍혔는지 확인하세요.")
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
