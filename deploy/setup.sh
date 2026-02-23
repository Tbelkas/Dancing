#!/usr/bin/env bash
set -e

# Dance Platform – Raspberry Pi Setup Script
# Run as root or with sudo.

echo "=== Dance Platform Setup ==="

# 1. System packages
apt-get update
apt-get install -y \
    postgresql \
    postgresql-client \
    apache2 \
    libapache2-mod-proxy-html \
    libxml2-dev

# 2. Enable Apache modules
a2enmod proxy proxy_http rewrite headers
systemctl restart apache2

# 3. Install .NET 8 runtime (ARM64/ARM32)
curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 8.0 --runtime aspnetcore --install-dir /usr/share/dotnet
ln -sf /usr/share/dotnet/dotnet /usr/bin/dotnet

# 4. PostgreSQL – create user and database
DB_USER="dance_user"
DB_NAME="dance_platform"
DB_PASS="changeme"

sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" 2>/dev/null || true

# 5. Deploy API
mkdir -p /opt/dance-platform/api
cp -r api-publish/* /opt/dance-platform/api/
chown -R www-data:www-data /opt/dance-platform

# Update connection string in appsettings
sed -i "s/Username=dance_user;Password=changeme/Username=${DB_USER};Password=${DB_PASS}/" \
    /opt/dance-platform/api/appsettings.json

# 6. Run EF migrations
cd /opt/dance-platform/api
dotnet DancePlatform.API.dll --migrate || true

# 7. Install systemd service
cp dance-platform.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dance-platform
systemctl start dance-platform

# 8. Deploy Angular app
mkdir -p /var/www/dance-platform
cp -r ui-dist/* /var/www/dance-platform/
chown -R www-data:www-data /var/www/dance-platform

# 9. Configure Apache
cp apache2.conf /etc/apache2/sites-available/dance-platform.conf
a2ensite dance-platform
a2dissite 000-default
systemctl reload apache2

echo ""
echo "=== Setup Complete ==="
echo "API: http://localhost:5000"
echo "UI:  http://dance.local (or your Pi's IP)"
