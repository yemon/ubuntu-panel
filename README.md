# 🖥️ VPS Manager

A modern, web-based control panel for managing Ubuntu VPS servers. Built with Flask and vanilla JavaScript, featuring a clean dark UI for managing software installations, web server configurations, and domain deployments.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)

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

## 🚀 Quick Start

### Prerequisites
- Ubuntu 23.04 LTS or compatible
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

# Run the application
python app.py
```

Access the dashboard at `http://YOUR_VPS_IP:5000`

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
1. **Use authentication**: Add Flask-Login or HTTP basic auth
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
