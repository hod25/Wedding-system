"""Remote-mode WhatsApp bot.

Runs locally and talks to the hosted Flask app via the bot API endpoints:
  GET  /api/bot/pending        - fetch guests to send messages to
  POST /api/bot/mark           - report successes / failures
  GET  /api/bot/logs?limit=50  - (optional) view recent logs

Usage:
  1. Set environment variables (put in .env next to this file):
      BOT_API_KEY=YOUR_SECRET_KEY
      REMOTE_BASE_URL=https://your-deployed-site.example.com
      WEBSITE_URL=https://your-deployed-site.example.com
       COUPLE_NAMES=הוד ונעם
       WEDDING_DATE=01/01/2026
  2. Run first time with wait so you can scan QR and preserve session:
       python whatsapp_bot_remote.py send_all --wait
  3. Subsequent runs can be without --wait if profile persisted.

Notes:
  * Stores WhatsApp profile in ./whatsapp_profile_remote so session stays logged in.
  * Respects --headless flag (off by default so you can see the browser). Add --headless to run invisible.
  * Safe delays & randomization to mimic human behaviour.
"""
from __future__ import annotations
import os
import time
import random
import json
import argparse
from typing import List, Dict, Any
from dotenv import load_dotenv

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException

load_dotenv()

REMOTE_BASE_URL = os.getenv('REMOTE_BASE_URL', 'http://localhost:5000')
BOT_API_KEY = os.getenv('BOT_API_KEY')
WEBSITE_URL = os.getenv('WEBSITE_URL', REMOTE_BASE_URL)
COUPLE_NAMES = os.getenv('COUPLE_NAMES', 'הזוג')
WEDDING_DATE = os.getenv('WEDDING_DATE', '')
SESSION_DIR = os.path.abspath('whatsapp_profile_remote')
HEADLESS_DEFAULT = False

# ------------- HTTP helpers -------------

def api_get(path: str, **params):
    url = REMOTE_BASE_URL.rstrip('/') + path
    headers = {'X-API-KEY': BOT_API_KEY} if BOT_API_KEY else {}
    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def api_post(path: str, payload: Dict[str, Any]):
    url = REMOTE_BASE_URL.rstrip('/') + path
    headers = {'X-API-KEY': BOT_API_KEY, 'Content-Type': 'application/json'} if BOT_API_KEY else {'Content-Type': 'application/json'}
    r = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers, timeout=60)
    r.raise_for_status()
    return r.json()

# ------------- Selenium helpers -------------

def human_type(el, text: str, base_delay: float = 0.05):
    for ch in text:
        el.send_keys(ch)
        time.sleep(base_delay + random.uniform(0.0, 0.07))

class RemoteWhatsAppBot:
    def __init__(self, headless: bool = HEADLESS_DEFAULT):
        self.driver = None
        self.headless = headless
        self.is_logged_in = False

    def setup_driver(self) -> bool:
        opts = Options()
        if self.headless:
            opts.add_argument('--headless=new')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--disable-blink-features=AutomationControlled')
        opts.add_experimental_option('excludeSwitches', ['enable-automation'])
        opts.add_experimental_option('useAutomationExtension', False)
        if not os.path.exists(SESSION_DIR):
            os.makedirs(SESSION_DIR, exist_ok=True)
        opts.add_argument(f'--user-data-dir={SESSION_DIR}')
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            return True
        except Exception as e:
            print(f'❌ Failed to start Chrome: {e}')
            return False

    def wait_for_login(self, timeout: int = 300) -> bool:
        if not self.driver and not self.setup_driver():
            return False
        self.driver.get('https://web.whatsapp.com')
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self.driver.find_elements(By.CSS_SELECTOR, '#pane-side'):
                    self.is_logged_in = True
                    print('✅ WhatsApp logged in')
                    return True
                if int(time.time() - start) % 20 == 0:
                    print('⏳ Waiting for QR scan...')
            except Exception:
                pass
            time.sleep(2.5)
        print('❌ Login timeout')
        return False

    def open_chat(self, phone_no_plus: str) -> bool:
        url = f'https://web.whatsapp.com/send?phone={phone_no_plus}&type=phone_number&app_absent=0'
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#main')))
            return True
        except Exception:
            print(f'❌ Cannot open chat for {phone_no_plus}')
            return False

    def get_box(self):
        selectors = [
            (By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]'),
            (By.CSS_SELECTOR, '#main div[contenteditable="true"]'),
            (By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]'),
        ]
        for by, sel in selectors:
            try:
                return WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((by, sel)))
            except Exception:
                continue
        return None

    def send_message(self, text: str) -> bool:
        box = self.get_box()
        if not box:
            print('❌ No compose box')
            return False
        try:
            human_type(box, text)
        except WebDriverException:
            try:
                self.driver.execute_script("arguments[0].textContent = arguments[1]; arguments[0].dispatchEvent(new InputEvent('input', {bubbles:true}));", box, text)
            except Exception as e2:
                print(f'❌ Fallback insert failed: {e2}')
                return False
        time.sleep(random.uniform(0.6, 1.4))
        try:
            box.send_keys(Keys.ENTER)
            time.sleep(random.uniform(0.8, 1.4))
            return True
        except Exception as e:
            print(f'⚠️ Enter failed: {e}')
            return False

    @staticmethod
    def normalize_phone(p: str) -> str:
        digits = ''.join(ch for ch in p if ch.isdigit() or ch == '+')
        if digits.startswith('+'):
            digits = digits[1:]
        if digits.startswith('0'):
            digits = '972' + digits[1:]
        return digits

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            print('🔐 Driver closed')

