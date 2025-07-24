#!/bin/bash

# Quick MySQL Schema Fix - One-line command
# This script quickly fixes missing columns in MySQL

echo "Quick MySQL Schema Fix for Voucher System"
echo "=========================================="

# Default values
MYSQL_USER="voucher_user"
MYSQL_PASS="voucher_password_2024"
MYSQL_DB="voucher_system"
MYSQL_HOST="localhost"

# Use provided arguments or defaults
if [ $# -ge 1 ]; then MYSQL_USER="$1"; fi
if [ $# -ge 2 ]; then MYSQL_PASS="$2"; fi
if [ $# -ge 3 ]; then MYSQL_DB="$3"; fi
if [ $# -ge 4 ]; then MYSQL_HOST="$4"; fi

echo "Connecting to MySQL as $MYSQL_USER@$MYSQL_HOST/$MYSQL_DB..."

# Quick fix - add all missing columns
mysql -h"$MYSQL_HOST" -u"$MYSQL_USER" -p"$MYSQL_PASS" "$MYSQL_DB" -e "
-- Fix omada_config table
ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS refresh_token TEXT AFTER access_token;
ALTER TABLE omada_config ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE AFTER token_expires_at;
UPDATE omada_config SET is_active = TRUE WHERE is_active IS NULL;

-- Fix admin_site table  
ALTER TABLE admin_site ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
UPDATE admin_site SET assigned_at = CURRENT_TIMESTAMP WHERE assigned_at IS NULL;

-- Fix vendor_site table
ALTER TABLE vendor_site ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;  
UPDATE vendor_site SET assigned_at = CURRENT_TIMESTAMP WHERE assigned_at IS NULL;

-- Show results
SELECT 'Schema fix completed successfully!' as status;
SELECT CONCAT('omada_config columns: ', COUNT(*)) as result FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'omada_config' AND table_schema = DATABASE();
SELECT CONCAT('admin_site columns: ', COUNT(*)) as result FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'admin_site' AND table_schema = DATABASE();
SELECT CONCAT('vendor_site columns: ', COUNT(*)) as result FROM INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'vendor_site' AND table_schema = DATABASE();
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Schema fix completed successfully!"
    echo "Your MySQL database should now work properly with the application."
    echo ""
    echo "If you're running the application with supervisor, restart it:"
    echo "sudo supervisorctl restart voucher-app"
else
    echo ""
    echo "❌ Error occurred. Please check your MySQL credentials and try again."
    echo ""
    echo "Usage: $0 [username] [password] [database] [host]"
    echo "Example: $0 voucher_user mypassword voucher_system localhost"
fi