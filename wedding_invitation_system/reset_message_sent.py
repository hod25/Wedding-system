from app import app, Guest, db

with app.app_context():
    Guest.query.update({"message_sent": False})
    db.session.commit()
    print('Reset message_sent for all guests')
