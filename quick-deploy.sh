#!/bin/bash

# Quick deployment script for updates

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting Quick Deployment...${NC}"

cd /var/www/nuril

# Pull latest changes
echo -e "${YELLOW}Pulling latest changes...${NC}"
git pull origin main

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
composer install --no-dev --optimize-autoloader

# Run migrations
echo -e "${YELLOW}Running migrations...${NC}"
php artisan migrate --force

# Clear cache
echo -e "${YELLOW}Clearing cache...${NC}"
php artisan config:cache
php artisan route:cache
php artisan view:cache

# Fix permissions
echo -e "${YELLOW}Fixing permissions...${NC}"
sudo chown -R www-data:www-data storage bootstrap/cache
sudo chmod -R 775 storage bootstrap/cache

# Restart services
echo -e "${YELLOW}Restarting services...${NC}"
sudo systemctl restart php8.1-fpm
sudo systemctl reload nginx

echo -e "${GREEN}Deployment completed successfully!${NC}"
