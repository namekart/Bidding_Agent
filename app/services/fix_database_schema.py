"""
Fix database schema - Rename column from hours_remaining to hours_remaining_at_decision
Run this once to fix the existing database table.
"""
import mysql.connector
from mysql.connector import Error

mysql_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'S@chname.com',  # ← Your password
    'database': 'bidding_auction_db'
}

def fix_database_schema():
    """Fix the column name in existing table"""
    try:
        print("Connecting to MySQL...")
        conn = mysql.connector.connect(**mysql_config)
        cursor = conn.cursor()
        
        # Check if old column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
              AND TABLE_NAME = 'auction_outcomes' 
              AND COLUMN_NAME = 'hours_remaining'
        """, (mysql_config['database'],))
        
        old_column_exists = cursor.fetchone()
        
        if old_column_exists:
            print("Found old column 'hours_remaining' - renaming to 'hours_remaining_at_decision'...")
            cursor.execute("""
                ALTER TABLE auction_outcomes 
                CHANGE COLUMN hours_remaining hours_remaining_at_decision DECIMAL(5,2)
            """)
            conn.commit()
            print("✅ Column renamed successfully!")
        else:
            # Check if new column already exists
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                  AND TABLE_NAME = 'auction_outcomes' 
                  AND COLUMN_NAME = 'hours_remaining_at_decision'
            """, (mysql_config['database'],))
            
            new_column_exists = cursor.fetchone()
            
            if new_column_exists:
                print("✅ Column 'hours_remaining_at_decision' already exists - no fix needed!")
            else:
                print("⚠️  Neither column found - table might not exist yet")
        
        # Verify the table structure
        print("\nCurrent table structure:")
        cursor.execute("DESCRIBE auction_outcomes")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]})")
        
        cursor.close()
        conn.close()
        print("\n✅ Database schema fix completed!")
        return True
        
    except Error as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("DATABASE SCHEMA FIX")
    print("="*60)
    fix_database_schema()



