-- Fix MySQL Schema - Add missing columns to omada_config table
-- Execute this script if you get errors about missing columns

USE voucher_system;

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

-- Update existing records to have is_active = TRUE if NULL
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

-- Show current table structures
DESCRIBE omada_config;
DESCRIBE admin_site;
DESCRIBE vendor_site;

-- Show confirmation message
SELECT 'MySQL schema update completed successfully!' as status;