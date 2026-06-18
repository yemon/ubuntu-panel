from flask import Flask, render_template, jsonify, request, send_file, abort, session, redirect, url_for
import subprocess
import shutil
import os
import re
import json
import datetime
import hmac

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional; fall back to real environment variables.
    pass

app = Flask(__name__)

# Session signing key. Set SECRET_KEY in .env; a random key is used as a
# fallback (which invalidates existing sessions whenever the app restarts).
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

# Login credentials, read from the environment / .env file.
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


@app.before_request
def require_login():
    """Gate every request behind a logged-in session."""
    if request.endpoint in ("login", "static"):
        return
    if session.get("logged_in"):
        return
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "message": "Authentication required"}), 401
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Render the login page and authenticate credentials."""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        valid = (
            bool(ADMIN_PASSWORD)
            and hmac.compare_digest(username, ADMIN_USERNAME)
            and hmac.compare_digest(password, ADMIN_PASSWORD)
        )
        if valid:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid username or password"), 401
    if session.get("logged_in"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Clear the session and return to the login page."""
    session.clear()
    return redirect(url_for("login"))

NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"
APACHE_SITES_AVAILABLE = "/etc/apache2/sites-available"
APACHE_SITES_ENABLED = "/etc/apache2/sites-enabled"

def run_cmd(cmd):
    """Run shell command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def get_version(cmd):
    """Get version from command output"""
    output = run_cmd(cmd)
    return output if output else "Not installed"

def check_service_status(service):
    """Check if a service is active"""
    result = run_cmd(f"systemctl is-active {service}")
    return result == "active"

SOFTWARE_CHECKS = {
    "node": {"version_cmd": "node --version", "name": "Node.js"},
    "npm": {"version_cmd": "npm --version", "name": "NPM"},
    "pm2": {"version_cmd": "pm2 --version", "name": "PM2"},
    "php": {"version_cmd": "php --version | head -n1", "name": "PHP"},
    "apache2": {"version_cmd": "apache2 -v | head -n1", "name": "Apache"},
    "nginx": {"version_cmd": "nginx -v 2>&1", "name": "Nginx"},
    "tesseract": {"version_cmd": "tesseract --version | head -n1", "name": "Tesseract OCR"},
    "python3": {"version_cmd": "python3 --version", "name": "Python 3"},
    "pip3": {"version_cmd": "pip3 --version", "name": "Pip3"},
    "git": {"version_cmd": "git --version", "name": "Git"},
    "docker": {"version_cmd": "docker --version", "name": "Docker"},
    "mysql": {"version_cmd": "mysql --version", "name": "MySQL"},
    "postgresql": {"version_cmd": "psql --version", "name": "PostgreSQL"},
    "redis": {"version_cmd": "redis-server --version", "name": "Redis"},
    "curl": {"version_cmd": "curl --version | head -n1", "name": "cURL"},
    "wget": {"version_cmd": "wget --version | head -n1", "name": "Wget"},
}


INSTALL_COMMANDS = {
    "node": "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs",
    "npm": "sudo apt-get install -y npm",
    "pm2": "sudo npm install -g pm2",
    "php": "sudo apt-get install -y php php-cli php-fpm php-mysql php-curl php-gd php-mbstring php-xml php-zip",
    "apache2": "sudo apt-get install -y apache2",
    "nginx": "sudo apt-get install -y nginx",
    "tesseract": "sudo apt-get install -y tesseract-ocr tesseract-ocr-eng",
    "python3": "sudo apt-get install -y python3 python3-venv",
    "pip3": "sudo apt-get install -y python3-pip",
    "git": "sudo apt-get install -y git",
    "docker": "curl -fsSL https://get.docker.com | sudo sh",
    "mysql": "sudo apt-get install -y mysql-server",
    "postgresql": "sudo apt-get install -y postgresql postgresql-contrib",
    "redis": "sudo apt-get install -y redis-server",
    "curl": "sudo apt-get install -y curl",
    "wget": "sudo apt-get install -y wget",
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def get_status():
    """Get installation status of all software"""
    status = {}
    for key, info in SOFTWARE_CHECKS.items():
        version = get_version(info["version_cmd"])
        installed = version != "Not installed"
        status[key] = {
            "name": info["name"],
            "installed": installed,
            "version": version
        }
    return jsonify(status)

@app.route("/api/system")
def get_system_info():
    """Get system information"""
    info = {
        "hostname": run_cmd("hostname") or "Unknown",
        "os": run_cmd("lsb_release -d | cut -f2") or "Unknown",
        "kernel": run_cmd("uname -r") or "Unknown",
        "uptime": run_cmd("uptime -p") or "Unknown",
        "memory": run_cmd("free -h | awk '/^Mem:/ {print $3 \"/\" $2}'") or "Unknown",
        "disk": run_cmd("df -h / | awk 'NR==2 {print $3 \"/\" $2 \" (\" $5 \" used)\"}'") or "Unknown",
        "cpu": run_cmd("nproc") or "Unknown",
        "ip": run_cmd("hostname -I | awk '{print $1}'") or "Unknown"
    }
    return jsonify(info)

@app.route("/api/install/<software>", methods=["POST"])
def install_software(software):
    """Install specified software"""
    if software not in INSTALL_COMMANDS:
        return jsonify({"success": False, "message": "Unknown software"}), 400
    
    # Update apt first
    run_cmd("sudo apt-get update")
    
    result = run_cmd(INSTALL_COMMANDS[software])
    if result is not None or shutil.which(software):
        return jsonify({"success": True, "message": f"{software} installed successfully"})
    return jsonify({"success": False, "message": f"Failed to install {software}"}), 500

@app.route("/api/services")
def get_services():
    """Get status of common services"""
    services = ["apache2", "nginx", "mysql", "postgresql", "redis-server", "docker"]
    status = {}
    for svc in services:
        status[svc] = {
            "active": check_service_status(svc),
            "enabled": run_cmd(f"systemctl is-enabled {svc}") == "enabled"
        }
    return jsonify(status)

@app.route("/api/service/<action>/<service>", methods=["POST"])
def manage_service(action, service):
    """Start/stop/restart a service"""
    if action not in ["start", "stop", "restart", "enable", "disable"]:
        return jsonify({"success": False, "message": "Invalid action"}), 400
    
    result = run_cmd(f"sudo systemctl {action} {service}")
    return jsonify({"success": True, "message": f"Service {service} {action}ed"})

@app.route("/api/pip/install", methods=["POST"])
def install_pip_package():
    """Install a Python package via pip"""
    data = request.get_json()
    package = data.get("package", "")
    if not package:
        return jsonify({"success": False, "message": "No package specified"}), 400
    
    result = run_cmd(f"pip3 install {package}")
    if result is not None:
        return jsonify({"success": True, "message": f"{package} installed"})
    return jsonify({"success": False, "message": f"Failed to install {package}"}), 500

@app.route("/api/pip/list")
def list_pip_packages():
    """List installed pip packages"""
    output = run_cmd("pip3 list --format=json")
    if output:
        return jsonify(json.loads(output))
    return jsonify([])

# ============ DOMAIN/SITE MANAGEMENT ============

def detect_web_server():
    """Detect which web server is active"""
    nginx_active = check_service_status("nginx")
    apache_active = check_service_status("apache2")
    return {"nginx": nginx_active, "apache": apache_active}

def get_nginx_sites():
    """Get all nginx sites"""
    sites = []
    if os.path.exists(NGINX_SITES_AVAILABLE):
        for filename in os.listdir(NGINX_SITES_AVAILABLE):
            filepath = os.path.join(NGINX_SITES_AVAILABLE, filename)
            enabled_path = os.path.join(NGINX_SITES_ENABLED, filename)
            if os.path.isfile(filepath):
                content = run_cmd(f"sudo cat {filepath}") or ""
                server_name = re.search(r'server_name\s+([^;]+);', content)
                root = re.search(r'root\s+([^;]+);', content)
                proxy = re.search(r'proxy_pass\s+([^;]+);', content)
                sites.append({
                    "name": filename,
                    "enabled": os.path.exists(enabled_path),
                    "server_name": server_name.group(1).strip() if server_name else "",
                    "root": root.group(1).strip() if root else "",
                    "proxy": proxy.group(1).strip() if proxy else "",
                    "type": "proxy" if proxy else "static"
                })
    return sites

def get_apache_sites():
    """Get all apache sites"""
    sites = []
    if os.path.exists(APACHE_SITES_AVAILABLE):
        for filename in os.listdir(APACHE_SITES_AVAILABLE):
            filepath = os.path.join(APACHE_SITES_AVAILABLE, filename)
            enabled_path = os.path.join(APACHE_SITES_ENABLED, filename)
            if os.path.isfile(filepath):
                content = run_cmd(f"sudo cat {filepath}") or ""
                server_name = re.search(r'ServerName\s+(\S+)', content)
                doc_root = re.search(r'DocumentRoot\s+(\S+)', content)
                proxy = re.search(r'ProxyPass\s+/\s+([^\s]+)', content)
                sites.append({
                    "name": filename,
                    "enabled": os.path.exists(enabled_path),
                    "server_name": server_name.group(1) if server_name else "",
                    "root": doc_root.group(1) if doc_root else "",
                    "proxy": proxy.group(1) if proxy else "",
                    "type": "proxy" if proxy else "static"
                })
    return sites

@app.route("/api/webserver")
def get_webserver_info():
    """Get web server status and sites"""
    servers = detect_web_server()
    return jsonify({
        "servers": servers,
        "nginx_sites": get_nginx_sites() if servers["nginx"] or os.path.exists(NGINX_SITES_AVAILABLE) else [],
        "apache_sites": get_apache_sites() if servers["apache"] or os.path.exists(APACHE_SITES_AVAILABLE) else []
    })

@app.route("/api/site/config/<server>/<name>")
def get_site_config(server, name):
    """Get site configuration content"""
    if server == "nginx":
        path = os.path.join(NGINX_SITES_AVAILABLE, name)
    else:
        path = os.path.join(APACHE_SITES_AVAILABLE, name)
    
    content = run_cmd(f"sudo cat {path}")
    return jsonify({"content": content or "", "path": path})

@app.route("/api/site/config/<server>/<name>", methods=["POST"])
def save_site_config(server, name):
    """Save site configuration"""
    data = request.get_json()
    content = data.get("content", "")
    
    if server == "nginx":
        path = os.path.join(NGINX_SITES_AVAILABLE, name)
    else:
        path = os.path.join(APACHE_SITES_AVAILABLE, name)
    
    # Write to temp file then move with sudo
    temp_path = f"/tmp/{name}.conf.tmp"
    with open(temp_path, "w") as f:
        f.write(content)
    
    run_cmd(f"sudo mv {temp_path} {path}")
    
    # Test and reload
    if server == "nginx":
        test = run_cmd("sudo nginx -t 2>&1")
        if "successful" in (test or ""):
            run_cmd("sudo systemctl reload nginx")
            return jsonify({"success": True, "message": "Config saved and nginx reloaded"})
        return jsonify({"success": False, "message": f"Config error: {test}"}), 400
    else:
        run_cmd("sudo systemctl reload apache2")
        return jsonify({"success": True, "message": "Config saved and apache reloaded"})

@app.route("/api/site/toggle/<server>/<name>", methods=["POST"])
def toggle_site(server, name):
    """Enable/disable a site"""
    if server == "nginx":
        available = os.path.join(NGINX_SITES_AVAILABLE, name)
        enabled = os.path.join(NGINX_SITES_ENABLED, name)
        if os.path.exists(enabled):
            run_cmd(f"sudo rm {enabled}")
            action = "disabled"
        else:
            run_cmd(f"sudo ln -s {available} {enabled}")
            action = "enabled"
        run_cmd("sudo systemctl reload nginx")
    else:
        if run_cmd(f"sudo a2query -s {name.replace('.conf', '')}"):
            run_cmd(f"sudo a2dissite {name}")
            action = "disabled"
        else:
            run_cmd(f"sudo a2ensite {name}")
            action = "enabled"
        run_cmd("sudo systemctl reload apache2")
    
    return jsonify({"success": True, "message": f"Site {action}"})

@app.route("/api/site/delete/<server>/<name>", methods=["DELETE"])
def delete_site(server, name):
    """Delete a site configuration"""
    if server == "nginx":
        run_cmd(f"sudo rm -f {NGINX_SITES_ENABLED}/{name}")
        run_cmd(f"sudo rm -f {NGINX_SITES_AVAILABLE}/{name}")
        run_cmd("sudo systemctl reload nginx")
    else:
        run_cmd(f"sudo a2dissite {name}")
        run_cmd(f"sudo rm -f {APACHE_SITES_AVAILABLE}/{name}")
        run_cmd("sudo systemctl reload apache2")
    
    return jsonify({"success": True, "message": "Site deleted"})

@app.route("/api/site/create", methods=["POST"])
def create_site():
    """Create a new site/domain"""
    data = request.get_json()
    domain = data.get("domain", "").strip()
    location = data.get("location", "").strip()
    site_type = data.get("type", "php")  # php or node
    port = data.get("port", "3000")
    git_url = data.get("git_url", "").strip()
    install_cmd = data.get("install_cmd", "").strip()
    ssl = data.get("ssl", False)
    server = data.get("server", "nginx")  # nginx or apache
    
    if not domain or not location:
        return jsonify({"success": False, "message": "Domain and location required"}), 400
    
    # Create document root
    doc_root = f"/var/www/{location}"
    run_cmd(f"sudo mkdir -p {doc_root}")
    run_cmd(f"sudo chown -R www-data:www-data {doc_root}")
    
    # Clone git repo if provided
    if git_url:
        run_cmd(f"sudo rm -rf {doc_root}/*")
        result = run_cmd(f"sudo git clone {git_url} {doc_root}")
        run_cmd(f"sudo chown -R www-data:www-data {doc_root}")
    
    # Run install commands if provided
    if install_cmd:
        run_cmd(f"cd {doc_root} && sudo {install_cmd}")
    
    # Generate config
    config_name = domain.replace(".", "_")
    
    if server == "nginx":
        if site_type == "node":
            config = f"""server {{
    listen 80;
    server_name {domain};
    
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
        else:  # PHP
            config = f"""server {{
    listen 80;
    server_name {domain};
    root {doc_root};
    index index.php index.html;
    
    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}
    
    location ~ \\.php$ {{
        fastcgi_pass unix:/var/run/php/php-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
    }}
    
    location ~ /\\.ht {{
        deny all;
    }}
}}
"""
        config_path = f"{NGINX_SITES_AVAILABLE}/{config_name}"
        temp_path = f"/tmp/{config_name}.tmp"
        with open(temp_path, "w") as f:
            f.write(config)
        run_cmd(f"sudo mv {temp_path} {config_path}")
        run_cmd(f"sudo ln -sf {config_path} {NGINX_SITES_ENABLED}/{config_name}")
        
        # Test nginx config before reload
        test_result = run_cmd("sudo nginx -t 2>&1")
        if test_result and "successful" in test_result:
            run_cmd("sudo systemctl reload nginx")
        else:
            # Rollback on failure
            run_cmd(f"sudo rm -f {NGINX_SITES_ENABLED}/{config_name}")
            run_cmd(f"sudo rm -f {config_path}")
            return jsonify({"success": False, "message": f"Nginx config error: {test_result}"}), 400
        
    else:  # Apache
        if site_type == "node":
            config = f"""<VirtualHost *:80>
    ServerName {domain}
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:{port}/
    ProxyPassReverse / http://127.0.0.1:{port}/
</VirtualHost>
"""
        else:  # PHP
            config = f"""<VirtualHost *:80>
    ServerName {domain}
    DocumentRoot {doc_root}
    
    <Directory {doc_root}>
        AllowOverride All
        Require all granted
    </Directory>
    
    ErrorLog ${{APACHE_LOG_DIR}}/{domain}_error.log
    CustomLog ${{APACHE_LOG_DIR}}/{domain}_access.log combined
</VirtualHost>
"""
        config_path = f"{APACHE_SITES_AVAILABLE}/{config_name}.conf"
        temp_path = f"/tmp/{config_name}.conf.tmp"
        with open(temp_path, "w") as f:
            f.write(config)
        run_cmd(f"sudo mv {temp_path} {config_path}")
        run_cmd(f"sudo a2ensite {config_name}.conf")
        if site_type == "node":
            run_cmd("sudo a2enmod proxy proxy_http")
        
        # Test apache config before reload
        test_result = run_cmd("sudo apachectl configtest 2>&1")
        if test_result and "Syntax OK" in test_result:
            run_cmd("sudo systemctl reload apache2")
        else:
            # Rollback on failure
            run_cmd(f"sudo a2dissite {config_name}.conf")
            run_cmd(f"sudo rm -f {config_path}")
            return jsonify({"success": False, "message": f"Apache config error: {test_result}"}), 400
    
    # SSL with Let's Encrypt
    if ssl:
        run_cmd("sudo apt-get install -y certbot")
        if server == "nginx":
            run_cmd("sudo apt-get install -y python3-certbot-nginx")
            run_cmd(f"sudo certbot --nginx -d {domain} --non-interactive --agree-tos --register-unsafely-without-email")
        else:
            run_cmd("sudo apt-get install -y python3-certbot-apache")
            run_cmd(f"sudo certbot --apache -d {domain} --non-interactive --agree-tos --register-unsafely-without-email")
    
    return jsonify({"success": True, "message": f"Site {domain} created successfully"})

# ============ BACKUP / EXPORT ============

BACKUP_DIR = "/var/backups/vps-manager"
NGINX_CONFIG_DIR = "/etc/nginx"
APACHE_CONFIG_DIR = "/etc/apache2"
LETSENCRYPT_DIR = "/etc/letsencrypt"
WWW_DIR = "/var/www"


def human_bytes(num):
    """Format a byte count into a human readable string."""
    num = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


def list_certbot_domains():
    """List domains that have Let's Encrypt certificates."""
    out = run_cmd(f"sudo ls {LETSENCRYPT_DIR}/live 2>/dev/null")
    if not out:
        return []
    return [d for d in out.split() if d != "README"]


def list_www_dirs():
    """List website directories under /var/www with their sizes."""
    dirs = []
    out = run_cmd(f"sudo du -sb {WWW_DIR}/* 2>/dev/null")
    if out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 2 and parts[0].isdigit():
                size = int(parts[0])
                dirs.append({
                    "name": os.path.basename(parts[1]),
                    "path": parts[1],
                    "bytes": size,
                    "size": human_bytes(size),
                })
    return dirs


def list_backups():
    """List previously created backup archives."""
    backups = []
    if os.path.exists(BACKUP_DIR):
        for f in sorted(os.listdir(BACKUP_DIR), reverse=True):
            if f.endswith(".tar.gz"):
                path = os.path.join(BACKUP_DIR, f)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                backups.append({
                    "name": f,
                    "bytes": st.st_size,
                    "size": human_bytes(st.st_size),
                    "created": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    return backups


def build_manifest(options=None):
    """Build the single descriptive config file that travels inside a backup."""
    servers = detect_web_server()
    return {
        "tool": "VPS Manager Backup",
        "version": 1,
        "generated_at": datetime.datetime.now().isoformat(),
        "system": {
            "hostname": run_cmd("hostname") or "Unknown",
            "os": run_cmd("lsb_release -d | cut -f2") or "Unknown",
            "kernel": run_cmd("uname -r") or "Unknown",
            "ip": run_cmd("hostname -I | awk '{print $1}'") or "Unknown",
        },
        "web_servers": {
            "nginx": {"installed": os.path.exists(NGINX_CONFIG_DIR), "running": servers["nginx"]},
            "apache": {"installed": os.path.exists(APACHE_CONFIG_DIR), "running": servers["apache"]},
        },
        "nginx_sites": get_nginx_sites() if os.path.exists(NGINX_SITES_AVAILABLE) else [],
        "apache_sites": get_apache_sites() if os.path.exists(APACHE_SITES_AVAILABLE) else [],
        "ssl": {"certbot": os.path.exists(LETSENCRYPT_DIR), "certificates": list_certbot_domains()},
        "options": options or {},
    }


def _copy_configs(staging):
    """Copy the active web server config trees into a staging directory."""
    copied = []
    if os.path.exists(NGINX_CONFIG_DIR):
        run_cmd(f"sudo cp -a {NGINX_CONFIG_DIR} {staging}/nginx")
        copied.append("nginx")
    if os.path.exists(APACHE_CONFIG_DIR):
        run_cmd(f"sudo cp -a {APACHE_CONFIG_DIR} {staging}/apache2")
        copied.append("apache2")
    return copied


def _write_manifest(staging, manifest):
    """Write the manifest JSON into a (possibly root-owned) staging directory."""
    tmp = f"/tmp/manifest_{os.getpid()}.json"
    with open(tmp, "w") as fh:
        json.dump(manifest, fh, indent=2)
    run_cmd(f"sudo mv {tmp} {staging}/manifest.json")


def _safe_backup_path(filename):
    """Resolve a user-supplied backup name to a safe path inside BACKUP_DIR."""
    base = os.path.basename(filename)
    if not base.endswith(".tar.gz"):
        return None
    path = os.path.join(BACKUP_DIR, base)
    if not os.path.isfile(path):
        return None
    return path


@app.route("/api/backup/info")
def backup_info():
    """Summarise what can be backed up so the UI can offer options."""
    servers = detect_web_server()
    return jsonify({
        "servers": {
            "nginx": {"installed": os.path.exists(NGINX_CONFIG_DIR), "running": servers["nginx"]},
            "apache": {"installed": os.path.exists(APACHE_CONFIG_DIR), "running": servers["apache"]},
        },
        "nginx_site_count": len(get_nginx_sites()) if os.path.exists(NGINX_SITES_AVAILABLE) else 0,
        "apache_site_count": len(get_apache_sites()) if os.path.exists(APACHE_SITES_AVAILABLE) else 0,
        "certbot": {"present": os.path.exists(LETSENCRYPT_DIR), "domains": list_certbot_domains()},
        "www_dirs": list_www_dirs(),
        "backups": list_backups(),
    })


@app.route("/api/backup/configs")
def backup_configs():
    """One-click: build and stream a single archive of all site configs + manifest."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"site-configs_{ts}"
    staging = f"/tmp/{name}"
    archive = f"/tmp/{name}.tar.gz"

    run_cmd(f"sudo rm -rf {staging}")
    run_cmd(f"sudo mkdir -p {staging}")
    _copy_configs(staging)
    _write_manifest(staging, build_manifest({"type": "configs-only"}))
    run_cmd(f"sudo tar czf {archive} -C /tmp {name}")
    run_cmd(f"sudo chmod 644 {archive}")
    run_cmd(f"sudo rm -rf {staging}")

    if not os.path.exists(archive):
        return jsonify({"success": False, "message": "Failed to build configs archive"}), 500
    return send_file(archive, as_attachment=True, download_name=f"{name}.tar.gz")


@app.route("/api/backup/create", methods=["POST"])
def backup_create():
    """Create a full backup with the requested options and store it for download."""
    data = request.get_json() or {}
    include_certbot = bool(data.get("include_certbot", False))
    include_site_files = bool(data.get("include_site_files", False))
    selected_sites = data.get("sites", []) or []  # dir names under /var/www; empty = all

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"backup_{ts}"
    run_cmd(f"sudo mkdir -p {BACKUP_DIR}")
    staging = f"{BACKUP_DIR}/{name}"
    run_cmd(f"sudo rm -rf {staging}")
    run_cmd(f"sudo mkdir -p {staging}")

    _copy_configs(staging)

    if include_certbot and os.path.exists(LETSENCRYPT_DIR):
        run_cmd(f"sudo cp -a {LETSENCRYPT_DIR} {staging}/letsencrypt")

    included_sites = []
    if include_site_files:
        run_cmd(f"sudo mkdir -p {staging}/www")
        for d in list_www_dirs():
            if not selected_sites or d["name"] in selected_sites:
                run_cmd(f"sudo cp -a {d['path']} {staging}/www/{d['name']}")
                included_sites.append(d["name"])

    _write_manifest(staging, build_manifest({
        "type": "full",
        "include_certbot": include_certbot,
        "include_site_files": include_site_files,
        "included_sites": included_sites,
    }))

    archive = f"{BACKUP_DIR}/{name}.tar.gz"
    run_cmd(f"sudo tar czf {archive} -C {BACKUP_DIR} {name}")
    run_cmd(f"sudo chmod 644 {archive}")
    run_cmd(f"sudo rm -rf {staging}")

    if not os.path.exists(archive):
        return jsonify({"success": False, "message": "Failed to create backup"}), 500
    st = os.stat(archive)
    return jsonify({
        "success": True,
        "message": f"Backup created ({human_bytes(st.st_size)})",
        "name": f"{name}.tar.gz",
        "size": human_bytes(st.st_size),
    })


@app.route("/api/backup/download/<filename>")
def backup_download(filename):
    """Download a previously created backup archive."""
    path = _safe_backup_path(filename)
    if not path:
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@app.route("/api/backup/delete/<filename>", methods=["DELETE"])
def backup_delete(filename):
    """Delete a stored backup archive."""
    path = _safe_backup_path(filename)
    if not path:
        return jsonify({"success": False, "message": "Backup not found"}), 404
    run_cmd(f"sudo rm -f {path}")
    return jsonify({"success": True, "message": "Backup deleted"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
