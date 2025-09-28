# דוגמאות שימוש

## הוספת אורחים בצורה מהירה

```python
from app import app, Guest, db
import uuid

# נתונים לדוגמה
guests_data = [
    {"name": "משה כהן", "phone": "+972501234567", "invited_count": 2},
    {"name": "שרה לוי", "phone": "+972502345678", "invited_count": 4},
    {"name": "דוד יעקב", "phone": "+972503456789", "invited_count": 1},
    {"name": "רבקה אברהם", "phone": "+972504567890", "invited_count": 3},
]

# הוספה אוטומטית
with app.app_context():
    for guest_data in guests_data:
        guest = Guest(
            name=guest_data["name"],
            phone=guest_data["phone"],
            unique_token=str(uuid.uuid4()),
            invited_count=guest_data["invited_count"]
        )
        db.session.add(guest)
    
    db.session.commit()
    print(f"נוספו {len(guests_data)} אורחים בהצלחה!")
```

## שליחת הזמנות לאורחים ספציפיים

```python
from whatsapp_bot import WhatsAppBot
from app import app, Guest

with app.app_context():
    bot = WhatsAppBot()
    
    # שליחה לאורח ספציפי
    guest = Guest.query.filter_by(name="משה כהן").first()
    if guest:
        bot.send_invitation(guest)
    
    # שליחה לפי מספר טלפון
    guest = Guest.query.filter_by(phone="+972501234567").first()
    if guest:
        bot.send_invitation(guest)
```

## יצירת שולחנות בצורה אוטומטית

```python
from app import app, Table, db

# יצירת 10 שולחנות
with app.app_context():
    for i in range(1, 11):
        table = Table(
            table_number=i,
            capacity=8,
            description=f"שולחן {i}" if i <= 5 else f"שולחן משפחה {i-5}"
        )
        db.session.add(table)
    
    db.session.commit()
    print("נוצרו 10 שולחנות בהצלחה!")
```

## דוחות וסטטיסטיקות

```python
from app import app, Guest, db
from sqlalchemy import func

with app.app_context():
    # סטטיסטיקות בסיסיות
    total_guests = Guest.query.count()
    confirmed = Guest.query.filter_by(is_attending=True).count()
    declined = Guest.query.filter_by(is_attending=False).filter(Guest.response_date.isnot(None)).count()
    pending = Guest.query.filter(Guest.response_date.is_(None)).count()
    
    print(f"סך הכל אורחים: {total_guests}")
    print(f"אישרו הגעה: {confirmed}")
    print(f"דחו: {declined}")
    print(f"ממתינים לתגובה: {pending}")
    
    # סך מגיעים
    total_attending = db.session.query(func.sum(Guest.confirmed_count)).filter_by(is_attending=True).scalar() or 0
    print(f"סך המגיעים: {total_attending}")
    
    # אורחים לפי מספר מוזמנים
    by_invited = db.session.query(Guest.invited_count, func.count(Guest.id)).group_by(Guest.invited_count).all()
    print("\nפילוח לפי מספר מוזמנים:")
    for invited_count, guest_count in by_invited:
        print(f"{invited_count} מוזמנים: {guest_count} אורחים")
```

## בדיקת תקינות נתונים

```python
from app import app, Guest
import re

def validate_phone_numbers():
    """בדיקת תקינות מספרי טלפון"""
    with app.app_context():
        guests = Guest.query.all()
        invalid_phones = []
        
        phone_pattern = r'^(\+972|0)[1-9]\d{8}$'
        
        for guest in guests:
            clean_phone = re.sub(r'[-\s]', '', guest.phone)
            if not re.match(phone_pattern, clean_phone):
                invalid_phones.append((guest.name, guest.phone))
        
        if invalid_phones:
            print("מספרי טלפון לא תקינים:")
            for name, phone in invalid_phones:
                print(f"- {name}: {phone}")
        else:
            print("כל מספרי הטלפון תקינים!")

# הפעלת הבדיקה
validate_phone_numbers()
```

## ייצוא נתונים ל-Excel

```python
import pandas as pd
from app import app, Guest

def export_to_excel():
    """ייצוא רשימת אורחים ל-Excel"""
    with app.app_context():
        guests = Guest.query.all()
        
        data = []
        for guest in guests:
            data.append({
                'שם': guest.name,
                'טלפון': guest.phone,
                'מוזמנים': guest.invited_count,
                'מגיעים': guest.confirmed_count if guest.is_attending else 0,
                'סטטוס': 'מגיע' if guest.is_attending else ('לא מגיע' if guest.response_date else 'ממתין'),
                'תאריך תגובה': guest.response_date.strftime('%d/%m/%Y %H:%M') if guest.response_date else '',
                'הערות': guest.notes or '',
                'שולחן': guest.table_number or ''
            })
        
        df = pd.DataFrame(data)
        df.to_excel('guest_list.xlsx', index=False)
        print("הקובץ נשמר בשם: guest_list.xlsx")

# הפעלת הייצוא (דורש התקנת pandas: pip install pandas openpyxl)
# export_to_excel()
```

