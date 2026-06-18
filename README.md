# 🖥️ VPS Manager

A modern, web-based control panel for managing Ubuntu VPS servers. Built with Flask and vanilla JavaScript, featuring a clean dark UI for managing software installations, web server configurations, and domain deployments.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)

## ⚠️ Important Disclaimer

**This project was coded entirely by Claude AI.** While functional, AI-generated code should always be reviewed carefully before use, especially for system administration tools that execute commands with elevated privileges. Please:

- Review all code thoroughly before deployment
- Test in a safe environment first
- Understand the security implications
- Add proper authentication before exposing to any network
- Consider this as a starting point, not production-ready software

## ✨ Features

### 📊 System Monitoring
- Real-time system information (hostname, OS, kernel, uptime)
- Memory and disk usage tracking
- CPU core count and IP address display

### 📦 Software Management
- Check installation status and versions for:
  - **Web**: Node.js, npm, PM2, PHP, Apache, Nginx
  - **Databases**: MySQL, PostgreSQL, Redis
  - **Tools**: Git, Docker, Tesseract OCR, curl, wget
- One-click installation for all supported software
- Python package management via pip

### 🌐 Domain & Site Management
- **Create new sites** with a simple form:
  - Support for both Nginx and Apache
  - PHP directory or Node.js proxy configurations
  - Automatic Git repository cloning
  - Custom install commands
  - Let's Encrypt SSL automation
- **Manage existing sites**:
  - View all configured domains/subdomains
  - Enable/disable sites
  - Edit configuration files directly
  - Delete sites with cleanup
- **Automatic validation**:
  - Syntax checking before applying configs
  - Auto-rollback on configuration errors
  - Safe reload of web servers

### ⚙️ Service Management
- Start, stop, and restart services
- Real-time service status monitoring
- Support for Apache, Nginx, MySQL, PostgreSQL, Redis, Docker

