#!/usr/bin/env python3
"""
Migration: Add expected_responses column to conversation_state table
Run on VPS to update existing database
"""
import sqlite3
import sys

def migrate():
    db_path = '/app/data/anu_login.sqlite3'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(conversation_state)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'expected_responses' not in columns:
            print("❌ Column 'expected_responses' missing from conversation_state")
            print("✅ Adding column...")
            cursor.execute("""
                ALTER TABLE conversation_state 
                ADD COLUMN expected_responses TEXT
            """)
            conn.commit()
            print("✅ Column added successfully")
        else:
            print("✅ Column 'expected_responses' already exists")
        
        # Verify
        cursor.execute("PRAGMA table_info(conversation_state)")
        columns = {row[1] for row in cursor.fetchall()}
        if 'expected_responses' in columns:
            print("✅ Migration verified - column present")
            return True
        else:
            print("❌ Migration failed - column still missing")
            return False
            
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
