#!/bin/bash

# MySQL Installation Script for Voucher Management System
# This script sets up the application with MySQL database backend

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run this script as root (use sudo)"
    exit 1
fi

print_status "Starting MySQL installation for Voucher Management System..."

# Update system packages
print_status "Updating system packages..."
apt update && apt upgrade -y

# Install required packages
print_status "Installing required packages..."
apt install -y python3 python3-pip python3-venv mysql-server mysql-client git nginx supervisor ufw

# Install Python MySQL driver
print_status "Installing Python MySQL driver..."
pip3 install pymysql cryptography

# Secure MySQL installation
print_status "Securing MySQL installation..."
mysql_secure_installation

# Get MySQL root password
echo
print_status "Please enter MySQL root password for database setup:"
read -s MYSQL_ROOT_PASSWORD

# Test MySQL connection
print_status "Testing MySQL connection..."
if ! mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "SELECT 1;" > /dev/null 2>&1; then
    print_error "Failed to connect to MySQL. Please check your password."
    exit 1
fi

print_success "MySQL connection successful!"

# Create application directory
APP_DIR="/opt/voucher-system"
print_status "Creating application directory: $APP_DIR"
mkdir -p $APP_DIR
cd $APP_DIR

# Download application files (assuming they're in current directory)
if [ -f "/tmp/voucher-app.tar.gz" ]; then
    print_status "Extracting application files from /tmp/voucher-app.tar.gz"
    tar -xzf /tmp/voucher-app.tar.gz -C $APP_DIR --strip-components=1
else
    print_status "Copying application files from current directory..."
    # Assuming script is run from the project directory
    cp -r . $APP_DIR/
fi

# Set up Python virtual environment
print_status "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
elif [ -f "pyproject.toml" ]; then
    pip install -e .
else
    # Install basic dependencies
    pip install flask flask-sqlalchemy flask-login flask-wtf pymysql gunicorn
fi

# Set up MySQL database
print_status "Setting up MySQL database..."
if [ -f "mysql_setup.sql" ]; then
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" < mysql_setup.sql
    print_success "Database setup completed!"
else
    print_warning "mysql_setup.sql not found. Setting up basic database..."
    mysql -u root -p"$MYSQL_ROOT_PASSWORD" -e "
    CREATE DATABASE IF NOT EXISTS voucher_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE USER IF NOT EXISTS 'voucher_user'@'localhost' IDENTIFIED BY 'voucher_password_2024';
    GRANT ALL PRIVILEGES ON voucher_system.* TO 'voucher_user'@'localhost';
    FLUSH PRIVILEGES;
    "
fi

# Configure environment variables
print_status "Configuring environment variables..."
if [ -f ".env.mysql" ]; then
    cp .env.mysql .env
else
    cat > .env << EOF
SESSION_SECRET=$(openssl rand -hex 32)
DATABASE_URL=mysql+pymysql://voucher_user:voucher_password_2024@localhost:3306/voucher_system
FLASK_ENV=production
FLASK_DEBUG=False
EOF
fi

# Get Omada Controller configuration
echo
print_status "Please enter your Omada Controller configuration:"
read -p "Omada Controller URL (https://your-controller.com:8043): " OMADA_URL
read -p "Omada Client ID: " OMADA_CLIENT_ID
read -p "Omada Client Secret: " OMADA_CLIENT_SECRET
read -p "Omada Controller ID: " OMADA_OMADAC_ID

# Update .env file with Omada configuration
cat >> .env << EOF
OMADA_CONTROLLER_URL=$OMADA_URL
OMADA_CLIENT_ID=$OMADA_CLIENT_ID
OMADA_CLIENT_SECRET=$OMADA_CLIENT_SECRET
OMADA_OMADAC_ID=$OMADA_OMADAC_ID
EOF

# Test database connection
print_status "Testing database connection..."
if python3 -c "
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
conn = engine.connect()
conn.close()
print('Database connection successful!')
" 2>/dev/null; then
    print_success "Database connection test passed!"
else
    print_error "Database connection test failed!"
    exit 1
fi

# Set up Supervisor configuration
print_status "Setting up Supervisor configuration..."
cat > /etc/supervisor/conf.d/voucher-app.conf << EOF
[program:voucher-app]
command=$APP_DIR/venv/bin/gunicorn --bind 127.0.0.1:5000 --workers 2 --timeout 30 --keep-alive 2 --max-requests 1000 --preload main:app
directory=$APP_DIR
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/voucher-app.log
environment=PATH="$APP_DIR/venv/bin"
EOF

# Set up Nginx configuration
print_status "Setting up Nginx configuration..."
cat > /etc/nginx/sites-available/voucher-system << EOF
server {
    listen 80;
    server_name _;
    
    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /static {
        alias $APP_DIR/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/voucher-system /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Set proper permissions
print_status "Setting file permissions..."
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR
chmod 600 $APP_DIR/.env

# Configure firewall
print_status "Configuring firewall..."
ufw --force enable
ufw allow 22
ufw allow 80
ufw allow 443

# Start services
print_status "Starting services..."
systemctl restart supervisor
systemctl restart nginx
systemctl enable supervisor
systemctl enable nginx

# Wait for application to start
print_status "Waiting for application to start..."
sleep 10

# Check if application is running
if curl -f http://localhost > /dev/null 2>&1; then
    print_success "Application is running successfully!"
else
    print_error "Application failed to start. Check logs:"
    print_error "Application logs: tail -f /var/log/voucher-app.log"
    print_error "Supervisor logs: tail -f /var/log/supervisor/supervisord.log"
    print_error "Nginx logs: tail -f /var/log/nginx/error.log"
    exit 1
fi

# Create backup script
print_status "Creating backup script..."
cat > /usr/local/bin/backup-voucher-db.sh << EOF
#!/bin/bash
BACKUP_DIR="/var/backups/voucher-system"
DATE=\$(date +%Y%m%d_%H%M%S)
mkdir -p \$BACKUP_DIR
mysqldump -u voucher_user -pvoucher_password_2024 voucher_system > \$BACKUP_DIR/voucher_system_\$DATE.sql
find \$BACKUP_DIR -name "*.sql" -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup-voucher-db.sh

# Add to crontab for daily backups
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/backup-voucher-db.sh") | crontab -

# Display final information
echo
print_success "=========================================="
print_success "Installation completed successfully!"
print_success "=========================================="
echo
print_status "Application Details:"
print_status "- Application directory: $APP_DIR"
print_status "- Database: MySQL (voucher_system)"
print_status "- Web server: Nginx"
print_status "- Process manager: Supervisor"
print_status "- Application URL: http://$(hostname -I | awk '{print $1}')"
echo
print_status "Default Login Credentials:"
print_status "- Master user: master / admin123"
print_status "- Admin user: joel / admin123"
print_status "- Vendor user: jota / admin123"
echo
print_status "Management Commands:"
print_status "- View logs: tail -f /var/log/voucher-app.log"
print_status "- Restart app: supervisorctl restart voucher-app"
print_status "- Database backup: /usr/local/bin/backup-voucher-db.sh"
echo
print_warning "IMPORTANT: Change default passwords after first login!"
print_warning "Configure your Omada Controller settings in the admin panel."
echo
print_success "Installation complete! Access your application at: http://$(hostname -I | awk '{print $1}')"