## יצירת QR codes עבור כל האורחים

```python
import qrcode
import os
from app import app, Guest

def generate_all_qr_codes():
    """יצירת קוד QR עבור כל אורח"""
    with app.app_context():
        guests = Guest.query.all()
        
        if not os.path.exists('qr_codes'):
            os.makedirs('qr_codes')
        
        for guest in guests:
            qr_url = f"http://localhost:5000/rsvp/{guest.unique_token}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            filename = f"qr_codes/{guest.name.replace(' ', '_')}_qr.png"
            img.save(filename)
        
        print(f"נוצרו {len(guests)} קודי QR בתיקייה qr_codes/")

# הפעלת היצירה
# generate_all_qr_codes()
```

## אלגוריתם פשוט לסידור ישיבה

```python
from app import app, Guest, Table, db

def auto_assign_tables():
    """הקצאה אוטומטית של אורחים לשולחנות"""
    with app.app_context():
        # אורחים שאישרו הגעה וללא שולחן
        unassigned_guests = Guest.query.filter_by(is_attending=True, table_number=None).all()
        tables = Table.query.order_by(Table.table_number).all()
        
        for guest in unassigned_guests:
            guest_count = guest.confirmed_count
            
            # חיפוש שולחן עם מספיק מקום
            for table in tables:
                # חישוב מקומות תפוסים בשולחן
                occupied = db.session.query(db.func.sum(Guest.confirmed_count))\
                    .filter_by(table_number=table.table_number, is_attending=True)\
                    .scalar() or 0
                
                available_seats = table.capacity - occupied
                
                if available_seats >= guest_count:
                    guest.table_number = table.table_number
                    print(f"הוקצה {guest.name} ({guest_count} אנשים) לשולחן {table.table_number}")
                    break
            else:
                print(f"לא נמצא מקום עבור {guest.name} ({guest_count} אנשים)")
        
        db.session.commit()
        print("סיום הקצאה אוטומטית")

# הפעלת האלגוריתם
# auto_assign_tables()
```

## שליחת הודעות מותאמות אישית

```python
from whatsapp_bot import WhatsAppBot
from app import app, Guest
import os

class CustomBot(WhatsAppBot):
    def send_custom_message(self, guest, message_type="invitation"):
        """שליחת הודעה מותאמת אישית"""
        if not self.client:
            return False
        
        invitation_link = f"{self.website_url}/rsvp/{guest.unique_token}"
        couple_names = os.getenv('COUPLE_NAMES', 'החתן והכלה')
        
        messages = {
            "invitation": f"""
🎉 {guest.name}, אתם מוזמנים לחתונה! 🎉

השמחה של {couple_names}
👫 מוזמנים: {guest.invited_count} אנשים

אישור הגעה: {invitation_link}

בואו תחגגו איתנו! 💕
            """,
            
            "reminder": f"""
🔔 {guest.name}, תזכורת חשובה!

עדיין לא קיבלנו אישור הגעה לחתונה של {couple_names}

קישור לאישור: {invitation_link}

נשמח לדעת אם תגיעו! ❤️
            """,
            
            "thank_you": f"""
💐 תודה {guest.name}!

קיבלנו את אישור ההגעה שלכם לחתונה.
זה יהיה יום מדהים עם כולכם!

מחכים לכם! 🥂
            """
        }
        
        message_body = messages.get(message_type, messages["invitation"]).strip()
        
        try:
            message = self.client.messages.create(
                body=message_body,
                from_=self.from_whatsapp_number,
                to=f'whatsapp:{guest.phone}'
            )
            print(f"✅ הודעה מותאמת נשלחה ל-{guest.name}")
            return True
        except Exception as e:
            print(f"❌ שגיאה: {str(e)}")
            return False

# שימוש
def send_thank_you_messages():
    """שליחת הודעות תודה לאורחים שאישרו הגעה"""
    with app.app_context():
        bot = CustomBot()
        confirmed_guests = Guest.query.filter_by(is_attending=True).all()
        
        for guest in confirmed_guests:
            bot.send_custom_message(guest, "thank_you")

# הפעלה
# send_thank_you_messages()
```