🚀 CARA PENGGUNAAN:
1. Download dan persiapan:
bash
# Download script
wget https://raw.githubusercontent.com/amifistore/nuril/main/installer.sh
wget https://raw.githubusercontent.com/amifistore/nuril/main/quick-deploy.sh
wget https://raw.githubusercontent.com/amifistore/nuril/main/setup-server.sh

# Berikan permission executable
chmod +x installer.sh quick-deploy.sh setup-server.sh
2. Jalankan installer:
bash
# Jalankan installer utama
./installer.sh

# Setup server security (optional)
./setup-server.sh
3. Untuk update deployment:
bash
./quick-deploy.sh
📋 FITUR INSTALLER:
✅ Auto system update

✅ Install PHP 8.1 + extensions

✅ Install MySQL database

✅ Install Nginx web server

✅ Setup virtual host otomatis

✅ Konfigurasi database otomatis

✅ Setup environment file

✅ Run migrations

✅ Fix permissions

✅ Setup cron job

✅ Security basic setup

🛡️ KEAMANAN TAMBAHAN:
Setelah instalasi, jalankan:

bash
# Setup SSL dengan Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com

# Secure MySQL
sudo mysql_secure_installation
Semua script sudah termasuk error handling dan log yang jelas. Pastikan VPS Anda memiliki minimal 1GB RAM dan 20GB storage untuk menjalankan aplikasi dengan lancar.

