from flask import Flask, render_template, jsonify, request
import subprocess
import shutil
import os
import re
import json

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
