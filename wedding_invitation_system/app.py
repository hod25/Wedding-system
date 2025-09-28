from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
import uuid
import os
import shutil
from dotenv import load_dotenv
import qrcode
from io import BytesIO
import base64
import pandas as pd
import tempfile
from werkzeug.utils import secure_filename

# טעינת משתני סביבה
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///wedding.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# הגדרת אזור הזמן
def get_local_time():
    """מחזיר את הזמן הנוכחי באזור זמן ישראל"""
    timezone = os.getenv('TIMEZONE', 'Asia/Jerusalem')
    israel_tz = pytz.timezone(timezone)
    return datetime.now(israel_tz)

# מודל האורחים
class Guest(db.Model):

# ...existing code...

# ====== כל הראוטים של Flask אחרי הגדרות מחלקות ======


# ====== כל הראוטים של Flask אחרי הגדרות מחלקות ======

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))  # כתובת מייל
    unique_token = db.Column(db.String(36), unique=True, nullable=False)
    invited_count = db.Column(db.Integer, default=1)  # כמה יגיעו
    confirmed_count = db.Column(db.Integer, default=0)  # כמה אישרו הגעה
    group_affiliation = db.Column(db.String(100))  # שיוך לקבוצה
    side = db.Column(db.String(50))  # מהצד של (חתן/כלה)
    attendance_status = db.Column(db.String(20), default='ממתין')  # יגיע/מתלבט/לא יגיע/ממתין
    estimated_gift_amount = db.Column(db.Float, default=0.0)  # סכום מתנה משוער
    is_attending = db.Column(db.Boolean, default=False)
    message_sent = db.Column(db.Boolean, default=False)
    response_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)  # הערות
    table_number = db.Column(db.Integer)  # לסידור ישיבה
    added_by = db.Column(db.String(20))  # מספר הטלפון של המשתמש שהוסיף
    created_at = db.Column(db.DateTime, default=get_local_time)

    def __repr__(self):
        return f'<Guest {self.name}>'

# מודל שולחנות
class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=8)
    description = db.Column(db.String(200))
    def __repr__(self):
        return f'<Table {self.table_number}>'

    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=8)
    description = db.Column(db.String(200))
    
    def __repr__(self):
        return f'<Table {self.table_number}>'


# ====== ראוט עריכת אורח ======
@app.route('/edit_guest/<int:guest_id>', methods=['GET', 'POST'])
def edit_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    if request.method == 'POST':
        guest.name = request.form['name']
        guest.phone = request.form['phone']
        guest.email = request.form.get('email', '').strip() or None
        guest.group_affiliation = request.form.get('group_affiliation', '').strip() or None
        guest.side = request.form.get('side', '').strip() or None
        guest.attendance_status = request.form.get('attendance_status', 'ממתין')
        guest.notes = request.form.get('notes', '').strip() or None
        try:
            guest.estimated_gift_amount = float(request.form.get('estimated_gift_amount', 0) or 0)
        except (ValueError, TypeError):
            guest.estimated_gift_amount = 0.0
        try:
            guest.invited_count = int(request.form.get('invited_count', 1) or 1)
        except (ValueError, TypeError):
            guest.invited_count = 1
        db.session.commit()
        flash(f'פרטי האורח {guest.name} עודכנו בהצלחה!', 'success')
        return redirect(url_for('admin'))
    return render_template('edit_guest.html', guest=guest)

# מחיקת כל האורחים
@app.route('/delete_all_guests')
def delete_all_guests():
    Guest.query.delete()
    db.session.commit()
    flash('כל האורחים נמחקו בהצלחה', 'success')
    return redirect(url_for('admin'))

# יצירת הטבלאות
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """עמוד הבית - סטטיסטיקות כלליות"""
    total_guests = Guest.query.count()
    confirmed_guests = Guest.query.filter_by(is_attending=True).count()
    total_attending = db.session.query(db.func.sum(Guest.confirmed_count)).filter_by(is_attending=True).scalar() or 0
    pending_responses = Guest.query.filter_by(is_attending=False, message_sent=True).count()
    
    return render_template('index.html', 
                         total_guests=total_guests,
                         confirmed_guests=confirmed_guests,
                         total_attending=total_attending,
                         pending_responses=pending_responses)

