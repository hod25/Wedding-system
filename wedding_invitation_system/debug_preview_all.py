from app import app, Guest
from whatsapp_bot import WhatsAppBot

with app.app_context():
    guests = Guest.query.all()
    bot = WhatsAppBot()
    print(f"Found {len(guests)} guests")
    for g in guests:
        token = getattr(g, 'token', None) or getattr(g, 'unique_token', None) or getattr(g, 'uniqueToken', None)
        print('---')
        print(f'id={g.id} name={g.name!r} phone={g.phone!r} token={token!r} message_sent={g.message_sent}')
        if not token:
            print('!! MISSING TOKEN - invite link will be broken')
        print('\nInvitation text preview:\n')
        print(bot.build_invitation_text(g))
        print('\nReminder text preview:\n')
        print(bot.build_reminder_text(g))