# ------------- Invitation text helper (server already provides message, but keep fallback) -------------

def fallback_message(data_guest: Dict[str, Any]) -> str:
    token = data_guest.get('unique_token')
    link = f"{WEBSITE_URL.rstrip('/')}/rsvp/{token}" if token else WEBSITE_URL
    parts = [f"שלום {data_guest.get('name')}", f"מוזמנים ל{COUPLE_NAMES}"]
    if WEDDING_DATE:
        parts.append(f"תאריך: {WEDDING_DATE}")
    parts.append(f"אישור הגעה: {link}")
    return '\n'.join(parts)

# ------------- Core loop -------------

def send_cycle(limit: int, headless: bool, dry_run: bool, resend_failed: bool):
    print(f"🔄 Fetching up to {limit} guests (resend_failed={resend_failed}) ...")
    params = {'limit': limit}
    if resend_failed:
        params['resend'] = '1'
    try:
        pending = api_get('/api/bot/pending', **params)
    except Exception as e:
        print(f'❌ API error: {e}')
        return
    if not pending.get('success'):
        print('❌ API responded with failure:', pending)
        return
    guests = pending.get('guests', [])
    if not guests:
        print('✅ No guests to send')
        return

    print(f"📤 Will attempt {len(guests)} sends")
    bot = RemoteWhatsAppBot(headless=headless)
    if not bot.wait_for_login(timeout=300):
        bot.close()
        return

    sent_ids: List[int] = []
    failed: List[Dict[str, Any]] = []

    for idx, g in enumerate(guests, 1):
        phone = bot.normalize_phone(g.get('phone',''))
        print(f"[{idx}/{len(guests)}] {g.get('name')} -> {phone}")
        message_text = g.get('message') or fallback_message(g)
        if dry_run:
            print('🧪 DRY RUN message preview:\n' + message_text)
            sent = True
        else:
            if not bot.open_chat(phone):
                failed.append({'id': g.get('id'), 'error': 'open_chat_failed'})
                continue
            ok = bot.send_message(message_text)
            if ok:
                sent = True
            else:
                sent = False
        if sent:
            sent_ids.append(g.get('id'))
            # Random human-like pause
            time.sleep(random.uniform(5, 11))
        else:
            failed.append({'id': g.get('id'), 'error': 'send_failed'})
            time.sleep(random.uniform(3, 6))

    bot.close()
    print(f"📦 Reporting results: {len(sent_ids)} sent, {len(failed)} failed")
    try:
        resp = api_post('/api/bot/mark', {'sent': sent_ids, 'failed': failed})
        print('🗒 Mark response:', resp)
    except Exception as e:
        print('❌ Failed to report results:', e)

# ------------- CLI -------------

