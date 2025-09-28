from app import app, Guest

with app.app_context():
    guests = Guest.query.limit(10).all()
    if not guests:
        print("No guests found in DB")
    else:
        print("id\tname\tphone\tmessage_sent\ttoken")
        for g in guests:
            token = getattr(g, 'token', None) or getattr(g, 'unique_token', None)
            print(f"{g.id}\t{g.name}\t{g.phone}\t{getattr(g, 'message_sent', None)}\t{token}")
