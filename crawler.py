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
        time.sleep(15) # 스크립트 데이터 로딩 완전 대기

        print(f"🌐 [체크] 현재 접속된 페이지 제목: '{driver.title}'")

        # [치트키 로직] 화면 레이아웃 무시하고, Next.js 자바스크립트가 소스코드에 심어놓은 원본 텍스트 데이터 추출
        html_source = driver.page_source
        
        target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

        for target in target_servers:
            current_price = "0원"
            change_status = "0%"

            # 1단계: 소스코드 텍스트 내부에서 정규식으로 서버의 원본 시세 스냅샷 데이터 강제 추출
            # 예: {"serverId":"데포로쥬","serverName":"데포로쥬","lowestPrice":1490 ... "deltaPercent":1.7}
            pattern = rf'"{target}"[^}}]+'
            match = re.search(pattern, html_source)

            if match:
                chunk = match.group(0)
                
                # 최저가(lowestPrice) 숫자 추출
                price_match = re.search(r'"lowestPrice":\s*(\d+)', chunk)
                if price_match:
                    price_num = int(price_match.group(1))
                    current_price = f"{price_num:,}원"

                # 등락률(deltaPercent) 숫자 추출 및 부호 복원
                delta_match = re.search(r'"deltaPercent":\s*([-\d.]+)', chunk)
                if delta_match:
                    delta_val = float(delta_match.group(1))
                    if delta_val > 0:
                        change_status = f"+{delta_val}%"
                    elif delta_val < 0:
                        change_status = f"{delta_val}%"
                    else:
                        change_status = "+0.0%"

            # 2단계 방어선: 만약 정규식 매칭 실패 시 브라우저 내 인접 엘리먼트 텍스트 강제 수집
            if current_price == "0원":
                try:
                    find_fallback = f"""
                    const elements = Array.from(document.querySelectorAll('*'));
                    const targetEl = elements.find(el => el.innerText === '{target}');
                    if(targetEl) {{
                        return targetEl.closest('a')?.innerText || targetEl.parentElement?.innerText || '';
                    }}
                    return '';
                    """
                    fallback_text = driver.execute_script(find_fallback)
                    if fallback_text:
                        lines = [l.strip() for l in fallback_text.split('\n') if l.strip()]
                        for line in lines:
                            if '원' in line and current_price == "0원": current_price = line
                            if '%' in line: change_status = line
                except Exception:
                    pass

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"🎯 [백엔드 원본 타격] {target} | 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 내부 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 5개 서버 데이터가 모두 정상적으로 ('0원' 없이) 수집되었는지 최종 검증
    if not new_prices or any(p['price'] == "0원" for p in new_prices):
        print("\n" + "="*50)
        print("🚨 [최종 빌드 실패] 일부 타겟 서버 데이터 수집이 유실되었습니다. 위 로그를 확인하세요.")
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