@app.route('/admin')
def admin():
    """עמוד ניהול - רשימת כל האורחים"""
    guests = Guest.query.all()
    return render_template('admin.html', guests=guests)

@app.route('/add_guest', methods=['GET', 'POST'])
def add_guest():
    """הוספת אורח חדש"""
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        invited_count = int(request.form.get('invited_count', 1))
        
        # שדות חדשים
        email = request.form.get('email', '').strip() or None
        group_affiliation = request.form.get('group_affiliation', '').strip() or None
        side = request.form.get('side', '').strip() or None
        attendance_status = request.form.get('attendance_status', 'ממתין')
        notes = request.form.get('notes', '').strip() or None
        
        # סכום מתנה
        try:
            estimated_gift_amount = float(request.form.get('estimated_gift_amount', 0) or 0)
        except (ValueError, TypeError):
            estimated_gift_amount = 0.0
        
        # יצירת טוקן ייחודי
        unique_token = str(uuid.uuid4())
        
        guest = Guest(
            name=name,
            phone=phone,
            email=email,
            unique_token=unique_token,
            invited_count=invited_count,
            group_affiliation=group_affiliation,
            side=side,
            attendance_status=attendance_status,
            estimated_gift_amount=estimated_gift_amount,
            notes=notes,
            added_by=request.form.get('added_by')  # יכול להיות מועבר מהממשק
        )
        
        # עדכון סטטוס is_attending לפי attendance_status
        if attendance_status == 'יגיע':
            guest.is_attending = True
        elif attendance_status == 'לא יגיע':
            guest.is_attending = False
        else:
            guest.is_attending = None
        
        db.session.add(guest)
        db.session.commit()
        
        flash(f'האורח {name} נוסף בהצלחה!', 'success')
        return redirect(url_for('admin'))
    
    return render_template('add_guest.html')

@app.route('/rsvp/<token>')
def rsvp_form(token):
    """טופס RSVP לאורח"""
    guest = Guest.query.filter_by(unique_token=token).first_or_404()
    
    # יצירת קוד QR עם הקישור
    website_url = os.getenv('WEBSITE_URL', 'http://localhost:5000')
    qr_url = f"{website_url}/rsvp/{token}"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return render_template('rsvp.html', guest=guest, qr_code=img_str)

@app.route('/rsvp/<token>', methods=['POST'])
def submit_rsvp(token):
    """עדכון RSVP"""
    guest = Guest.query.filter_by(unique_token=token).first_or_404()
    
    is_attending = request.form.get('is_attending') == 'yes'
    confirmed_count = int(request.form.get('confirmed_count', 0)) if is_attending else 0
    notes = request.form.get('notes', '')
    
    guest.is_attending = is_attending
    guest.confirmed_count = confirmed_count
    guest.notes = notes
    guest.response_date = get_local_time()
    
    db.session.commit()
    
    if is_attending:
        flash(f'תודה {guest.name}! אנחנו שמחים שתגיעו ({confirmed_count} אנשים)', 'success')
    else:
        flash(f'תודה {guest.name} על העדכון. נצטער שלא תוכלו להגיע', 'info')
    
    return render_template('rsvp_success.html', guest=guest)

@app.route('/seating')
def seating_chart():
    """תכנון סידור ישיבה"""
    tables = Table.query.all()
    guests_with_tables = Guest.query.filter(Guest.table_number.isnot(None)).all()
    guests_without_tables = Guest.query.filter_by(is_attending=True, table_number=None).all()
    
    return render_template('seating.html', 
                         tables=tables, 
                         guests_with_tables=guests_with_tables,
                         guests_without_tables=guests_without_tables)

@app.route('/add_table', methods=['POST'])
def add_table():
    """הוספת שולחן חדש"""
    table_number = int(request.form['table_number'])
    capacity = int(request.form.get('capacity', 8))
    description = request.form.get('description', '')
    
    table = Table(table_number=table_number, capacity=capacity, description=description)
    db.session.add(table)
    db.session.commit()
    
    flash(f'שולחן {table_number} נוסף בהצלחה!', 'success')
    return redirect(url_for('seating_chart'))

