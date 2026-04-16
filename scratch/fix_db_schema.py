from sqlalchemy import create_engine, text
import os

# Use the RDS URL found earlier
DATABASE_URL = "postgresql://planapp:PlanLector2024!@plan-lector-postgres.c32m6a8uybyx.us-east-1.rds.amazonaws.com:5432/planLectorDB"

def fix_schema():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Adding user_email column to busquedas table...")
        try:
            conn.execute(text("ALTER TABLE busquedas ADD COLUMN IF NOT EXISTS user_email VARCHAR(128);"))
            conn.commit()
            print("Successfully added column.")
        except Exception as e:
            print(f"Error adding column: {e}")

        print("Checking if users table exists...")
        try:
            res = conn.execute(text("SELECT to_regclass('public.users');"))
            if res.scalar():
                print("Users table exists.")
            else:
                print("Users table does NOT exist. SQLAlchemy create_all should handle it, but let's be sure.")
        except Exception as e:
            print(f"Error checking users table: {e}")

if __name__ == "__main__":
    fix_schema()
