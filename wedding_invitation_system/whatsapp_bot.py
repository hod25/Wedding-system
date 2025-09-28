"""
Robust WhatsApp bot for sending wedding invitations and reminders via WhatsApp Web.

Requires:
  pip install selenium webdriver-manager python-dotenv

Environment variables (optional):
  WEBSITE_URL, COUPLE_NAMES, WEDDING_DATE

This module expects an `app` module that exports `app` (Flask), `Guest` (ORM model), and `db` (SQLAlchemy).
Guest should have: name, phone, invited_count, token, message_sent (bool), response_date (nullable)
"""

import os
import time
import random
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from jinja2 import Template

# Import your Flask app and models
from app import app, Guest, db

load_dotenv()


def human_type(el, text: str, base_delay: float = 0.06):
    """Type text into element with small human-like delays."""
    for ch in text:
        el.send_keys(ch)
        time.sleep(base_delay + random.uniform(0.0, 0.08))


class WhatsAppBot:
    def __init__(self):
        self.website_url = os.getenv("WEBSITE_URL", "http://localhost:5000")
        self.driver = None
        self.is_logged_in = False

    def setup_driver(self) -> bool:
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        profile_path = os.path.join(os.getcwd(), "whatsapp_profile")
        chrome_options.add_argument(f"--user-data-dir={profile_path}")

        try:
            local_driver = os.path.join(os.getcwd(), "chromedriver.exe")
            if os.path.exists(local_driver):
                service = Service(local_driver)
            else:
                service = Service(ChromeDriverManager().install())

            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            # hide webdriver flag
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"❌ Error setting up ChromeDriver: {e}")
            return False

    def login_to_whatsapp(self, timeout: int = 60) -> bool:
        """Open WhatsApp Web and wait until chats load. Timeout in seconds."""
        if not self.driver and not self.setup_driver():
            return False
        # open WhatsApp Web and poll for an element that indicates logged-in state
        self.driver.get("https://web.whatsapp.com")

        poll = 3
        elapsed = 0
        selectors_logged_in = [
            '[data-testid="chat-list"]',
            '[data-testid="conversation-panel-messages"]',
            '#pane-side',
            'div[role="textbox"][contenteditable="true"]',
        ]
        selectors_qr = [
            'canvas[aria-label="Scan me!"]',
            'div[data-ref][data-testid] img',
        ]

        print(f'Opening WhatsApp Web and waiting up to {timeout}s for login...')
        while elapsed < timeout:
            try:
                # check logged-in indicators
                for sel in selectors_logged_in:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if els:
                        self.is_logged_in = True
                        print('✅ Detected logged-in state (selector matched):', sel)
                        return True

                # if not logged in, check whether QR is visible to guide the user
                for q in selectors_qr:
                    try:
                        if self.driver.find_elements(By.CSS_SELECTOR, q):
                            print(f'ℹ️ QR code detected on page (selector: {q}). Please scan the QR with your phone.')
                            break
                    except Exception:
                        continue

            except Exception:
                # ignore transient errors while page loads
                pass

            if elapsed % 15 == 0:
                print(f'Waiting for login... ({elapsed}s elapsed).')
            time.sleep(poll)
            elapsed += poll

        # timed out
        print('❌ Timeout: Could not detect WhatsApp Web login within the given time. Please ensure you scanned the QR in the opened browser (or try the temporary profile helper).')
        return False

    def verify_message_in_chat(self, text_snippet: str, timeout: int = 8) -> bool:
        """Wait up to `timeout` seconds for the sent message (containing text_snippet)
        to appear in the chat's message area. Returns True if found."""
        # First, poll the visible text of the main container for the snippet (robust if text is split)
        try:
            end = time.time() + timeout
            while time.time() < end:
                try:
                    main_text = self.driver.execute_script(
                        "var m = document.querySelector('#main'); return m ? m.innerText : '';"
                    )
                except Exception:
                    main_text = ''
                if main_text and text_snippet in main_text:
                    return True
                time.sleep(0.5)
        except Exception:
            pass

        # Fallback: try XPath search for nodes containing the snippet
        try:
            xpath = f"//*[@id='main']//*[contains(text(), \"{text_snippet}\")]"
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return True
        except Exception:
            return False

    def open_chat(self, phone_e164_no_plus: str) -> bool:
        # phone_e164_no_plus example: 972501234567 (without +)
        url = f"https://web.whatsapp.com/send?phone={phone_e164_no_plus}&type=phone_number&app_absent=0"
        self.driver.get(url)
        try:
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#main")))
            return True
        except Exception:
            print(f"❌ Failed to open chat for {phone_e164_no_plus}")
            return False

    def get_message_box(self):
        selectors = [
            (By.CSS_SELECTOR, '[data-testid="conversation-compose-box-input"]'),
            (By.CSS_SELECTOR, '#main div[contenteditable="true"]'),
            (By.XPATH, '//*[@id="main"]//footer//div[@contenteditable="true"]'),
        ]
        for by, sel in selectors:
            try:
                el = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((by, sel)))
                return el
            except Exception:
                continue
        return None

    def send_text_to_open_chat(self, text: str) -> bool:
        box = self.get_message_box()
        if not box:
            print("❌ Message box not found")
            return False
        # Try human-like typing first. Some ChromeDriver versions raise when
        # send_keys contains non-BMP characters (emoji). Fall back to a JS
        # paste into the contenteditable element if typing fails.
        try:
            human_type(box, text, 0.05)
        except WebDriverException as e:
            # Specific ChromeDriver error about BMP characters -> fallback
            msg = str(e)
            if 'only supports characters in the BMP' in msg or 'ChromeDriver only supports characters in the BMP' in msg:
                inserted = False
                # 1) Try document.execCommand('insertText') which many contenteditable accept
                try:
                    script = (
                        "arguments[0].focus(); document.execCommand('insertText', false, arguments[1]);"
                    )
                    self.driver.execute_script(script, box, text)
                    inserted = True
                    print('ℹ️ Inserted text via execCommand("insertText")')
                except Exception:
                    inserted = False

                # 2) If not inserted, try setting innerHTML with <br> for newlines
                if not inserted:
                    try:
                        # preserve paragraph breaks: map double-newline to double <br>
                        html = text.replace('\r\n', '\n')
                        html = html.replace('\n\n', '<br><br>')
                        html = html.replace('\n', '<br>')
                        script = (
                            "arguments[0].focus(); arguments[0].innerHTML = arguments[1];"
                            "arguments[0].dispatchEvent(new InputEvent('input', {bubbles: true}));"
                        )
                        self.driver.execute_script(script, box, html)
                        inserted = True
                        print('ℹ️ Inserted text via innerHTML fallback')
                    except Exception as e2:
                        print(f"❌ innerHTML fallback failed: {e2}")

                # 3) As another attempt, set textContent and dispatch events
                if not inserted:
                    try:
                        script = (
                            "arguments[0].focus(); arguments[0].textContent = arguments[1];"
                            "arguments[0].dispatchEvent(new InputEvent('input', {bubbles: true}));"
                        )
                        self.driver.execute_script(script, box, text)
                        inserted = True
                        print('ℹ️ Inserted text via textContent fallback')
                    except Exception as e3:
                        print(f"❌ textContent fallback failed: {e3}")

                if not inserted:
                    print("❌ All JS insertion fallbacks failed")
                    return False
            else:
                # re-raise unexpected WebDriver exceptions
                raise

        # small pause then send. Ensure the box is focused first.
        try:
            time.sleep(random.uniform(0.8, 1.6))
            try:
                box.click()
            except Exception:
                pass

            # Log box content before sending for debugging
            try:
                content = box.get_attribute('textContent') or box.get_attribute('innerText') or ''
                print(f'ℹ️ Message box content preview (first100): {content[:100]!r}')
            except Exception:
                pass

            box.send_keys(Keys.ENTER)
            time.sleep(random.uniform(0.8, 1.2))
            print("ℹ️ Sent with Enter key (attempt)")
            return True
        except Exception as e_enter:
            # Fallback: try to locate and click the send button
            print(f"⚠️ Enter send failed: {e_enter}. Trying send-button fallback...")
            send_selectors = [
                (By.CSS_SELECTOR, 'button[data-testid="compose-btn-send"]'),
                (By.CSS_SELECTOR, 'button[aria-label="Send"]'),
                (By.CSS_SELECTOR, 'span[data-icon="send"]'),
            ]
            for by, sel in send_selectors:
                try:
                    btn = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                    try:
                        btn.click()
                        time.sleep(random.uniform(0.8, 1.2))
                        print(f"ℹ️ Sent by clicking send button (selector: {sel})")
                        return True
                    except Exception:
                        continue
                except Exception:
                    continue

            print("❌ Could not send message: Enter and send-button fallbacks failed")
            return False
        return False

    @staticmethod
    def normalize_phone(phone_raw: str) -> str:
        p = "".join(ch for ch in phone_raw if ch.isdigit() or ch == "+")
        if p.startswith("+"):
            p = p[1:]
        if p.startswith("0"):
            p = "972" + p[1:]
        return p

    def build_invitation_text(self, guest) -> str:
        couple_names = os.getenv("COUPLE_NAMES", "החתן והכלה")
        wedding_date = os.getenv("WEDDING_DATE", "תאריך החתונה")
        token = getattr(guest, 'token', None) or getattr(guest, 'unique_token', None) or getattr(guest, 'uniqueToken', None)
        invitation_link = f"{self.website_url}/rsvp/{token}"

        # Allow overriding the invitation text via a Jinja2 template file. If the
        # environment variable INVITATION_TEMPLATE_PATH is set, use it; otherwise
        # look for templates/invitation_template.txt in the project.
        template_path = os.getenv('INVITATION_TEMPLATE_PATH') or os.path.join('templates', 'invitation_template.txt')
        try:
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    tpl = Template(f.read())
                return tpl.render(
                    name=guest.name,
                    couple_names=couple_names,
                    wedding_date=wedding_date,
                    invited_count=guest.invited_count,
                    link=invitation_link,
                    guest=guest,
                )
        except Exception:
            # fall back to the default message if template rendering fails
            pass

        # Default fallback message
        return (
            f"🎉 הזמנה לחתונה! 🎉\n\n"
            f"שלום {guest.name}!\n\n"
            f"אנחנו שמחים להזמין אותך לחתונה של {couple_names}\n"
            f"📅 תאריך: {wedding_date}\n"
            f"👨‍👩‍👧‍👦 מוזמנים: {guest.invited_count}\n\n"
            f"בבקשה אשר/י הגעה בקישור:\n{invitation_link}\n\n"
            f"מחכים לכם! 💕"
        )

    def build_reminder_text(self, guest) -> str:
        token = getattr(guest, 'token', None) or getattr(guest, 'unique_token', None) or getattr(guest, 'uniqueToken', None)
        invitation_link = f"{self.website_url}/rsvp/{token}"
        return (
            f"היי {guest.name}, מזכירים בעדינות לאשר הגעה 🙏\n"
            f"הקישור: {invitation_link}\n"
            f"זה עוזר לנו מאוד בהושבה והקייטרינג. תודה 💙"
        )

    def send_invitation(self, guest) -> bool:
        if not self.is_logged_in and not self.login_to_whatsapp():
            return False

        phone = self.normalize_phone(guest.phone)
        if not phone.startswith("972"):
            print(f"⚠️ Unsupported/invalid phone: {guest.phone}")
            return False

        text = self.build_invitation_text(guest)
        if not self.open_chat(phone):
            return False

        ok = self.send_text_to_open_chat(text)
        if ok:
            # Verify the link/text appeared in the chat before updating DB
            # use the token link as a unique marker
            token = getattr(guest, 'token', None) or getattr(guest, 'unique_token', None) or getattr(guest, 'uniqueToken', None)
            link_snippet = f"/rsvp/{token}" if token else None
            verified = False
            if link_snippet:
                verified = self.verify_message_in_chat(link_snippet, timeout=10)

            if verified:
                try:
                    guest.message_sent = True
                    db.session.commit()
                except Exception:
                    db.session.rollback()
            else:
                print('⚠️ Sent but could not verify message in chat. message_sent not updated.')
        # random delay after sending to mimic human behavior
        time.sleep(random.uniform(5, 10))
        return ok

    def send_reminder(self, guest) -> bool:
        if not self.is_logged_in and not self.login_to_whatsapp():
            return False
        phone = self.normalize_phone(guest.phone)
        text = self.build_reminder_text(guest)
        if not self.open_chat(phone):
            return False
        ok = self.send_text_to_open_chat(text)
        time.sleep(random.uniform(5, 10))
        return ok

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            print("🔐 Driver closed")