@app.route('/assign_table', methods=['POST'])
def assign_table():
    """הקצאת אורח לשולחן"""
    guest_id = int(request.form['guest_id'])
    table_number = int(request.form['table_number'])
    
    guest = Guest.query.get_or_404(guest_id)
    guest.table_number = table_number
    db.session.commit()
    
    flash(f'{guest.name} הוקצה לשולחן {table_number}', 'success')
    return redirect(url_for('seating_chart'))

@app.route('/api/guest_stats')
def guest_stats():
    """API לסטטיסטיקות (לצרכי JavaScript)"""
    stats = {
        'total_guests': Guest.query.count(),
        'confirmed': Guest.query.filter_by(is_attending=True).count(),
        'declined': Guest.query.filter_by(is_attending=False).filter(Guest.response_date.isnot(None)).count(),
        'pending': Guest.query.filter(Guest.response_date.is_(None)).count(),
        'total_attending': db.session.query(db.func.sum(Guest.confirmed_count)).filter_by(is_attending=True).scalar() or 0
    }
    return jsonify(stats)

def check_chrome_availability():
    """בדיקה אם Chrome זמין במערכת"""
    import shutil
    
    # בדיקת Chrome binary
    chrome_paths = [
        "/usr/bin/google-chrome-stable",  # Most common after apt install
        "/usr/bin/google-chrome",
        "/opt/google/chrome/chrome",
        "/app/.chrome-for-testing/chrome-linux64/chrome",
        "google-chrome-stable",
        "google-chrome",
        "chrome"
    ]
    
    for path in chrome_paths:
        if shutil.which(path) or os.path.exists(path):
            print(f"🔍 Found Chrome at: {path}")  # Debug info
            return True
    
    print("🔍 Chrome not found in any expected location")  # Debug info
    return False

@app.route('/api/send_invitations', methods=['POST'])
def api_send_invitations():
    """API להפעלת בוט שליחת הזמנות"""
    try:
        # בדיקה אם Chrome זמין
        if not check_chrome_availability():
            return jsonify({
                'success': False,
                'message': '📱 שירות WhatsApp זמין רק בסביבת פיתוח מקומית. באפליקציה המוצגת באינטרנט, תוכל לצפות ברשימת האורחים, להוסיף אורחים, לקבל תגובות ולראות מי הגיע. שליחת הודעות WhatsApp מתבצעת בסביבה מקומית בלבד.'
            })
        
        import subprocess
        import sys
        
        # הפעלת הבוט ברקע
        python_exe = sys.executable
        script_path = os.path.join(os.getcwd(), 'whatsapp_bot.py')
        
        # הפעלה בתהליך נפרד
        subprocess.Popen([python_exe, script_path, 'send_all'])
        
        return jsonify({
            'success': True,
            'message': 'تהליך השליחה התחיל בהצלחה'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'שגיאה בהפעלת הבוט: {str(e)}'
        })

@app.route('/api/send_reminders', methods=['POST'])
def api_send_reminders():
    """API להפעלת בוט שליחת תזכורות"""
    try:
        # בדיקה אם Chrome זמין
        if not check_chrome_availability():
            return jsonify({
                'success': False,
                'message': '📱 שירות WhatsApp זמין רק בסביבת פיתוח מקומית. באפליקציה המוצגת באינטרנט, תוכל לצפות ברשימת האורחים, להוסיף אורחים, לקבל תגובות ולראות מי הגיע. שליחת הודעות WhatsApp מתבצעת בסביבה מקומית בלבד.'
            })
        
        import subprocess
        import sys
        
        python_exe = sys.executable
        script_path = os.path.join(os.getcwd(), 'whatsapp_bot.py')
        
        subprocess.Popen([python_exe, script_path, 'send_reminders'])
        
        return jsonify({
            'success': True,
            'message': 'תהליך שליחת התזכורות התחיל בהצלחה'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'שגיאה בהפעלת הבוט: {str(e)}'
        })

