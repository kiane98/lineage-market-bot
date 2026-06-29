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
        time.sleep(15) # Next.js 내부 데이터 스크립트 적재 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # 1단계: Next.js 프레임워크가 숨겨놓은 마스터 데이터 스크립트 태그 타격
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        next_data_script = soup.find('script', id='__NEXT_DATA__')

        # 2단계: 만약 해당 태그가 있다면 통째로 JSON 파싱 (가장 깨끗한 정석 방식)
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                # Next.js 내부 구조를 타고 들어가서 28개 서버 스냅샷 데이터 배열 확보
                # 일반적인 Next.js의 pageProps 내부에서 marketData나 snapshots 위치를 추적합니다.
                props = json_data.get('props', {}).get('pageProps', {})
                
                # 데이터 통이 묶여있는 키값 유연하게 탐색
                market_data = props.get('marketData', props.get('initialState', {}).get('market', {}))
                snapshots = market_data.get('snapshots', [])
                
                if snapshots:
                    target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]
                    for target in target_servers:
                        for snap in snapshots:
                            if snap.get('serverName') == target or snap.get('serverId') == target:
                                price_num = snap.get('lowestPrice', 0)
                                delta_val = snap.get('deltaPercent', 0.0)
                                
                                current_price = f"{price_num:,}원" if price_num else "0원"
                                change_status = f"+{delta_val}%" if delta_val > 0 else f"{delta_val}%"
                                if delta_val == 0: change_status = "+0.0%"
                                
                                prices_data.append({
                                    "source": target,
                                    "price": current_price,
                                    "status": change_status
                                })
                                print(f"🎯 [마스터 JSON 파싱 성공] {target} | 가격: {current_price} | 상태: {change_status}")
                                break
            except Exception as json_err:
                print(f"⚠️ JSON 구조 파싱 지연/실패: {json_err}")

        # 3단계 [완벽 방어망]: 2단계가 막혔을 때를 대비해, 문자열 소스 전체에서 타겟 서버 텍스트 강제 슬라이싱 파싱
        if not prices_data:
            print("💡 3단계 텍스트 가로채기 방어선 가동...")
            page_text = driver.page_source
            target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]
            
            for target in target_servers:
                current_price = "0원"
                change_status = "0%"
                
                # 서버명 뒤에 붙는 객체 구역을 잘라내어 가격과 등락률을 1:1 독립 매칭
                import re
                idx = page_text.find(f'"{target}"')
                if idx != -1:
                    chunk = page_text[idx:idx+300] # 서버명 기준 뒤쪽 300자만 안전하게 격리
                    
                    price_match = re.search(r'"lowestPrice"\s*:\s*(\d+)', chunk)
                    if price_match:
                        current_price = f"{int(price_match.group(1)):,}원"
                        
                    delta_match = re.search(r'"deltaPercent"\s*:\s*([-\d.]+)', chunk)
                    if delta_match:
                        dv = float(delta_match.group(1))
                        change_status = f"+{dv}%" if dv > 0 else f"{dv}%"
                        if dv == 0: change_status = "+0.0%"
                
                prices_data.append({
                    "source": target,
                    "price": current_price,
                    "status": change_status
                })
                print(f"🎯 [텍스트 격리 분리 성공] {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 중복 복사 방지용 추가 검증 장치: 가격이나 상태가 전부 똑같다면 빌드를 실패시켜 안전하게 홀딩
    if new_prices and len(new_prices) >= 2:
        all_same_price = all(p['price'] == new_prices[0]['price'] for p in new_prices)
        if all_same_price and new_prices[0]['price'] != "0원":
            print("\n🚨 [위험 감지] 모든 서버의 시세가 동일하게 중복 복사되었습니다. 빌드를 중단합니다.")
            exit(1)
            
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n🚨 [최종 빌드 실패] 일부 서버의 시세가 0원으로 누락되었습니다.")
        exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
