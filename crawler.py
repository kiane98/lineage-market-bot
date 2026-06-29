import os
import json
import time
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

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
        
        # 기본 컴포넌트 로딩 대기 (최대 20초)
        wait = WebDriverWait(driver, 20)
        
        # 캡처본에 보이는 상단 서버 정렬 탭 버튼 영역이 뜰 때까지 대기
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '서버 정렬')]")))
        time.sleep(3)

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                print(f"🎯 [{target}] 서버 데이터 수집 시도 중...")
                
                # 1단계: 캡처본 상단에 나열된 수많은 서버 버튼 중 해당 서버이름 버튼 정밀 매칭
                # 태그가 button이든 div이든 텍스트가 정확히 일치하는 요소를 찾아 클릭합니다.
                button_xpath = f"//button[text()='{target}'] | //div[text()='{target}'] | //span[text()='{target}']"
                server_btn = wait.until(EC.element_to_be_clickable((By.XPATH, button_xpath)))
                
                # 안전한 자바스크립트 클릭 이벤트 주입
                driver.execute_script("arguments[0].click();", server_btn)
                time.sleep(3.5) # 클릭 후 하단에 최저가, 최고가 카드 UI판이 갱신되는 시간 충분히 확보

                # 2단계: 클릭 후 활성화된 하단 영역의 소스코드 파싱
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                # 캡처화면에 크게 나타난 대형 타이틀 구역(예: 발라카스 -9.2%) 추적
                # 서버 이름 바로 옆에 붙어있는 등락률(badge 또는 span)을 정확히 조준합니다.
                main_title_zone = soup.find(lambda tag: tag.name in ['h3', 'h2', 'p'] and target in tag.get_text())
                
                if main_title_zone:
                    # 해당 타이틀 블록을 포함한 하단 시세 요약 카드 박스 전체 텍스트 수집
                    parent_box = main_title_zone.find_parent(lambda tag: tag.name in ['div', 'section'])
                    if not parent_box:
                        parent_box = main_title_zone.parent.parent
                        
                    box_texts = parent_box.get_text(separator="\n").split('\n')
                    box_texts = [b.strip() for b in box_texts if b.strip()]
                    
                    print(f"🔍 [{target}] 활성화 구역 내부 텍스트 스캔: {box_texts}")

                    # 카드 안에서 '최저가' 글자 바로 다음에 나오는 가격 노출 데이터 가로채기
                    for idx, txt in enumerate(box_texts):
                        if '최저가' in txt and idx + 1 < len(box_texts):
                            next_txt = box_texts[idx+1]
                            if '원' in next_txt:
                                current_price = next_txt
                        
                        # % 등락률 데이터 가로채기
                        if '%' in txt and change_status == "0%":
                            change_status = txt

                # 3단계 백업: 만약 특정 카드 지정이 꼬였다면 본문 인접 줄바꿈 텍스트에서 강제 선별
                if current_price == "0원":
                    all_lines = soup.get_text(separator="\n").split('\n')
                    all_lines = [l.strip() for l in all_lines if l.strip()]
                    for i, line in enumerate(all_lines):
                        if line == target:
                            # 이름 발견 후 아래 10줄 스캔
                            for sub_line in all_lines[i:i+11]:
                                if '원' in sub_line and current_price == "0원" and len(sub_line) < 12:
                                    current_price = sub_line
                                if '%' in sub_line and change_status == "0%":
                                    change_status = sub_line
                            break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 클릭 제어 중 부분 렉/에러 발생: {item_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [최종 매칭 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 중복 복사 및 0원 유실 방지 최종 검증 장치
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 서버 정렬 탭 선택 후 화면 데이터 추출에 실패했습니다.")
        print("="*50 + "\n")
        exit(1)
        
    if len(new_prices) >= 2 and all(p['price'] == new_prices[0]['price'] for p in new_prices):
        print("\n🚨 [위험 감지] 모든 서버의 시세가 갱신되지 못하고 중복 복사되었습니다.")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
