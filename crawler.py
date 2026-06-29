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
    
    driver.execute_cmd_cmd = driver.execute_cdp_cmd # 하위 호환성 유지
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []

    try:
        url = "https://enchant-lab.com/market"
        driver.get(url)
        time.sleep(20) # 완전히 로딩될 때까지 넉넉하게 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 형님이 찾으신 서버 이름 태그(h3)를 전부 수집
        server_elements = driver.find_elements(By.TAG_NAME, "h3")
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        if not server_elements:
            print("⚠️ [위험] 페이지에서 h3 태그를 찾지 못했습니다. 레이아웃이 완전히 뒤엎어졌을 수 있습니다.")

        for elem in server_elements:
            server_name = elem.text.strip()
            
            # 타겟 서버 명칭 검사
            if any(target in server_name for target in target_servers):
                matched_target = next(target for target in target_servers if target in server_name)
                
                # [지능형 텍스트 블록 추출]
                # h3 태그를 포함한 상위 카드 전체(부모 div)의 텍스트를 통째로 긁어 배열로 분리합니다.
                try:
                    # h3를 감싸는 직계 혹은 상위 조상 div 찾기
                    parent_card = elem.find_element(By.XPATH, "./ancestor::div[1]")
                    card_text = parent_card.text.split('\n')
                    
                    # 만약 긁어온 텍스트가 너무 짧으면 한 단계 더 위 부모 탐색
                    if len(card_text) < 2:
                        parent_card = elem.find_element(By.XPATH, "./ancestor::div[2]")
                        card_text = parent_card.text.split('\n')
                except Exception:
                    # 부모 탐색 실패 시 h3 기준 주변 영역 강제 추출
                    card_text = elem.find_element(By.XPATH, "..").text.split('\n')

                current_price = "0원"
                change_status = "0%"

                # 긁어온 텍스트 카드 안에서 가격과 변동률 파싱
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
    
    # 실패 시 명확하게 원인을 짚고 exit(1)로 깃허브 액션을 멈춤
    if not new_prices:
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 변경된 카드형 UI에서 가격/변동률 텍스트 추출에 실패했습니다.")
        print("💡 원인 분석: 서버 이름(h3)은 찾았으나 내부 부모 태그 텍스트 파싱 범위가 좁았을 수 있습니다.")
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
