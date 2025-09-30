# Download ulang script tanpa pengecekan root
cat > /tmp/nuri-installer-root.sh << 'EOF'
#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔══════════════════════════════╗"
echo "║    NURI PROJECT INSTALLER    ║"
echo "║        (ROOT VERSION)        ║"
echo "╚══════════════════════════════╝"
echo -e "${NC}"

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%T')]${NC} $1"
}

# Step 1: System Update
log "Step 1: Updating system packages..."
apt update
apt upgrade -y
apt install -y curl wget git unzip

# Step 2: Install PHP
log "Step 2: Installing PHP and extensions..."
apt install -y php8.1 php8.1-fpm php8.1-mysql php8.1-curl \
php8.1-mbstring php8.1-xml php8.1-zip php8.1-gd php8.1-bcmath

# Step 3: Install MySQL
log "Step 3: Installing MySQL database..."
apt install -y mysql-server mysql-client

# Step 4: Install Nginx
log "Step 4: Installing Nginx web server..."
apt install -y nginx

# Step 5: Install Composer
log "Step 5: Installing Composer..."
curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

# Step 6: Create Project Directory
log "Step 6: Setting up project directory..."
mkdir -p /var/www/nuri
cd /var/www/nuri

# Step 7: Clone Repository
log "Step 7: Cloning repository from GitHub..."
git clone https://github.com/amifistore/nuri.git .
chown -R www-data:www-data /var/www/nuri

# Step 8: Install PHP Dependencies
log "Step 8: Installing PHP dependencies..."
composer install --no-dev --optimize-autoloader

# Step 9: Setup Environment
log "Step 9: Setting up environment configuration..."
cp .env.example .env
php artisan key:generate

# Step 10: Setup Database
log "Step 10: Setting up database..."
db_name="nuri_db"
db_user="nuri_user"
db_pass=$(openssl rand -base64 12)

# Create database and user
mysql -e "CREATE DATABASE IF NOT EXISTS $db_name;"
mysql -e "CREATE USER IF NOT EXISTS '$db_user'@'localhost' IDENTIFIED BY '$db_pass';"
mysql -e "GRANT ALL PRIVILEGES ON $db_name.* TO '$db_user'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"

# Update .env file
sed -i "s/DB_DATABASE=.*/DB_DATABASE=$db_name/" .env
sed -i "s/DB_USERNAME=.*/DB_USERNAME=$db_user/" .env
sed -i "s/DB_PASSWORD=.*/DB_PASSWORD=$db_pass/" .env

# Step 11: Run Database Migrations
log "Step 11: Running database migrations..."
php artisan migrate --force

# Step 12: Setup Storage
log "Step 12: Setting up storage..."
php artisan storage:link
chmod -R 775 storage
chmod -R 775 bootstrap/cache

# Step 13: Configure Nginx
log "Step 13: Configuring Nginx..."
cat > /etc/nginx/sites-available/nuri << 'NGINX_CONFIG'
server {
    listen 80;
    server_name _;
    root /var/www/nuri/public;
    index index.php index.html index.htm;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~ /\.ht {
        deny all;
    }
}
NGINX_CONFIG

# Enable site
ln -sf /etc/nginx/sites-available/nuri /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Step 14: Test Nginx Configuration
log "Step 14: Testing Nginx configuration..."
nginx -t

# Step 15: Set Permissions
log "Step 15: Setting permissions..."
chown -R www-data:www-data /var/www/nuri
chmod -R 755 /var/www/nuri
chmod -R 775 /var/www/nuri/storage
chmod -R 775 /var/www/nuri/bootstrap/cache

# Step 16: Restart Services
log "Step 16: Restarting services..."
systemctl restart nginx
systemctl restart php8.1-fpm
systemctl enable nginx
systemctl enable php8.1-fpm

# Completion Message
echo
echo -e "${GREEN}"
echo "╔════════════════════════════════════════╗"
echo "║          INSTALLATION COMPLETE!        ║"
echo "╠════════════════════════════════════════╣"
echo "║ Project: NURI                          ║"
echo "║ Location: /var/www/nuri                ║"
echo "║ Database: $db_name                     ║"
echo "║ Database User: $db_user                ║"
echo "║ Database Password: $db_pass            ║"
echo "║ Access: http://your-server-ip          ║"
echo "╚════════════════════════════════════════╝"
echo -e "${NC}"

# Get IP address
ip_address=$(hostname -I | awk '{print $1}')
echo "Application URL: http://$ip_address"
echo
echo "Database credentials saved above ↑"
EOF

# Beri permission dan jalankan
chmod +x /tmp/nuri-installer-root.sh
./nuri-installer-root.sh
