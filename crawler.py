import os
import json
import time
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def get_lineage_prices():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')                    
    chrome_options.add_argument('--disable-dev-shm-usage')          
    chrome_options.add_argument('--disable-gpu')                 
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--lang=ko-KR')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(options=chrome_options)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    prices_data = []
    target_servers = ["데포로쥬", "켄라우헬", "에바", "데컨", "듀크데필"]

    try:
        for target in target_servers:
            current_price = "0원"
            change_status = "0%"
            
            try:
                # 한글 서버명을 URL 인코딩 처리
                encoded_target = quote(target)
                direct_url = f"https://enchant-lab.com/market/{encoded_target}"
                print(f"🌐 [{target}] 다이렉트 주소 이동 시도 ➔ https://enchant-lab.com/market/{target}")
                driver.get(direct_url)
                
                # 1. 대상 텍스트가 뜰 때까지 최대 15초 대기 (실패해도 pass 후 body 파싱 시도)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{target}')]"))
                    )
                except Exception:
                    pass

                time.sleep(3.0)  # 리액트 렌더링 마무리 대기

                # 2. 텍스트 추출 및 파싱
                body_elem = driver.find_element(By.TAG_NAME, "body")
                body_text = body_elem.text
                lines = [l.strip() for l in body_text.split('\n') if l.strip()]

                for i, line in enumerate(lines):
                    if target in line:
                        scan_zone = lines[max(0, i-4):min(len(lines), i+30)]
                        
                        for item in scan_zone:
                            if '원' in item and current_price == "0원":
                                if '평균' not in item and '최고' not in item and len(item) < 12:
                                    current_price = item
                            
                            if '%' in item and change_status == "0%":
                                if '상승권' not in item and len(item) < 10:
                                    change_status = item.replace('전일 대비', '').strip()
                        break

            except Exception as item_err:
                print(f"⚠️ {target} 서버 페이지 처리 중 예외 발생: {item_err}")

            prices_data.append({
                "source": target,
                "price": current_price,
                "status": change_status
            })
            print(f"📢 [수집 기록 완료] {target} ➔ 가격: {current_price} | 상태: {change_status}")

    except Exception as e:
        print(f"❌ 크롤링 치명적 에러 발생: {e}")
    finally:
        driver.quit()

    return prices_data

def update_json():
    new_prices = get_lineage_prices()
    
    # 0원 누락 데이터 확인
    failed_items = [p['source'] for p in new_prices if p['price'] == "0원"]
    if failed_items:
        print("\n" + "="*50)
        print(f"🚨 [빌드 실패] 시세 수집 누락 서버: {', '.join(failed_items)}")
        print("="*50 + "\n")
        exit(1)
        
    if len(new_prices) >= 2:
        all_same_price = all(p['price'] == new_prices[0]['price'] for p in new_prices)
        all_same_status = all(p['status'] == new_prices[0]['status'] for p in new_prices)
        if all_same_price or all_same_status:
            print("\n⚠️ [알림] 전 서버 수집 데이터가 동일합니다.")

    kst = timezone(timedelta(hours=9))
    current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')
    
    data = {"last_updated": current_time, "prices": new_prices}

    with open('market_stats.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"✅ 리니지 마켓 시세 업데이트 완료: {current_time}")

if __name__ == "__main__":
    update_json()
