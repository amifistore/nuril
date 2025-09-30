#!/bin/bash

# Basic server security setup

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Basic Server Setup...${NC}"

# Update system
sudo apt update && sudo apt upgrade -y

# Install basic utilities
sudo apt install -y ufw fail2ban htop nethogs

# Setup firewall
echo -e "${YELLOW}Setting up firewall...${NC}"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw --force enable

# Create swap file if not exists
if [ ! -f /swapfile ]; then
    echo -e "${YELLOW}Creating swap file...${NC}"
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# Optimize PHP-FPM
echo -e "${YELLOW}Optimizing PHP-FPM...${NC}"
sudo sed -i 's/^pm.max_children = .*/pm.max_children = 50/' /etc/php/8.1/fpm/pool.d/www.conf
sudo sed -i 's/^pm.start_servers = .*/pm.start_servers = 10/' /etc/php/8.1/fpm/pool.d/www.conf
sudo sed -i 's/^pm.min_spare_servers = .*/pm.min_spare_servers = 5/' /etc/php/8.1/fpm/pool.d/www.conf
sudo sed -i 's/^pm.max_spare_servers = .*/pm.max_spare_servers = 15/' /etc/php/8.1/fpm/pool.d/www.conf

sudo systemctl restart php8.1-fpm

echo -e "${GREEN}Server setup completed!${NC}"
