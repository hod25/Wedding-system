"""
דוגמה מהירה להפעלת המערכת
ריצה: python quick_start.py
"""

from app import app, Guest, Table, db
import uuid

def create_sample_data():
    """יצירת נתוני דוגמה"""
    with app.app_context():
        # בדיקה אם כבר יש נתונים
        if Guest.query.count() > 0:
            print("כבר יש נתונים במערכת")
            return
        
        # אורחים לדוגמה
        sample_guests = [
            {"name": "משה כהן", "phone": "+972501234567", "invited_count": 2},
            {"name": "שרה לוי", "phone": "+972502345678", "invited_count": 4},
            {"name": "דוד יעקב", "phone": "+972503456789", "invited_count": 1},
            {"name": "רבקה אברהם", "phone": "+972504567890", "invited_count": 3},
            {"name": "יוסף מרדכי", "phone": "+972505678901", "invited_count": 2},
            {"name": "מרים גולדמן", "phone": "+972506789012", "invited_count": 5},
        ]
        
        print("יוצר אורחי דוגמה...")
        for guest_data in sample_guests:
            guest = Guest(
                name=guest_data["name"],
                phone=guest_data["phone"],
                unique_token=str(uuid.uuid4()),
                invited_count=guest_data["invited_count"]
            )
            db.session.add(guest)
        
        # שולחנות לדוגמה
        print("יוצר שולחנות דוגמה...")
        for i in range(1, 6):
            table = Table(
                table_number=i,
                capacity=8,
                description=f"שולחן {i}"
            )
            db.session.add(table)
        
        db.session.commit()
        print(f"נוצרו {len(sample_guests)} אורחים ו-5 שולחנות בהצלחה!")
        
        # הדפסת קישורי דוגמה
        print("\n🔗 קישורי RSVP לדוגמה:")
        guests = Guest.query.all()
        for guest in guests[:3]:  # 3 ראשונים
            print(f"- {guest.name}: http://localhost:5000/rsvp/{guest.unique_token}")

if __name__ == "__main__":
    print("🎉 מתחיל הקמת מערכת ניהול חתונה...")
    
    # יצירת נתוני דוגמה
    create_sample_data()
    
    print("\n✅ המערכת מוכנה!")
    print("🌐 הפעל את השרת עם: python app.py")
    print("📱 לאחר הגדרת Twilio, הפעל: python whatsapp_bot.py send_all")
    print("📋 עדכן את קובץ .env עם הפרטים שלך")