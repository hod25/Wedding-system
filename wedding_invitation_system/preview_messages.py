from app import app, Guest
from whatsapp_bot import WhatsAppBot

with app.app_context():
    for gid in (1,2):
        g = Guest.query.get(gid)
        if not g:
            print(f"Guest {gid} not found")
            continue
        bot = WhatsAppBot()
        print(f"\n--- Preview for guest id={g.id} ({g.name}) ---")
        print(bot.build_invitation_text(g))
