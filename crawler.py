import os
import json
import time
import re
import requests
from datetime import datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def send_telegram_alert(message: str):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[Telegram] 토큰 또는 채팅 ID가 환경변수에 없습니다.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("[Telegram] 알림 전송 완료")
        else:
            print(f"[Telegram] 전송 실패: {res.text}")
    except Exception as e:
        print(f"[Telegram] 통신 오류: {e}")

def get_driver():
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
    return driver

def extract_server_data(full_text, target):
    price = "0원"
    status = "0%"

    pattern = rf"{target}\s+평균[^\n\r]*[\n\r]+\s*([0-9,]+원)\s*[\n\r]+\s*([+-]?[0-9.]+\%)"
    match = re.search(pattern, full_text)

    if match:
        price = match.group(1).strip()
        status = match.group(2).strip()
        return price, status

    if target in full_text:
        start_idx = full_text.find(target)
        chunk = full_text[start_idx : start_idx + 400]
        
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        for l in lines:
            if '원' in l and '평균' not in l and '최고' not in l and price == "0원":
                digits = re.sub(r'[^\d]', '', l)
                if digits and int(digits) > 0 and len(digits) <= 6:
                    price = l
            if '%' in l and '상승' not in l and '하락' not in l and status == "0%":
                m = re.search(r'([+-]?\d+(?:\.\d+)?%)', l)
                if m:
                    status = m.group(1)

    return price, status

def get_lineage_prices():
    target_servers = ["파아그리오", "안타라스", "글루디오", "군터", "데포로쥬"]
    prices_data = []

    driver = get_driver()

    try:
        main_url = "https://enchant-lab.com/market"
        print(f"🌐 [마켓 통합 페이지] 1회 접속 시도 ➔ {main_url}")
        driver.get(main_url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception:
            pass

        time.sleep(5.0)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        for target in target_servers:
            price, status = extract_server_data(body_text, target)

            prices_data.append({
                "source": target,
                "price": price,
                "status": status
            })
            print(f"📢 [수집 기록 완료] {target} ➔ 가격: {price} | 상태: {status}")

    except Exception as e:
        print(f"❌ 크롤링 치명적 에러: {e}")
        send_telegram_alert(
            f"🚨 <b>[리니지 크롤러] 실행 중단 에러</b>\n\n"
            f"• 에러 내용: <code>{str(e)}</code>"
        )
    finally:
        driver.quit()

    return prices_data

def update_json():
    try:
        new_prices = get_lineage_prices()

        failed_items = [p['source'] for p in new_prices if p['price'] == "0원"]
        if failed_items:
            err_msg = f"시세 수집 누락 서버: {', '.join(failed_items)}"
            print("\n" + "="*50)
            print(f"🚨 [빌드 실패] {err_msg}")
            print("="*50 + "\n")

            send_telegram_alert(
                f"🚨 <b>[리니지 아데나 수집 누락]</b>\n\n"
                f"• 사유: <code>{err_msg}</code>\n"
                f"• 조치: 0원 데이터 업데이트를 차단하기 위해 중단되었습니다."
            )
            exit(1)

        kst = timezone(timedelta(hours=9))
        current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M')

        data = {"last_updated": current_time, "prices": new_prices}

        with open('market_stats.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ 리니지 마켓 시세 업데이트 완료: {current_time}")

        # 정상 완료 텔레그램 리포트 발송
        price_lines = "\n".join([f"• <b>{p['source']}</b>: {p['price']} ({p['status']})" for p in new_prices])
        success_msg = (
            f"✅ <b>[리니지 클래식] 아데나 시세 갱신 성공</b>\n\n"
            f"{price_lines}\n\n"
            f"📅 갱신 시각: {current_time} (KST)"
        )
        send_telegram_alert(success_msg)

    except Exception as e:
        send_telegram_alert(
            f"🚨 <b>[리니지 업데이트 프로세스 예외]</b>\n\n"
            f"• 에러 내용: <code>{str(e)}</code>"
        )
        raise e

if __name__ == "__main__":
    update_json()
