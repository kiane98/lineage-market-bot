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
        
        # 데이터가 브라우저 내부 메모리에 완벽히 안착할 때까지 대기
        time.sleep(15) 

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # [마스터 탈취 키] 브라우저 콘솔창 내부의 리액트/넥스트 하이드레이션 객체를 직접 해독
        # 화면의 정렬 버튼 상태나 탭 클릭 여부와 관계없이 28개 서버 원본 배열을 강제로 뽑아냅니다.
        js_extract_script = """
        try {
            // 1안: Next.js 스크립트 데이터 영역 파싱
            const nextEl = document.querySelector('#__NEXT_DATA__');
            if (nextEl) {
                const data = JSON.parse(nextEl.textContent);
                const props = data.props?.pageProps || {};
                const list = props.marketData?.snapshots || props.initialState?.market?.snapshots || props.snapshots;
                if (list && list.length > 0) return list;
            }
            
            # 2안: 화면 내에 바인딩된 글로벌 데이터 저장소 추적
            if (window.__NEXT_DATA__?.props?.pageProps?.snapshots) return window.__NEXT_DATA__.props.pageProps.snapshots;
        } catch(e) {}
        return null;
        """
        
        raw_snapshots = driver.execute_script(js_extract_script)
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        # 성공적으로 객체를 낚아챘다면 JSON 매핑 진행
        if raw_snapshots and isinstance(raw_snapshots, list):
            print(f"📦 [엔진 타격 성공] 내부 메모리에서 {len(raw_snapshots)}개의 서버 원본 데이터를 통째로 가로채기 완료했습니다.")
            for target in target_servers:
                matched = False
                for snap in raw_snapshots:
                    s_name = snap.get('serverName', snap.get('serverId', ''))
                    if s_name == target:
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
                        print(f"🎯 [객체 매칭 완벽 성공] {target} ➔ 가격: {current_price} | 상태: {change_status}")
                        matched = True
                        break
        
        # [최후의 보루: 광역 그물망 스캔] 
        # 만약 보안 패치로 내부 객체가 안 꺼내진다면, 브라우저 화면의 돔(DOM) 트리를 순회하며 이름 기반 텍스트 크롤링 가동
        if not prices_data:
            print("💡 4차 최종 방어선 (글로벌 돔 텍스트 정밀 추적) 가동...")
            html = driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 페이지의 모든 텍스트 요소를 조각내어 순서 정렬
            all_lines = soup.get_text(separator="\n").split('\n')
            all_lines = [l.strip() for l in all_lines if l.strip()]
            
            for target in target_servers:
                current_price = "0원"
                change_status = "0%"
                
                for i, line in enumerate(all_lines):
                    if line == target or target in line:
                        # 이름 매칭 부근 20줄을 확장 스캔하여 엉뚱한 평균/최고가 제외하고 최저가만 필터링
                        sub_range = all_lines[max(0, i-5):i+20]
                        for item in sub_range:
                            if '원' in item and current_price == "0원" and '평균' not in item and '최고' not in item and len(item) < 12:
                                current_price = item
                            if '%' in item and change_status == "0%" and '상승권' not in item:
                                change_status = item
                        
                # 겉화면에 등락률 부호가 잘려있다면 전일 대비 글자 정제
                change_status = change_status.replace('전일 대비', '').strip()
                prices_data.append({
                    "source": target,
                    "price": current_price,
                    "status": change_status
                })
                print(f"🎯 [돔 스캔 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 0원 누락 리스크 방지 최종 세이프티 벨트
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 개편된 Next.js 스트리밍 돔에서 데이터를 수집하지 못했습니다.")
        print("="*50 + "\n")
        exit(1)
        
    # 데이터 오염(전부 같은 값 복사) 방지 벨트
    if len(new_prices) >= 2:
        all_same_price = all(p['price'] == new_prices[0]['price'] for p in new_prices)
        all_same_status = all(p['status'] == new_prices[0]['status'] for p in new_prices)
        if all_same_price or all_same_status:
            print("\n🚨 [위험 감지] 서버 간 데이터 중복 복사 버그가 감지되어 빌드를 정지합니다.")
            exit(1)

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 한국 시간 기준 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
