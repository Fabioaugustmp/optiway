"""
Migration script to add alternatives_json, cost_breakdown_json, and hotels_json columns to itineraries table
"""
from sqlalchemy import text
from app.db.database import engine

def migrate():
    with engine.connect() as conn:
        try:
            # Check if columns already exist
            result = conn.execute(text("PRAGMA table_info(itineraries)"))
            columns = [row[1] for row in result]
            
            if 'alternatives_json' not in columns:
                print("Adding alternatives_json column...")
                conn.execute(text("ALTER TABLE itineraries ADD COLUMN alternatives_json TEXT"))
                conn.commit()
                print("✓ alternatives_json column added")
            else:
                print("✓ alternatives_json column already exists")
            
            if 'cost_breakdown_json' not in columns:
                print("Adding cost_breakdown_json column...")
                conn.execute(text("ALTER TABLE itineraries ADD COLUMN cost_breakdown_json TEXT"))
                conn.commit()
                print("✓ cost_breakdown_json column added")
            else:
                print("✓ cost_breakdown_json column already exists")
            
            if 'hotels_json' not in columns:
                print("Adding hotels_json column...")
                conn.execute(text("ALTER TABLE itineraries ADD COLUMN hotels_json TEXT"))
                conn.commit()
                print("✓ hotels_json column added")
            else:
                print("✓ hotels_json column already exists")
            
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    migrate()