### 💾 Backup & Export
- **One-click download** of all Nginx/Apache site configs in a single `.tar.gz`
- Automatically detects whether the server runs Nginx and/or Apache
- Every archive includes a single `manifest.json` describing the server (web servers, sites, SSL certificates, system info)
- **Full backup** with options for what to include:
  - SSL certificates (Let's Encrypt / certbot)
  - Website files from `/var/www` — choose specific sites (sizes shown) since running sites may be large
  - MySQL databases via `mysqldump` — choose specific databases (sizes shown)
- List, download, and delete previously created backups

### 📥 Import & Restore
- Upload a backup `.tar.gz` (exported from this tool) to restore on the same or a **different** server
- Inspects the archive first and shows what it contains (source host, site configs, SSL certificates, website files with sizes)
- Choose exactly what to restore: Nginx configs, Apache configs, SSL certificates, specific website directories, and MySQL databases
- MySQL databases are imported with `mysqldump` (existing tables dropped & recreated); each database is snapshotted first and rolled back if its import fails
- Web server config is syntax-tested before reload; SSL certificates are domain-bound so they keep working on a new server/IP (point DNS to it and verify renewal)

### 🔁 Server-to-Server Transfer (rsync)
- Copy large websites **directly** to another server over SSH — only changed data is sent and interrupted transfers resume, far more efficient than downloading/uploading huge archives
- Transfer selected `/var/www` sites, web server configs, and SSL certificates in one job
- SSH key or password authentication (password uses `sshpass`), custom port, optional `--rsync-path="sudo rsync"` for remotes that need sudo
- **Test Connection** button, **dry-run** preview, optional `--delete` mirror mode
- Runs in the background with a live progress log (so large transfers don't time out the request) and can be cancelled
- Requires `rsync` on both servers (and `sshpass` on this server for password auth)

## 🚀 Quick Start

### Prerequisites
- Ubuntu 24.04 LTS or compatible
- Python 3.8+
- sudo privileges

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/vps-manager.git
cd vps-manager

# Install Python and dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Configure login credentials
cp .env.example .env
nano .env   # set ADMIN_USERNAME, ADMIN_PASSWORD and SECRET_KEY

# Run the application
python app.py
```

Access the dashboard at `http://YOUR_VPS_IP:5000` and sign in with the
credentials you set in `.env`.

### Authentication

The dashboard is protected by a session-based login. Credentials are read
from a `.env` file (which is git-ignored — never commit it):

```ini
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-password
SECRET_KEY=change-this-to-a-long-random-string
```

Generate a strong secret key with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

All pages and API endpoints require authentication; unauthenticated API
requests receive `401 Unauthorized`.

## 📖 Usage

### Creating a New Site

1. Navigate to the **Domains & Sites** tab
2. Click **+ Add New Site**
3. Fill in the form:
   - **Domain**: `example.com` or `sub.example.com`
   - **Location**: Directory name in `/var/www/`
   - **Web Server**: Choose Nginx or Apache
   - **Type**: PHP directory or Node.js proxy
   - **Port**: For Node.js apps (e.g., 3000)
   - **Git URL**: Optional repository to clone
   - **Install Commands**: Optional (e.g., `npm install && npm run build`)
   - **SSL**: Enable Let's Encrypt certificate
4. Click **Create Site**

The system will:
- Create the document root
- Clone your repository (if provided)
- Run install commands
- Generate and validate the web server config
- Enable the site
- Set up SSL (if requested)

### Editing Site Configurations

1. Find your site in the list
2. Click **Edit** to open the configuration editor
3. Make your changes
4. Click **Save Configuration**

The system validates syntax before applying changes and rolls back on errors.

## 🔧 Production Deployment

For production use, run with Gunicorn behind Nginx:

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 127.0.0.1:5000 app:app

# Or use systemd service (recommended)
sudo nano /etc/systemd/system/vps-manager.service
```

**Example systemd service:**

```ini
[Unit]
Description=VPS Manager
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/vps-manager
Environment="PATH=/opt/vps-manager/venv/bin"
ExecStart=/opt/vps-manager/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

Then proxy through Nginx:

```nginx
server {
    listen 80;
    server_name manager.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔒 Security Considerations

**⚠️ IMPORTANT**: This tool executes commands with sudo privileges.

### Recommendations:
1. **Authentication**: A session-based login is built in — set strong `ADMIN_PASSWORD` and `SECRET_KEY` values in `.env`
2. **Firewall**: Restrict port 5000 to trusted IPs
3. **HTTPS**: Always use SSL in production
4. **VPN**: Run behind a VPN or private network
5. **Sudoers**: Configure specific sudo permissions without password for www-data user

**Example sudoers configuration** (`/etc/sudoers.d/vps-manager`):
```
www-data ALL=(ALL) NOPASSWD: /usr/sbin/nginx, /usr/sbin/apache2ctl, /bin/systemctl
```

## 🛠️ Development

```bash
# Clone and setup
git clone https://github.com/yourusername/vps-manager.git
cd vps-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run in debug mode
python app.py
```

## 📝 API Endpoints

- `GET /api/status` - Software installation status
- `GET /api/system` - System information
- `GET /api/services` - Service status
- `GET /api/webserver` - Web server and sites info
- `POST /api/install/<software>` - Install software
- `POST /api/site/create` - Create new site
- `GET /api/site/config/<server>/<name>` - Get site config
- `POST /api/site/config/<server>/<name>` - Update site config
- `POST /api/site/toggle/<server>/<name>` - Enable/disable site
- `DELETE /api/site/delete/<server>/<name>` - Delete site
- `GET /api/backup/info` - Backup overview (web servers, site counts, certbot, /var/www sizes, saved backups)
- `GET /api/backup/configs` - One-click download of all site configs as a `.tar.gz`
- `POST /api/backup/create` - Create a full backup (options: SSL certs, website files, selected sites)
- `GET /api/backup/download/<filename>` - Download a saved backup
- `DELETE /api/backup/delete/<filename>` - Delete a saved backup
- `POST /api/import/upload` - Upload a backup archive and inspect its contents
- `POST /api/import/apply` - Restore selected parts of an uploaded archive
- `POST /api/import/cancel` - Discard an uploaded archive without restoring
- `POST /api/sync/test` - Test SSH connectivity to a target server
- `POST /api/sync/start` - Start a background rsync transfer to another server
- `GET /api/sync/status/<job_id>` - Poll progress/output of a transfer
- `POST /api/sync/cancel/<job_id>` - Cancel a running transfer

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Designed for Ubuntu Server
- Inspired by modern server management tools

## 📧 Support

If you encounter any issues or have questions, please [open an issue](https://github.com/yourusername/vps-manager/issues) on GitHub.

---

**Made with ❤️ for the DevOps community**
