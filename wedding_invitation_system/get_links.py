"""
סקריפט לקבלת קישורים ייחודיים לכל האורחים
ריצה: python get_links.py
"""

from app import app, Guest
import os

def generate_guest_links():
    """יצירת קישורים ייחודיים לכל אורח"""
    with app.app_context():
        guests = Guest.query.all()
        website_url = os.getenv('WEBSITE_URL', 'http://localhost:5000')
        
        if not guests:
            print("❌ אין אורחים במערכת")
            return
        
        print(f"📋 רשימת קישורים ייחודיים עבור {len(guests)} אורחים:\n")
        print("=" * 80)
        
        # יצירת קובץ טקסט עם הקישורים
        with open('guest_links.txt', 'w', encoding='utf-8') as f:
            f.write("רשימת קישורים ייחודיים לאורחים\n")
            f.write("=" * 50 + "\n\n")
            
            for i, guest in enumerate(guests, 1):
                link = f"{website_url}/rsvp/{guest.unique_token}"
                
                # הדפסה למסך
                print(f"{i:2d}. {guest.name:<20} | {guest.phone:<15} | מוזמנים: {guest.invited_count}")
                print(f"    🔗 {link}")
                print(f"    📱 WhatsApp: https://wa.me/{guest.phone.replace('+', '').replace('-', '').replace(' ', '')}?text=שלום%20{guest.name.replace(' ', '%20')}!%20הנה%20הקישור%20לאישור%20הגעה:%20{link}")
                print()
                
                # כתיבה לקובץ
                f.write(f"{i}. {guest.name} ({guest.phone}) - מוזמנים: {guest.invited_count}\n")
                f.write(f"   קישור: {link}\n")
                f.write(f"   WhatsApp: https://wa.me/{guest.phone.replace('+', '').replace('-', '').replace(' ', '')}?text=שלום%20{guest.name.replace(' ', '%20')}!%20הנה%20הקישור%20לאישור%20הגעה:%20{link}\n")
                f.write("\n")
        
        print("=" * 80)
        print(f"✅ הקישורים נשמרו גם בקובץ: guest_links.txt")
        print("\n📱 דרכים לשליחה:")
        print("   1. העתק את הקישור לכל אורח ושלח ידנית")
        print("   2. לחץ על קישור WhatsApp לשליחה מהירה")
        print("   3. השתמש בבוט האוטומטי: python whatsapp_bot.py send_all")

def generate_guest_cards():
    """יצירת כרטיסיות להדפסה עם QR codes"""
    try:
        import qrcode
        from PIL import Image, ImageDraw, ImageFont
        
        with app.app_context():
            guests = Guest.query.all()
            website_url = os.getenv('WEBSITE_URL', 'http://localhost:5000')
            
            if not os.path.exists('invitation_cards'):
                os.makedirs('invitation_cards')
            
            print("🎨 יוצר כרטיסי הזמנה עם QR codes...")
            
            for guest in guests:
                # יצירת QR code
                qr_url = f"{website_url}/rsvp/{guest.unique_token}"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_url)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                # יצירת כרטיס
                card = Image.new('RGB', (800, 600), color='white')
                draw = ImageDraw.Draw(card)
                
                # הוספת טקסט
                try:
                    font_large = ImageFont.truetype("arial.ttf", 40)
                    font_medium = ImageFont.truetype("arial.ttf", 24)
                    font_small = ImageFont.truetype("arial.ttf", 18)
                except:
                    font_large = ImageFont.load_default()
                    font_medium = ImageFont.load_default()
                    font_small = ImageFont.load_default()
                
                # כותרת
                draw.text((400, 50), "הזמנה לחתונה", font=font_large, anchor="mm", fill="black")
                draw.text((400, 120), f"שלום {guest.name}!", font=font_medium, anchor="mm", fill="blue")
                draw.text((400, 170), f"מוזמנים: {guest.invited_count} אנשים", font=font_medium, anchor="mm", fill="black")
                
                # הוספת QR code
                qr_img = qr_img.resize((200, 200))
                card.paste(qr_img, (300, 250))
                
                draw.text((400, 480), "סרוק את הקוד או גש לקישור:", font=font_small, anchor="mm", fill="gray")
                draw.text((400, 510), qr_url, font=font_small, anchor="mm", fill="gray")
                
                # שמירת הכרטיס
                filename = f"invitation_cards/{guest.name.replace(' ', '_')}_invitation.png"
                card.save(filename)
            
            print(f"✅ נוצרו {len(guests)} כרטיסי הזמנה בתיקייה: invitation_cards/")
            
    except ImportError:
        print("⚠️  להפקת כרטיסים צריך להתקין: pip install Pillow")

if __name__ == "__main__":
    print("🎉 מערכת ניהול קישורי הזמנה\n")
    
    while True:
        print("בחר אפשרות:")
        print("1. הצג רשימת קישורים")
        print("2. צור כרטיסי הזמנה להדפסה")
        print("3. יציאה")
        
        choice = input("\nהבחירה שלך (1-3): ").strip()
        
        if choice == "1":
            generate_guest_links()
        elif choice == "2":
            generate_guest_cards()
        elif choice == "3":
            print("👋 ביי!")
            break
        else:
            print("❌ בחירה לא תקינה")
        
        input("\nלחץ Enter להמשך...")