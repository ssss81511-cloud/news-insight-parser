"""
Add AI analysis columns to existing database
"""
import sqlite3

def add_ai_columns():
    """Add AI columns to universal_posts table"""

    conn = sqlite3.connect('data/insights.db')
    cursor = conn.cursor()

    # List of columns to add
    columns = [
        ('ai_summary', 'TEXT'),
        ('ai_category', 'VARCHAR(50)'),
        ('ai_sentiment', 'VARCHAR(20)'),
        ('ai_insights', 'TEXT'),
        ('ai_technologies', 'TEXT'),
        ('ai_companies', 'TEXT'),
        ('ai_topics', 'TEXT'),
        ('ai_analyzed_at', 'DATETIME')
    ]

    for column_name, column_type in columns:
        try:
            cursor.execute(f'ALTER TABLE universal_posts ADD COLUMN {column_name} {column_type}')
            print(f"[OK] Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e):
                print(f"[SKIP] Column already exists: {column_name}")
            else:
                print(f"[ERROR] Error adding {column_name}: {e}")

    conn.commit()
    conn.close()
    print("\n[DONE] Database migration complete!")

if __name__ == '__main__':
    add_ai_columns()
