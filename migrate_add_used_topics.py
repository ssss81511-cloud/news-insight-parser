"""
Database migration: Add used_topics table

This script adds the UsedTopic table to track which topics have been
used for content generation.
"""
import os
from storage.universal_models import Base, UsedTopic
from sqlalchemy import create_engine, inspect

# Get database URL
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/techcrunch.db')

# Fix postgres URL if needed
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print(f"Connecting to database: {DATABASE_URL}")

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Check if table already exists
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

print(f"\nExisting tables: {len(existing_tables)}")
for table in existing_tables:
    print(f"  - {table}")

# Create used_topics table if it doesn't exist
if 'used_topics' in existing_tables:
    print("\n[INFO] used_topics table already exists - skipping creation")
else:
    print("\n[INFO] Creating used_topics table...")
    try:
        # Create only the UsedTopic table
        UsedTopic.__table__.create(engine)
        print("[OK] used_topics table created successfully!")
    except Exception as e:
        print(f"[ERROR] Failed to create table: {e}")
        exit(1)

# Verify table was created
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

if 'used_topics' in existing_tables:
    print("\n[OK] Migration completed successfully!")
    print("\nTable structure:")
    columns = inspector.get_columns('used_topics')
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")

    indexes = inspector.get_indexes('used_topics')
    if indexes:
        print("\nIndexes:")
        for idx in indexes:
            print(f"  - {idx['name']}: {idx['column_names']}")
else:
    print("\n[ERROR] Table was not created!")
    exit(1)

print("\n" + "="*60)
print("Migration complete!")
print("="*60)
print("\nYou can now use TopicSelector to prevent topic repetition:")
print("""
from automation.topic_selector import TopicSelector
from storage.universal_database import UniversalDatabaseManager

db = UniversalDatabaseManager(DATABASE_URL)
selector = TopicSelector(db)

topic = selector.select_next_topic(exclude_days=30)
""")
