#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Jangan jalankan script ini sebagai root user!"
    log_info "Gunakan user biasa atau buat user baru"
    exit 1
fi

# Display banner
echo -e "${GREEN}"
cat << "EOF"
 _   _ _   _ ___ _   _ 
| \ | | | | |_ _| | | |
|  \| | | | || || | | |
| |\  | |_| || || |_| |
|_| \_|\___/|___|\___/ 
                        
EOF
echo -e "${NC}"

log_info "Starting Nuril Project Installation..."
sleep 2

# Step 1: System Update
log_info "Step 1: Update sistem..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip

# Step 2: Install PHP
log_info "Step 2: Install PHP dan ekstensi..."
sudo apt install -y php8.1 php8.1-cli php8.1-fpm php8.1-mysql php8.1-curl \
php8.1-gd php8.1-mbstring php8.1-xml php8.1-zip php8.1-bcmath \
php8.1-common php8.1-json php8.1-tokenizer php8.1-ctype

# Step 3: Install MySQL
log_info "Step 3: Install MySQL Database..."
sudo apt install -y mysql-server mysql-client

# Step 4: Install Nginx
log_info "Step 4: Install Nginx Web Server..."
sudo apt install -y nginx

# Step 5: Install Composer
log_info "Step 5: Install Composer..."
curl -sS https://getcomposer.org/installer | sudo php -- --install-dir=/usr/local/bin --filename=composer

# Step 6: Clone Repository
log_info "Step 6: Clone repository dari GitHub..."
cd /var/www
sudo rm -rf nuril
sudo git clone https://github.com/amifistore/nuril.git
sudo chown -R $USER:$USER /var/www/nuril
cd nuril

# Step 7: Install PHP Dependencies
log_info "Step 7: Install dependencies PHP..."
composer install --no-dev --optimize-autoloader

# Step 8: Setup Environment
log_info "Step 8: Setup environment..."
cp .env.example .env
php artisan key:generate

# Step 9: Setup Database
log_info "Step 9: Setup database..."
read -p "Masukkan nama database (default: nuril_db): " db_name
db_name=${db_name:-nuril_db}

read -p "Masukkan username database (default: nuril_user): " db_user
db_user=${db_user:-nuril_user}

read -s -p "Masukkan password database: " db_pass
echo

# Create database and user
sudo mysql -e "CREATE DATABASE IF NOT EXISTS $db_name;"
sudo mysql -e "CREATE USER IF NOT EXISTS '$db_user'@'localhost' IDENTIFIED BY '$db_pass';"
sudo mysql - NOT EXISTS '$db_user'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Update .env with database credentials
sed -i "s/DB_DATABASE=.*/DB_DATABASE=$db_name/" .env
sed -i "s/DB_USERNAME=.*/DB_USERNAME=$db_user/" .env
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$db_pass/" .env

# Step 10: Run Migrations
log_info "Step 10: Run database migrations..."
php artisan migrate --force

# Step 11: Setup Storage
log_info "Step 11: Setup storage..."
php artisan storage:link
sudo chmod -R 775 storage
sudo chmod -R 775 bootstrap/cache

# Step 12: Setup Nginx
log_info "Step 12: Setup Nginx virtual host..."

sudo tee /etc/nginx/sites-available/nuril > /dev/null << EOF
server {
    listen 80;
    server_name _;
    root /var/www/nuril/public;
    index index.php index.html index.htm;

    location / {
        try_files \$uri \$uri/ /index.php?\$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$realpath_root\$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }

    error_log /var/log/nginx/nuril_error.log;
    access_log /var/log/nginx/nuril_access.log;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/nuril /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Step 13: Test Configuration
log_info "Step 13: Test konfigurasi Nginx..."
sudo nginx -t

if [ $? -eq 0 ]; then
    log_success "Konfigurasi Nginx valid"
else
    log_error "Konfigurasi Nginx error, periksa file konfigurasi"
    exit 1
fi

# Step 14: Restart Services
log_info "Step 14: Restart services..."
sudo systemctl restart nginx
sudo systemctl restart php8.1-fpm
sudo systemctl enable nginx
sudo systemctl enable php8.1-fpm

# Step 15: Setup Cron Job
log_info "Step 15: Setup cron job untuk scheduler..."
(crontab -l 2>/dev/null; echo "* * * * * cd /var/www/nuril && php artisan schedule:run >> /dev/null 2>&1") | crontab -

# Step 16: Fix Permissions
log_info "Step 16: Fix permissions..."
sudo chown -R www-data:www-data /var/www/nuril/storage
sudo chown -R www-data:www-data /var/www/nuril/bootstrap/cache
sudo chmod -R 775 /var/www/nuril/storage
sudo chmod -R 775 /var/www/nuril/bootstrap/cache

# Installation Complete
log_success "=================================================="
log_success "INSTALASI BERHASIL!"
log_success "=================================================="
log_info "Akses aplikasi via: http://$(curl -s ifconfig.me)"
log_info "Directory: /var/www/nuril"
log_info "Database: $db_name"
log_info "File konfigurasi: /var/www/nuril/.env"
log_info "Nginx config: /etc/nginx/sites-available/nuril"
echo
log_warning "Jangan lupa:"
log_warning "1. Setup domain di .env (APP_URL)"
log_warning "2. Setup mail configuration jika perlu"
log_warning "3. Run 'php artisan db:seed' untuk sample data"
log_warning "4. Setup SSL certificate dengan certbot"