def main():
    parser = argparse.ArgumentParser(description='Remote WhatsApp Bot')
    sub = parser.add_subparsers(dest='cmd')

    p_send = sub.add_parser('send_all', help='Send invitations to pending guests')
    p_send.add_argument('--limit', type=int, default=15)
    p_send.add_argument('--headless', action='store_true')
    p_send.add_argument('--dry-run', action='store_true')
    p_send.add_argument('--resend-failed', action='store_true')

    p_loop = sub.add_parser('loop', help='Continuous loop (poll every X seconds)')
    p_loop.add_argument('--interval', type=int, default=600, help='Seconds between cycles')
    p_loop.add_argument('--limit', type=int, default=15)
    p_loop.add_argument('--headless', action='store_true')

    p_file = sub.add_parser('send_file', help='Send messages from a local Excel/CSV file')
    p_file.add_argument('path', help='Path to .xlsx/.xls/.csv file')
    p_file.add_argument('--sheet', help='Sheet name or index (for Excel)', default=None)
    p_file.add_argument('--phone-col', help='Column name that contains phone numbers (default: phone or נייד)', default=None)
    p_file.add_argument('--name-col', help='Column name for recipient name (default: name or שם)', default=None)
    p_file.add_argument('--message-col', help='Column name for message text (default: personal_message or message)', default=None)
    p_file.add_argument('--dry-run', action='store_true', help='Do not actually send messages')

    args = parser.parse_args()

    if not BOT_API_KEY:
        print('⚠️ BOT_API_KEY not set – API calls will likely fail (unauthorized). Set it in .env.')

    if args.cmd == 'send_all':
        send_cycle(limit=args.limit, headless=args.headless, dry_run=args.dry_run, resend_failed=args.resend_failed)
    elif args.cmd == 'send_file':
        from pathlib import Path
        import pandas as pd

        path = Path(args.path)
        if not path.exists():
            print(f'❌ File not found: {path}')
            return

        # read file
        try:
            if path.suffix.lower() in ('.xlsx', '.xls'):
                df = pd.read_excel(path, sheet_name=args.sheet, engine='openpyxl')
            else:
                df = pd.read_csv(path)
        except Exception as e:
            print(f'❌ Failed reading file: {e}')
            return

        # flexible column selection
        def find_col(preferred):
            if args.phone_col and args.phone_col in df.columns:
                return args.phone_col
            for cand in preferred:
                if cand in df.columns:
                    return cand
            return None

        phone_col = find_col([args.phone_col, 'phone', 'נייד', 'טלפון'])
        name_col = find_col([args.name_col, 'name', 'שם'])
        msg_col = find_col([args.message_col, 'personal_message', 'message', 'הודעה'])

        if not phone_col:
            print('❌ Could not find a phone column. Use --phone-col to specify the column name.')
            return

        bot = RemoteWhatsAppBot(headless=False)
        if not bot.wait_for_login(timeout=300):
            bot.close(); return

        sent = []
        failed = []
        for idx, row in df.iterrows():
            raw_phone = str(row.get(phone_col, '') or '')
            phone = bot.normalize_phone(raw_phone)
            name = str(row.get(name_col, '') or '')
            message = ''
            if msg_col and msg_col in df.columns:
                message = str(row.get(msg_col) or '')
            if not message:
                # fallback to simple template
                link = f"{WEBSITE_URL.rstrip('/')}/rsvp/{row.get('unique_token') or ''}"
                message = f"שלום {name}!\nנשמח לאישור הגעה כאן: {link}"

            print(f'Sending to {name} -> {phone}')
            if args.dry_run:
                print('DRY RUN:')
                print(message[:200])
                sent.append(None)
                continue

            if not bot.open_chat(phone):
                failed.append({'phone': raw_phone, 'error': 'open_chat_failed'})
                continue
            ok = bot.send_message(message)
            if ok:
                sent.append(raw_phone)
            else:
                failed.append({'phone': raw_phone, 'error': 'send_failed'})
            time.sleep(random.uniform(4, 9))

        bot.close()
        print(f'Finished. Sent: {len(sent)}, Failed: {len(failed)}')
    elif args.cmd == 'loop':
        while True:
            send_cycle(limit=args.limit, headless=args.headless, dry_run=False, resend_failed=False)
            print(f'⏲ Sleeping {args.interval}s...')
            time.sleep(args.interval)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
