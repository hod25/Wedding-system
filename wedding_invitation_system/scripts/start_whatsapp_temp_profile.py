import tempfile
import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def main():
    tempdir = tempfile.mkdtemp(prefix='wa_profile_')
    print('Created temporary Chrome profile at:', tempdir)

    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(f'--user-data-dir={tempdir}')
    chrome_options.add_argument('--start-maximized')

    print('Starting Chrome (this will open a new window). Please do NOT close it.')
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print('Failed to start ChromeDriver:', e)
        shutil.rmtree(tempdir, ignore_errors=True)
        return

    try:
        driver.get('https://web.whatsapp.com')
        print('Chrome opened. Please scan the QR code from your phone (WhatsApp -> Linked devices -> Link a device).')

        timeout = 600  # seconds
        poll = 5
        elapsed = 0
        while elapsed < timeout:
            try:
                # check for chat list or conversation panel
                if driver.find_elements(By.CSS_SELECTOR, '[data-testid="chat-list"]'):
                    print('\n✅ Logged in: chat list found.')
                    print('Temporary profile path (keeps session while this script runs):', tempdir)
                    print('Leaving browser open. When done, close the browser window to end the session and then you can delete the temp folder if desired.')
                    return
                if driver.find_elements(By.CSS_SELECTOR, '[data-testid="conversation-panel-messages"]'):
                    print('\n✅ Logged in: conversation panel found.')
                    print('Temporary profile path (keeps session while this script runs):', tempdir)
                    return
            except Exception:
                pass

            if elapsed % 30 == 0:
                print(f'Waiting for login... ({elapsed}s elapsed).')
            time.sleep(poll)
            elapsed += poll

        print('\n❌ Timeout waiting for login (10 minutes).')
        print('If you see the QR but cannot scan, try closing other Chrome instances or delete the existing whatsapp_profile folder and retry.')
    finally:
        # do not auto-delete tempdir here; leave it so the session can persist while browser open
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()
