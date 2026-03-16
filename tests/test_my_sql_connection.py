""" Test MySQL connection script"""
import mysql.connector
from mysql.connector import Error

def test_connection():
    """ Test MySQL connection"""
    try:
        mysql_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'root',
            'password':'S@chname.com',
            'database': 'bidding_auction_db'

        }

        print("Attempting to connect to MySQL...")
        print(f"Host: {mysql_config['host']}")
        print(f"Database: {mysql_config['database']}")
        print(f"User: {mysql_config['user']}")

        conn = mysql.connector.connect(**mysql_config)

        if conn.is_connected():
            print("\n SUCCESS: Connected to MySQL!")

            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version= cursor.fetchone()
            print(f"MySQL Version: {version[0]}")

            # list databases
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print(f"\n Available databases: {[db[0] for db in databases]}")

            if('bidding_auction_db',) in databases:
                print(" Database 'bidding_auction_db' found.")
            else:
                print(" Database 'bidding_auction_db' NOT found")

            cursor.close()
            conn.close()
            print("\n Connection closed successfully")
            return True

    except Error as e:
        print(f"\n Error: {e}")
        print("\n Trobleshooting:")
        print("1. Check MySQL server is running")
        print("2. Verify username and password")
        print("3. Check if database exists")
        print("4. Verify user has privileges")
        return false

if __name__ == "__main__":
    print("="*60)
    print("MySQL Connection Test")
    print("="*60)
    test_connection()
    