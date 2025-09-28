from time import sleep
from selenium.common.exceptions import NoSuchElementException

from whatsapp_bot import WhatsAppBot


def main():
    print('Starting WhatsApp helper...')
    bot = WhatsAppBot()
    ok = bot.setup_driver()
    if not ok:
        print('Failed to setup driver')
        return

    print('Opening https://web.whatsapp.com ...')
    bot.driver.get('https://web.whatsapp.com')

    print('Polling for login (will check every 5s for up to 10 minutes).')
    max_tries = 120
    for i in range(max_tries):
        try:
            # check for chat list or conversation panel
            el = bot.driver.find_element('css selector', '[data-testid="chat-list"]')
            if el:
                print('\n✅ WhatsApp Web appears logged in (chat-list found).')
                print('You can now close this helper or let it run while messages are sent.')
                return
        except Exception:
            pass
        try:
            el2 = bot.driver.find_element('css selector', '[data-testid="conversation-panel-messages"]')
            if el2:
                print('\n✅ WhatsApp Web appears logged in (conversation panel found).')
                return
        except Exception:
            pass

        if i % 6 == 0:
            print(f'Waiting... ({i*5}s elapsed) - please scan the QR in the opened Chrome window if you haven\'t yet.')
        sleep(5)

    print('\n❌ Timeout waiting for WhatsApp login (10 minutes).')
    print('If you see a Chrome window but cannot scan QR, check for any Chrome already running using the same profile or try deleting the whatsapp_profile folder to force a fresh profile.')


if __name__ == '__main__':
    main()
