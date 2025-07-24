#!/bin/bash

# Fix MySQL Schema - Add missing columns to omada_config table
# This script fixes the "Unknown column 'refresh_token'" error

echo "Fixing MySQL schema for omada_config table..."

# Check if MySQL is accessible
if ! command -v mysql &> /dev/null; then
    echo "Error: MySQL client not found. Please install mysql-client."
    exit 1
fi

# Prompt for MySQL credentials
echo "Enter MySQL credentials:"
read -p "MySQL username (default: voucher_user): " MYSQL_USER
MYSQL_USER=${MYSQL_USER:-voucher_user}

read -s -p "MySQL password: " MYSQL_PASS
echo

read -p "Database name (default: voucher_system): " MYSQL_DB
MYSQL_DB=${MYSQL_DB:-voucher_system}

read -p "MySQL host (default: localhost): " MYSQL_HOST
MYSQL_HOST=${MYSQL_HOST:-localhost}

# Test connection
echo "Testing MySQL connection..."
if ! mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "USE $MYSQL_DB;" 2>/dev/null; then
    echo "Error: Could not connect to MySQL database. Check your credentials."
    exit 1
fi

echo "Connection successful. Updating schema..."

# Execute the fix
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_DB" << 'EOF'
-- Add refresh_token column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'omada_config' 
     AND column_name = 'refresh_token' 
     AND table_schema = DATABASE()) > 0,
    "SELECT 'refresh_token column already exists' as message",
    "ALTER TABLE omada_config ADD COLUMN refresh_token TEXT AFTER access_token"
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add is_active column if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'omada_config' 
     AND column_name = 'is_active' 
     AND table_schema = DATABASE()) > 0,
    "SELECT 'is_active column already exists' as message",
    "ALTER TABLE omada_config ADD COLUMN is_active BOOLEAN DEFAULT TRUE AFTER token_expires_at"
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing records
UPDATE omada_config SET is_active = TRUE WHERE is_active IS NULL;

-- Add assigned_at column to admin_site table if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'admin_site' 
     AND column_name = 'assigned_at' 
     AND table_schema = DATABASE()) > 0,
    "SELECT 'assigned_at column already exists in admin_site' as message",
    "ALTER TABLE admin_site ADD COLUMN assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add assigned_at column to vendor_site table if it doesn't exist
SET @sql = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS 
     WHERE table_name = 'vendor_site' 
     AND column_name = 'assigned_at' 
     AND table_schema = DATABASE()) > 0,
    "SELECT 'assigned_at column already exists in vendor_site' as message",
    "ALTER TABLE vendor_site ADD COLUMN assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
));
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Update existing records to have assigned_at = CURRENT_TIMESTAMP if NULL
UPDATE admin_site SET assigned_at = CURRENT_TIMESTAMP WHERE assigned_at IS NULL;
UPDATE vendor_site SET assigned_at = CURRENT_TIMESTAMP WHERE assigned_at IS NULL;

-- Show current structures
SELECT 'MySQL schema updated successfully!' as status;
DESCRIBE omada_config;
DESCRIBE admin_site;
DESCRIBE vendor_site;
EOF

if [ $? -eq 0 ]; then
    echo "Schema update completed successfully!"
    echo "The application should now work properly with MySQL."
    echo ""
    echo "If you're still getting errors, try restarting your application:"
    echo "- supervisorctl restart voucher-app"
    echo "- or restart your Flask application manually"
else
    echo "Error occurred during schema update. Check the output above."
    exit 1
fi