@app.route('/api/generate_links', methods=['POST'])
def api_generate_links():
    """API ליצירת קישורים לכל האורחים"""
    try:
        guests = Guest.query.all()
        website_url = os.getenv('WEBSITE_URL', 'http://localhost:5000')
        
        links = []
        for guest in guests:
            clean_phone = guest.phone.replace('+', '').replace('-', '').replace(' ', '')
            links.append({
                'name': guest.name,
                'phone': guest.phone,
                'clean_phone': clean_phone,
                'invited_count': guest.invited_count,
                'link': f"{website_url}/rsvp/{guest.unique_token}"
            })
        
        return jsonify({
            'success': True,
            'links': links
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'שגיאה ביצירת הקישורים: {str(e)}'
        })

@app.route('/export_guests')
def export_guests():
    """ייצוא כל האורחים לקובץ Excel"""
    try:
        guests = Guest.query.all()
        
        # יצירת רשימת נתונים
        data = []
        for guest in guests:
            # מיפוי סטטוס נוכחות
            if guest.attendance_status:
                status = guest.attendance_status
            elif guest.is_attending is True:
                status = 'יגיע'
            elif guest.is_attending is False:
                status = 'לא יגיע'
            else:
                status = 'ממתין'
                
            # מיפוי סטטוס שליחת הזמנה
            invitation_status = 'נשלחה' if guest.message_sent else 'לא נשלחה'
            
            data.append({
                'שם המוזמן': guest.name,
                'נייד': guest.phone,
                'כמה יגיעו': guest.invited_count,
                'שיוך לקבוצה': guest.group_affiliation or '',
                'מהצד של...': guest.side or '',
                'סטטוס הגעה (יגיע, מתלבט, לא יגיע)': status,
                'סכום מתנה משוער': guest.estimated_gift_amount or 0,
                'האם נשלחה הזמנה? (נשלחה, לא נשלחה)': invitation_status,
                'mail': guest.email or '',
                'הערות (מלל חופשי)': guest.notes or '',
                'מספר הטלפון של המשתמש שהכניס את המוזמן באפליקציה': guest.added_by or ''
            })
        
        # יצירת DataFrame
        df = pd.DataFrame(data)
        
        # יצירת קובץ זמני
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False, engine='openpyxl')
            tmp_path = tmp.name
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=f'wedding_guests_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'שגיאה בייצוא: {str(e)}', 'error')
        return redirect(url_for('admin'))