def send_invitation_to_guest_id(guest_id: int):
    with app.app_context():
        guest = Guest.query.get(guest_id)
        if not guest:
            print(f"❌ No guest with id={guest_id}")
            return
        bot = WhatsAppBot()
        if not bot.login_to_whatsapp():
            print("❌ WhatsApp login failed")
            return
        print("Preview message:\n" + bot.build_invitation_text(guest))
        ok = bot.send_invitation(guest)
        print("✅ Sent" if ok else "❌ Failed")
        bot.close()


def send_invitations_to_all(wait_for_login: bool = False):
    with app.app_context():
        bot = WhatsAppBot()
        # allow longer time for interactive QR scan (300s = 5 minutes)
        if not bot.login_to_whatsapp(timeout=300):
            if wait_for_login:
                print("Please open the opened Chrome window and scan the QR code with your phone.")
                input("After scanning QR and seeing your chats, press Enter to continue...")
                if not bot.login_to_whatsapp(timeout=300):
                    print("❌ Still cannot detect WhatsApp login. Aborting.")
                    bot.close()
                    return
            else:
                print("❌ Cannot login to WhatsApp")
                bot.close()
                return
        guests_to_invite = Guest.query.filter_by(message_sent=False).all()
        if not guests_to_invite:
            print("✅ Everyone already invited")
            bot.close()
            return
        print(f"📤 Sending invitations to {len(guests_to_invite)} guests...")
        success = 0
        for i, guest in enumerate(guests_to_invite, 1):
            print(f"[{i}/{len(guests_to_invite)}] Sending to {guest.name} ({guest.phone})")
            if bot.send_invitation(guest):
                success += 1
            time.sleep(random.uniform(6, 14))
        print(f"✅ Sent {success} invitations out of {len(guests_to_invite)}")
        bot.close()


