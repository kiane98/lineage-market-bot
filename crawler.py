import os
import json
import time
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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
        
        # 리액트/Next.js의 복잡한 카드 렌더링이 완전히 끝날 때까지 25초로 대기 상향
        time.sleep(25) 

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 렌더링이 완료된 브라우저의 전체 소스를 BeautifulSoup에 주입
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # 페이지 내부의 모든 텍스트 요소를 수집하기 위해 본문 전체를 줄바꿈 단위로 완전 해체
        all_lines = soup.get_text(separator="\n").split('\n')
        all_lines = [l.strip() for l in all_lines if l.strip()]

        print(f"📄 [디버깅] 현재 메모리에 로드된 전체 텍스트 라인 수: {len(all_lines)}개")

        # [그물망 탐색 로직]
        # 서버 이름을 발견하면, 그 바로 아래 줄(인접한 15줄 이내)에 무조건 시세('원')와 등락률('%')이 순서대로 나옵니다.
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            for i, line in enumerate(all_lines):
                if line == target:
                    # 서버 이름을 찾았다면 그 주변 최대 15줄을 샅샅이 뒤집니다.
                    search_range = all_lines[i:i+16]
                    
                    for item in search_range:
                        if '원' in item and current_price == "0원":
                            current_price = item
                        elif '%' in item and change_status == "0%":
                            change_status = item
                    
                    # 원하는 데이터를 다 찾았다면 루프 조기 종료
                    if current_price != "0원" and change_status != "0%":
                        break

            # 2차 방어선: 만약 정확히 매칭이 안 풀렸다면 문맥 검색 적용
            if current_price == "0원":
                for line in all_lines:
                    if target in line and '원' in line:
                        # 한 줄에 서버이름과 가격이 같이 박힌 데이터 레이아웃 방어
                        current_price = line.replace(target, '').strip()

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [최종 매칭 결과] {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 가격이 '0원'으로 유실된 게 하나라도 있으면 구동 정지 및 알림 유도
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 개편된 텍스트 풀 구조에서 가격 추출에 실패했습니다.")
        print("💡 해결 팁: 위 로그에서 매칭 결과를 확인하고 로딩 대기 시간을 더 늘리거나 보정해야 합니다.")
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