@app.route('/import_guests', methods=['POST'])
def import_guests():
    """ייבוא אורחים מקובץ Excel/CSV"""
    try:
        if 'file' not in request.files:
            flash('לא נבחר קובץ', 'error')
            return redirect(url_for('admin'))
        
        file = request.files['file']
        if file.filename == '':
            flash('לא נבחר קובץ', 'error')
            return redirect(url_for('admin'))
        
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            flash('סוג קובץ לא נתמך. אנא העלה קובץ Excel או CSV', 'error')
            return redirect(url_for('admin'))
        
        # קריאת הקובץ
        try:
            # ננסה לזהות אם השורה הראשונה אינה שמות עמודות (כמו "קובץ רשימות מוזמנים...")
            if file.filename.lower().endswith('.csv'):
                df_preview = pd.read_csv(file, encoding='utf-8-sig', nrows=2, header=None)
                file.seek(0)
                if 'שם המוזמן' not in df_preview.iloc[0].astype(str).tolist() and 'שם המוזמן' in df_preview.iloc[1].astype(str).tolist():
                    df = pd.read_csv(file, encoding='utf-8-sig', header=1)
                else:
                    df = pd.read_csv(file, encoding='utf-8-sig')
            else:
                df_preview = pd.read_excel(file, engine='openpyxl', nrows=2, header=None)
                file.seek(0)
                if 'שם המוזמן' not in df_preview.iloc[0].astype(str).tolist() and 'שם המוזמן' in df_preview.iloc[1].astype(str).tolist():
                    df = pd.read_excel(file, engine='openpyxl', header=1)
                else:
                    df = pd.read_excel(file, engine='openpyxl')
        except Exception as e:
            flash(f'שגיאה בקריאת הקובץ: {str(e)}', 'error')
            return redirect(url_for('admin'))
        
        print(f"עמודות בקובץ: {list(df.columns)}")  # לדיבוג
        print(f"מספר שורות: {len(df)}")  # לדיבוג
        
        # ניקוי שמות עמודות - הסרת רווחים מיותרים ותווים מיוחדים
        df.columns = [str(col).strip().replace('\n', ' ').replace('\r', '') for col in df.columns]
        
        # מיפוי עמודות גמיש יותר
        column_mapping = {}
        for col in df.columns:
            col_clean = str(col).strip()
            col_lower = col_clean.lower()
            
            # חיפוש מדויק יותר
            if col_clean == 'שם המוזמן' or 'שם' in col_lower:
                column_mapping[col] = 'name'
            elif col_clean == 'נייד' or 'נייד' in col_lower or 'טלפון' in col_lower:
                column_mapping[col] = 'phone'
            elif col_clean == 'כמה יגיעו' or ('כמה' in col_lower and 'יגיעו' in col_lower):
                column_mapping[col] = 'invited_count'
            elif col_clean == 'שיוך לקבוצה' or 'קבוצה' in col_lower:
                column_mapping[col] = 'group_affiliation'
            elif col_clean == 'מהצד של...' or ('צד' in col_lower and 'של' in col_lower):
                column_mapping[col] = 'side'
            elif 'סטטוס הגעה' in col_clean or ('סטטוס' in col_lower and 'הגעה' in col_lower):
                column_mapping[col] = 'attendance_status'
            elif col_clean == 'סכום מתנה משוער' or ('מתנה' in col_lower and ('משוער' in col_lower or 'סכום' in col_lower)):
                column_mapping[col] = 'estimated_gift_amount'
            elif 'האם נשלחה הזמנה' in col_clean or ('הזמנה' in col_lower and 'נשלחה' in col_lower):
                column_mapping[col] = 'message_sent_text'
            elif col_clean == 'mail' or 'mail' in col_lower or 'מייל' in col_lower:
                column_mapping[col] = 'email'
            elif col_clean == 'הערות (מלל חופשי)' or 'הערות' in col_lower:
                column_mapping[col] = 'notes'
            elif 'מספר הטלפון של המשתמש' in col_clean or ('מספר' in col_lower and 'הכניס' in col_lower):
                column_mapping[col] = 'added_by'
        
        print(f"מיפוי עמודות: {column_mapping}")  # לדיבוג
        
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # פונקציה לקבלת ערך מהשורה
                def get_value(mapping_key):
                    for col, mapped in column_mapping.items():
                        if mapped == mapping_key:
                            value = row.get(col)
                            if pd.notna(value) and str(value).strip() not in ['', 'nan', 'NaN', 'null', 'None']:
                                return str(value).strip()
                    return None
                
                # קבלת נתונים בסיסיים
                name = get_value('name')
                phone = get_value('phone')
                # תיקון: הוספת 0 אם חסר במספר סלולרי ישראלי
                if phone and phone.isdigit() and len(phone) == 10 and not phone.startswith('0') and phone.startswith('5'):
                    phone = '0' + phone
                
                if not name:
                    errors.append(f'שורה {index + 2}: חסר שם אורח')
                    error_count += 1
                    continue
                
                if not phone:
                    errors.append(f'שורה {index + 2}: חסר מספר טלפון עבור {name}')
                    error_count += 1
                    continue
                
                # בדיקה אם האורח כבר קיים
                existing_guest = Guest.query.filter_by(phone=phone).first()
                if existing_guest:
                    errors.append(f'שורה {index + 2}: האורח {name} ({phone}) כבר קיים במערכת')
                    error_count += 1
                    continue
                
                # יצירת אורח חדש
                guest = Guest(
                    name=name,
                    phone=phone,
                    unique_token=str(uuid.uuid4())
                )
                
                # מילוי שדות נוספים
                guest.email = get_value('email')
                guest.group_affiliation = get_value('group_affiliation')
                guest.side = get_value('side')
                guest.notes = get_value('notes')
                guest.added_by = get_value('added_by')
                guest.attendance_status = get_value('attendance_status') or 'ממתין'
                
                # טיפול במספר מוזמנים
                invited_count_str = get_value('invited_count')
                try:
                    guest.invited_count = int(float(invited_count_str)) if invited_count_str else 1
                except (ValueError, TypeError):
                    guest.invited_count = 1
                
                # טיפול בסכום מתנה
                gift_amount_str = get_value('estimated_gift_amount')
                try:
                    guest.estimated_gift_amount = float(gift_amount_str) if gift_amount_str else 0.0
                except (ValueError, TypeError):
                    guest.estimated_gift_amount = 0.0
                
                # טיפול בסטטוס שליחת הזמנה
                message_sent_str = get_value('message_sent_text')
                if message_sent_str:
                    guest.message_sent = message_sent_str.lower() in ['נשלחה', 'true', '1', 'yes', 'כן']
                else:
                    guest.message_sent = False
                
                # עדכון is_attending לפי attendance_status
                if guest.attendance_status == 'יגיע':
                    guest.is_attending = True
                elif guest.attendance_status == 'לא יגיע':
                    guest.is_attending = False
                else:
                    guest.is_attending = None
                
                db.session.add(guest)
                success_count += 1
                
            except Exception as e:
                errors.append(f'שורה {index + 2}: {str(e)}')
                error_count += 1
        
        # שמירה במסד הנתונים
        db.session.commit()
        
        # הודעת סיכום
        message = f'יובאו בהצלחה {success_count} אורחים'
        if error_count > 0:
            message += f', {error_count} שגיאות'
            if len(errors) <= 5:  # מציג עד 5 שגיאות ראשונות
                message += f': {"; ".join(errors[:5])}'
            elif len(errors) > 5:
                message += f'. דוגמאות: {"; ".join(errors[:3])}...'
        
        flash(message, 'success' if error_count == 0 else 'warning')
        
        # הדפסה למסוף לדיבוג
        print(f"סיכום ייבוא: {success_count} הצליחו, {error_count} נכשלו")
        if errors:
            print("שגיאות:")
            for error in errors[:10]:  # מדפיס 10 ראשונות
                print(f"  {error}")
        
    except Exception as e:
        flash(f'שגיאה בייבוא הקובץ: {str(e)}', 'error')
    
    return redirect(url_for('admin'))

