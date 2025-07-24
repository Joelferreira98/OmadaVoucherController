-- MySQL Database Setup for Voucher Management System
-- Execute this script as MySQL root user or with appropriate privileges

-- Create database
CREATE DATABASE IF NOT EXISTS voucher_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user for the application
CREATE USER IF NOT EXISTS 'voucher_user'@'localhost' IDENTIFIED BY 'voucher_password_2024';

-- Grant privileges
GRANT ALL PRIVILEGES ON voucher_system.* TO 'voucher_user'@'localhost';
FLUSH PRIVILEGES;

-- Use the database
USE voucher_system;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    user_type ENUM('master', 'admin', 'vendor') NOT NULL DEFAULT 'vendor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_user_type (user_type)
);

-- Create sites table
CREATE TABLE IF NOT EXISTS sites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    omada_site_id VARCHAR(255) NOT NULL UNIQUE,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_omada_site_id (omada_site_id)
);

-- Create voucher_plans table
CREATE TABLE IF NOT EXISTS voucher_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    duration_hours INT NOT NULL,
    bandwidth_limit INT,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    site_id INT NOT NULL,
    created_by_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_site_id (site_id),
    INDEX idx_created_by (created_by_id)
);

-- Create voucher_groups table
CREATE TABLE IF NOT EXISTS voucher_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    omada_group_id VARCHAR(255),
    site_id INT NOT NULL,
    plan_id INT NOT NULL,
    created_by_id INT NOT NULL,
    unused_count INT DEFAULT 0,
    used_count INT DEFAULT 0,
    in_use_count INT DEFAULT 0,
    expired_count INT DEFAULT 0,
    last_sync TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES voucher_plans(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_site_id (site_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_created_by_id (created_by_id),
    INDEX idx_omada_group_id (omada_group_id)
);

-- Create admin_site table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS admin_site (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    site_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    UNIQUE KEY unique_admin_site (admin_id, site_id),
    INDEX idx_admin_id (admin_id),
    INDEX idx_site_id (site_id)
);

-- Create vendor_site table (many-to-many relationship)
CREATE TABLE IF NOT EXISTS vendor_site (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vendor_id INT NOT NULL,
    site_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vendor_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    UNIQUE KEY unique_vendor_site (vendor_id, site_id),
    INDEX idx_vendor_id (vendor_id),
    INDEX idx_site_id (site_id)
);

-- Create cash_register table
CREATE TABLE IF NOT EXISTS cash_register (
    id INT AUTO_INCREMENT PRIMARY KEY,
    site_id INT NOT NULL,
    opened_by_id INT NOT NULL,
    closed_by_id INT,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP NULL,
    total_vouchers_sold INT DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0.00,
    voucher_data JSON,
    status ENUM('open', 'closed') DEFAULT 'open',
    notes TEXT,
    FOREIGN KEY (site_id) REFERENCES sites(id) ON DELETE CASCADE,
    FOREIGN KEY (opened_by_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (closed_by_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_site_id (site_id),
    INDEX idx_opened_by_id (opened_by_id),
    INDEX idx_status (status),
    INDEX idx_opened_at (opened_at),
    INDEX idx_closed_at (closed_at)
);

-- Create omada_config table for API configuration
CREATE TABLE IF NOT EXISTS omada_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    controller_url VARCHAR(500) NOT NULL,
    client_id VARCHAR(255) NOT NULL,
    client_secret VARCHAR(255) NOT NULL,
    omadac_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    token_expires_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default master user (password: admin123)
INSERT IGNORE INTO users (username, email, password_hash, user_type) VALUES 
('master', 'master@sistema.com', 'scrypt:32768:8:1$UxqRZrFq9H2AGfbh$3e1b8f8d2c4a5e7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7', 'master');

-- Insert test admin user (password: admin123)
INSERT IGNORE INTO users (username, email, password_hash, user_type) VALUES 
('joel', 'joel@sistema.com', 'scrypt:32768:8:1$UxqRZrFq9H2AGfbh$3e1b8f8d2c4a5e7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7', 'admin');

-- Insert test vendor user (password: admin123)
INSERT IGNORE INTO users (username, email, password_hash, user_type) VALUES 
('jota', 'jota@sistema.com', 'scrypt:32768:8:1$UxqRZrFq9H2AGfbh$3e1b8f8d2c4a5e7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7', 'vendor');

-- Create indexes for better performance
CREATE INDEX idx_voucher_groups_created_at ON voucher_groups(created_at);
CREATE INDEX idx_cash_register_date_range ON cash_register(opened_at, closed_at);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Show database information
SELECT 'Database setup completed successfully!' as message;
SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'voucher_system';
SELECT table_name, table_rows FROM information_schema.tables WHERE table_schema = 'voucher_system' ORDER BY table_name;