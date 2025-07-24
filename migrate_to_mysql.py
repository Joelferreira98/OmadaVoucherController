#!/usr/bin/env python3
"""
Migration script to convert Voucher Management System from PostgreSQL to MySQL
This script exports data from PostgreSQL and imports it into MySQL

Usage:
    python migrate_to_mysql.py

Requirements:
    - Both PostgreSQL and MySQL databases accessible
    - PyMySQL and psycopg2 packages installed
    - Source .env file with PostgreSQL configuration
    - Target .env.mysql file with MySQL configuration
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
import mysql.connector
import psycopg2
from psycopg2.extras import RealDictCursor

class DatabaseMigrator:
    def __init__(self):
        self.pg_conn = None
        self.mysql_conn = None
        self.migration_log = []
        
    def log(self, message, level="INFO"):
        """Log migration progress"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.migration_log.append(log_entry)
        
    def connect_postgresql(self):
        """Connect to PostgreSQL database"""
        try:
            # Load PostgreSQL configuration
            load_dotenv('.env')
            pg_url = os.getenv('DATABASE_URL')
            
            if not pg_url:
                raise ValueError("DATABASE_URL not found in .env file")
                
            self.log("Connecting to PostgreSQL database...")
            self.pg_conn = psycopg2.connect(pg_url)
            self.log("PostgreSQL connection established")
            return True
            
        except Exception as e:
            self.log(f"Failed to connect to PostgreSQL: {e}", "ERROR")
            return False
            
    def connect_mysql(self):
        """Connect to MySQL database"""
        try:
            # Load MySQL configuration
            load_dotenv('.env.mysql')
            mysql_url = os.getenv('DATABASE_URL')
            
            if not mysql_url:
                raise ValueError("DATABASE_URL not found in .env.mysql file")
            
            # Parse MySQL URL: mysql+pymysql://user:pass@host:port/db
            if mysql_url.startswith('mysql+pymysql://'):
                url_parts = mysql_url.replace('mysql+pymysql://', '').split('/')
                db_name = url_parts[1].split('?')[0]  # Remove any parameters
                auth_host = url_parts[0].split('@')
                user_pass = auth_host[0].split(':')
                host_port = auth_host[1].split(':')
                
                config = {
                    'user': user_pass[0],
                    'password': user_pass[1],
                    'host': host_port[0],
                    'port': int(host_port[1]) if len(host_port) > 1 else 3306,
                    'database': db_name,
                    'charset': 'utf8mb4',
                    'collation': 'utf8mb4_unicode_ci'
                }
            else:
                raise ValueError("Invalid MySQL URL format")
            
            self.log("Connecting to MySQL database...")
            self.mysql_conn = mysql.connector.connect(**config)
            self.log("MySQL connection established")
            return True
            
        except Exception as e:
            self.log(f"Failed to connect to MySQL: {e}", "ERROR")
            return False
            
    def export_table_data(self, table_name):
        """Export data from PostgreSQL table"""
        try:
            cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            cursor.close()
            
            # Convert to list of dictionaries
            data = [dict(row) for row in rows]
            self.log(f"Exported {len(data)} rows from {table_name}")
            return data
            
        except Exception as e:
            self.log(f"Failed to export {table_name}: {e}", "ERROR")
            return []
    
    def fix_mysql_schema(self):
        """Fix MySQL schema to ensure all required columns exist"""
        try:
            cursor = self.mysql_conn.cursor()
            
            # Check and add refresh_token column
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE table_name = 'omada_config' 
                AND column_name = 'refresh_token' 
                AND table_schema = DATABASE()
            """)
            
            if cursor.fetchone()[0] == 0:
                cursor.execute("ALTER TABLE omada_config ADD COLUMN refresh_token TEXT AFTER access_token")
                self.log("Added refresh_token column to omada_config")
            
            # Check and add is_active column
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE table_name = 'omada_config' 
                AND column_name = 'is_active' 
                AND table_schema = DATABASE()
            """)
            
            if cursor.fetchone()[0] == 0:
                cursor.execute("ALTER TABLE omada_config ADD COLUMN is_active BOOLEAN DEFAULT TRUE AFTER token_expires_at")
                self.log("Added is_active column to omada_config")
            
            # Update existing records
            cursor.execute("UPDATE omada_config SET is_active = TRUE WHERE is_active IS NULL")
            
            self.mysql_conn.commit()
            cursor.close()
            self.log("MySQL schema fix completed")
            
        except Exception as e:
            self.log(f"Warning: Could not fix MySQL schema: {e}", "WARNING")
            
    def import_table_data(self, table_name, data):
        """Import data into MySQL table"""
        if not data:
            self.log(f"No data to import for {table_name}")
            return True
            
        try:
            cursor = self.mysql_conn.cursor()
            
            # Get column names
            columns = list(data[0].keys())
            placeholders = ', '.join(['%s'] * len(columns))
            column_names = ', '.join(columns)
            
            # Prepare INSERT statement
            query = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
            
            # Convert data to tuples
            values = []
            for row in data:
                row_values = []
                for col in columns:
                    value = row[col]
                    # Handle datetime objects
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    # Handle None values
                    elif value is None:
                        value = None
                    # Handle JSON fields
                    elif isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    row_values.append(value)
                values.append(tuple(row_values))
            
            # Execute batch insert
            cursor.executemany(query, values)
            self.mysql_conn.commit()
            cursor.close()
            
            self.log(f"Imported {len(data)} rows into {table_name}")
            return True
            
        except Exception as e:
            self.log(f"Failed to import {table_name}: {e}", "ERROR")
            return False
            
    def migrate_table(self, table_name):
        """Migrate a single table"""
        self.log(f"Migrating table: {table_name}")
        
        # Export from PostgreSQL
        data = self.export_table_data(table_name)
        if not data:
            return True  # Empty table is OK
            
        # Import to MySQL
        return self.import_table_data(table_name, data)
        
    def run_migration(self):
        """Run the complete migration process"""
        self.log("Starting database migration from PostgreSQL to MySQL")
        
        # Connect to databases
        if not self.connect_postgresql():
            return False
            
        if not self.connect_mysql():
            return False
        
        # Define migration order (respecting foreign key constraints)
        tables_to_migrate = [
            'users',
            'sites', 
            'voucher_plans',
            'voucher_groups',
            'admin_site',
            'vendor_site',
            'cash_register',
            'omada_config'
        ]
        
        # Disable foreign key checks in MySQL
        try:
            mysql_cursor = self.mysql_conn.cursor()
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            self.mysql_conn.commit()
            mysql_cursor.close()
            self.log("Disabled MySQL foreign key checks")
        except Exception as e:
            self.log(f"Warning: Could not disable foreign key checks: {e}", "WARNING")
        
        # Ensure MySQL schema has required columns
        self.fix_mysql_schema()
        
        # Migrate each table
        success = True
        for table in tables_to_migrate:
            if not self.migrate_table(table):
                success = False
                self.log(f"Migration failed for table: {table}", "ERROR")
                break
                
        # Re-enable foreign key checks
        try:
            mysql_cursor = self.mysql_conn.cursor()
            mysql_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            self.mysql_conn.commit()
            mysql_cursor.close()
            self.log("Re-enabled MySQL foreign key checks")
        except Exception as e:
            self.log(f"Warning: Could not re-enable foreign key checks: {e}", "WARNING")
        
        # Close connections
        if self.pg_conn:
            self.pg_conn.close()
            self.log("PostgreSQL connection closed")
            
        if self.mysql_conn:
            self.mysql_conn.close()
            self.log("MySQL connection closed")
        
        if success:
            self.log("Migration completed successfully!", "SUCCESS")
        else:
            self.log("Migration failed!", "ERROR")
            
        return success
        
    def save_migration_log(self):
        """Save migration log to file"""
        log_filename = f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(log_filename, 'w') as f:
            f.write('\n'.join(self.migration_log))
        print(f"Migration log saved to: {log_filename}")

def main():
    """Main migration function"""
    print("Voucher Management System - PostgreSQL to MySQL Migration")
    print("=" * 60)
    
    # Check if required files exist
    if not os.path.exists('.env'):
        print("ERROR: .env file not found (PostgreSQL configuration)")
        sys.exit(1)
        
    if not os.path.exists('.env.mysql'):
        print("ERROR: .env.mysql file not found (MySQL configuration)")
        sys.exit(1)
    
    # Confirm migration
    response = input("This will migrate data from PostgreSQL to MySQL. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    migrator = DatabaseMigrator()
    success = migrator.run_migration()
    migrator.save_migration_log()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("Next steps:")
        print("1. Rename .env to .env.postgresql (backup)")
        print("2. Rename .env.mysql to .env (activate MySQL)")
        print("3. Test the application with MySQL")
        print("4. Update any deployment scripts to use MySQL")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Migration failed! Check the log file for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()