@app.route('/download_template')
def download_template():
    """הורדת תבנית Excel לייבוא אורחים"""
    try:
        # יצירת תבנית עם דוגמאות
        template_data = [
            {
                'שם המוזמן': 'יוסי כהן',
                'נייד': '0501234567',
                'כמה יגיעו': 2,
                'שיוך לקבוצה': 'חברי עבודה',
                'מהצד של...': 'חתן',
                'סטטוס הגעה (יגיע, מתלבט, לא יגיע)': 'ממתין',
                'סכום מתנה משוער': 500,
                'האם נשלחה הזמנה? (נשלחה, לא נשלחה)': 'לא נשלחה',
                'mail': 'yossi@example.com',
                'הערות (מלל חופשי)': 'צריך מקום מיוחד',
                'מספר הטלפון של המשתמש שהכניס את המוזמן באפליקציה': '0507654321'
            },
            {
                'שם המוزמן': 'שרה לוי',
                'נייד': '0507654321',
                'כמה יגיעו': 1,
                'שיוך לקבוצה': 'משפחה',
                'מהצד של...': 'כלה',
                'סטטוס הגעה (יגיע, מתלבט, לא יגיע)': 'יגיע',
                'סכום מתנה משוער': 300,
                'האם נשלחה הזמנה? (נשלחה, לא נשלחה)': 'נשלחה',
                'mail': 'sarah@example.com',
                'הערות (מלל חופשי)': 'צמחונית',
                'מספר הטלפון של המשתמש שהכניס את המוזמן באפליקציה': '0501234567'
            }
        ]
        
        df = pd.DataFrame(template_data)
        
        # יצירת קובץ זמני
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False, engine='openpyxl')
            tmp_path = tmp.name
        
        return send_file(
            tmp_path,
            as_attachment=True,
            download_name='wedding_guests_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'שגיאה ביצירת התבנית: {str(e)}', 'error')
        return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)