def send_reminders():
    with app.app_context():
        bot = WhatsAppBot()
        # allow longer time for interactive QR scan when started from API/subprocess
        if not bot.login_to_whatsapp(timeout=300):
            print("❌ Cannot login to WhatsApp")
            bot.close()
            return
        guests_no_response = Guest.query.filter_by(message_sent=True, response_date=None).all()
        if not guests_no_response:
            print("✅ No reminders needed")
            bot.close()
            return
        print(f"📤 Sending reminders to {len(guests_no_response)} guests...")
        success = 0
        for i, guest in enumerate(guests_no_response, 1):
            print(f"[{i}/{len(guests_no_response)}] Reminder to {guest.name} ({guest.phone})")
            if bot.send_reminder(guest):
                success += 1
            time.sleep(random.uniform(6, 14))
        print(f"✅ Sent {success} reminders")
        bot.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        wait_flag = '--wait' in sys.argv or '-w' in sys.argv
        if cmd == 'send_all':
            send_invitations_to_all(wait_for_login=wait_flag)
        elif cmd == 'send_reminders':
            send_reminders()  # reminders currently don't support interactive wait
        elif cmd == 'send_one' and len(sys.argv) >= 3:
            send_invitation_to_guest_id(int(sys.argv[2]))
        else:
            print("Usage: python whatsapp_bot.py [send_all|send_reminders|send_one <guest_id>] [--wait]")
    else:
        print("Usage: python whatsapp_bot.py [send_all|send_reminders|send_one <guest_id>]")