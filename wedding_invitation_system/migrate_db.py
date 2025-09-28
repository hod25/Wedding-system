#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
מיגרציה למסד הנתונים - הוספת שדות חדשים
"""

from app import app, db, Guest
import sys

def migrate_database():
    """הוסף שדות חדשים למסד הנתונים"""
    with app.app_context():
        try:
            print("🔄 מתחיל מיגרציה למסד הנתונים...")
            
            # בדיקה אם השדות החדשים כבר קיימים
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('guest')]
            
            new_columns = [
                'email', 'group_affiliation', 'side', 'attendance_status', 
                'estimated_gift_amount', 'added_by'
            ]
            
            missing_columns = [col for col in new_columns if col not in columns]
            
            if not missing_columns:
                print("✅ כל השדות כבר קיימים במסד הנתונים")
                return
            
            print(f"📝 מוסיף שדות חסרים: {', '.join(missing_columns)}")
            
            # הוספת שדות חדשים
            with db.engine.connect() as conn:
                if 'email' in missing_columns:
                    conn.execute(db.text("ALTER TABLE guest ADD COLUMN email VARCHAR(100)"))
                    print("✅ הוסף שדה email")
                
                if 'group_affiliation' in missing_columns:
                    conn.execute(db.text("ALTER TABLE guest ADD COLUMN group_affiliation VARCHAR(100)"))
                    print("✅ הוסף שדה group_affiliation")
                
                if 'side' in missing_columns:
                    conn.execute(db.text("ALTER TABLE guest ADD COLUMN side VARCHAR(50)"))
                    print("✅ הוסף שדה side")
                
                if 'attendance_status' in missing_columns:
                    conn.execute(db.text("ALTER TABLE guest ADD COLUMN attendance_status VARCHAR(20) DEFAULT 'ממתין'"))
                    print("✅ הוסף שדה attendance_status")
                
                if 'estimated_gift_amount' in missing_columns:
                    conn.execute(db.text("ALTER TABLE guest ADD COLUMN estimated_gift_amount FLOAT DEFAULT 0.0"))
                    print("✅ הוסף שדה estimated_gift_amount")
                
                if 'added_by' in missing_columns:
                    conn.execute(db.text("ALTER TABLE guest ADD COLUMN added_by VARCHAR(20)"))
                    print("✅ הוסף שדה added_by")
                
                conn.commit()
            
            print("✅ מיגרציה הושלמה בהצלחה!")
            
        except Exception as e:
            print(f"❌ שגיאה במיגרציה: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()