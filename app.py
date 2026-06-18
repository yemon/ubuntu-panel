from flask import Flask, render_template, jsonify, request, send_file, abort, session, redirect, url_for
import subprocess
import shutil
import os
import re
import json
import datetime
import hmac
import shlex

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


def run_cmd_detailed(cmd, timeout=120):
    """Run a shell command and return success, output and any error text.

    Unlike run_cmd(), this preserves stderr so callers can show the user a
    clear explanation of why something failed.
    """
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "returncode": -1, "stdout": "",
                "stderr": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "returncode": -1, "stdout": "", "stderr": str(e)}


def _tail(text, lines=3, limit=400):
    """Return the last few lines of command output, trimmed for display."""
    if not text:
        return ""
    snippet = " ".join(text.strip().splitlines()[-lines:])
    return snippet[:limit] + ("…" if len(snippet) > limit else "")

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
        return jsonify({"success": False, "message": f"Unknown software '{software}'."}), 400

    # Update apt first so package metadata is fresh.
    update = run_cmd_detailed("sudo apt-get update")
    if not update["success"]:
        return jsonify({"success": False,
                        "message": f"'apt-get update' failed, cannot install {software}: {_tail(update['stderr'] or update['stdout'])}"}), 500

    res = run_cmd_detailed(INSTALL_COMMANDS[software])
    present = bool(shutil.which(software))
    if res["success"] and present:
        return jsonify({"success": True, "message": f"{software} installed successfully and is now available."})
    if res["success"]:
        return jsonify({"success": True,
                        "message": f"{software} installation finished. If the command differs from the package name it may already be ready to use."})
    return jsonify({"success": False,
                    "message": f"Failed to install {software}: {_tail(res['stderr'] or res['stdout']) or 'no output captured. Check that the server has sudo and internet access.'}"}), 500

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
        return jsonify({"success": False, "message": f"Invalid action '{action}'."}), 400

    res = run_cmd_detailed(f"sudo systemctl {action} {service}")
    if res["success"]:
        return jsonify({"success": True, "message": f"Service '{service}' {action}ed successfully."})
    detail = _tail(res["stderr"] or res["stdout"]) or "no details returned"
    return jsonify({"success": False, "message": f"Failed to {action} '{service}': {detail}"}), 500

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


# --- MySQL helpers ---
# Credentials are optional: if MYSQL_USER is set (in .env) they are used,
# otherwise we rely on root socket auth via sudo (the Ubuntu default).
MYSQL_USER = os.environ.get("MYSQL_USER", "")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_SYSTEM_DBS = {"information_schema", "performance_schema", "mysql", "sys"}
_DB_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def mysql_available():
    """True if mysqldump/mysql client tools are installed."""
    return shutil.which("mysqldump") is not None and shutil.which("mysql") is not None


def _mysql_auth(binary):
    """Prefix a mysql/mysqldump invocation with credentials if configured."""
    if MYSQL_USER:
        return f"MYSQL_PWD={shlex.quote(MYSQL_PASSWORD)} {binary} -u {shlex.quote(MYSQL_USER)}"
    return binary


def _mysql_run(inner):
    """Run a mysql-related command as root via sudo (so socket auth works)."""
    return run_cmd_detailed(f"sudo bash -c {shlex.quote(inner)}")


def list_mysql_databases():
    """List user databases with sizes (excludes MySQL's own system schemas)."""
    if not mysql_available():
        return []
    show = _mysql_run(f"{_mysql_auth('mysql')} -N -e 'SHOW DATABASES'")
    if not show["success"]:
        return []
    names = [d for d in show["stdout"].splitlines() if d and d not in MYSQL_SYSTEM_DBS]
    sizes = {}
    sql = ("SELECT table_schema, ROUND(SUM(data_length+index_length)/1024/1024,1) "
           "FROM information_schema.tables GROUP BY table_schema")
    res = _mysql_run(f"{_mysql_auth('mysql')} -N -e {shlex.quote(sql)}")
    if res["success"]:
        for line in res["stdout"].splitlines():
            p = line.split("\t")
            if len(p) >= 2:
                sizes[p[0]] = p[1]
    return [{"name": n, "size": f"{sizes.get(n, '0')} MB"} for n in names]


def _dump_database(db, dest):
    """Dump a single database (incl. CREATE DATABASE) to a .sql file."""
    inner = f"{_mysql_auth('mysqldump')} --databases {shlex.quote(db)} > {shlex.quote(dest)}"
    return _mysql_run(inner)


def _import_sql(sqlfile):
    """Load a .sql dump back into MySQL."""
    return _mysql_run(f"{_mysql_auth('mysql')} < {shlex.quote(sqlfile)}")


def _db_exists(db):
    res = _mysql_run(f"{_mysql_auth('mysql')} -N -e 'SHOW DATABASES'")
    return res["success"] and db in res["stdout"].splitlines()


def _drop_database(db):
    return _mysql_run(f"{_mysql_auth('mysql')} -e {shlex.quote('DROP DATABASE IF EXISTS `' + db + '`')}")


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
        "mysql": {"available": mysql_available(), "databases": list_mysql_databases()},
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
    copied = _copy_configs(staging)
    _write_manifest(staging, build_manifest({"type": "configs-only"}))
    tar = run_cmd_detailed(f"sudo tar czf {archive} -C /tmp {name}")
    run_cmd(f"sudo chmod 644 {archive}")
    run_cmd(f"sudo rm -rf {staging}")

    if not os.path.exists(archive):
        detail = _tail(tar["stderr"]) or "could not write the archive (check disk space and sudo access)."
        return jsonify({"success": False, "message": f"Failed to build configs archive: {detail}"}), 500
    if not copied:
        # Nothing to archive but still return the (manifest-only) file with a hint via header.
        pass
    return send_file(archive, as_attachment=True, download_name=f"{name}.tar.gz")


@app.route("/api/backup/create", methods=["POST"])
def backup_create():
    """Create a full backup with the requested options and store it for download."""
    data = request.get_json() or {}
    include_certbot = bool(data.get("include_certbot", False))
    include_site_files = bool(data.get("include_site_files", False))
    include_mysql = bool(data.get("include_mysql", False))
    selected_sites = data.get("sites", []) or []  # dir names under /var/www; empty = all
    selected_dbs = data.get("mysql_databases", []) or []  # db names; empty = all

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

    included_dbs = []
    if include_mysql and mysql_available():
        run_cmd(f"sudo mkdir -p {staging}/mysql")
        for db in [d["name"] for d in list_mysql_databases()]:
            if (not selected_dbs or db in selected_dbs) and _safe(db, _DB_RE):
                res = _dump_database(db, f"{staging}/mysql/{db}.sql")
                if res["success"]:
                    included_dbs.append(db)

    _write_manifest(staging, build_manifest({
        "type": "full",
        "include_certbot": include_certbot,
        "include_site_files": include_site_files,
        "included_sites": included_sites,
        "include_mysql": include_mysql,
        "included_databases": included_dbs,
    }))

    archive = f"{BACKUP_DIR}/{name}.tar.gz"
    tar = run_cmd_detailed(f"sudo tar czf {archive} -C {BACKUP_DIR} {name}")
    run_cmd(f"sudo chmod 644 {archive}")
    run_cmd(f"sudo rm -rf {staging}")

    if not os.path.exists(archive):
        detail = _tail(tar["stderr"]) or "could not write the archive (check disk space and sudo access)."
        return jsonify({"success": False, "message": f"Failed to create backup: {detail}"}), 500

    st = os.stat(archive)
    parts = ["web server configs"]
    if include_certbot:
        parts.append("SSL certificates")
    if included_sites:
        parts.append(f"{len(included_sites)} website(s)")
    if included_dbs:
        parts.append(f"{len(included_dbs)} database(s)")
    return jsonify({
        "success": True,
        "message": f"Backup created ({human_bytes(st.st_size)}) including: {', '.join(parts)}.",
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


# ============ IMPORT / RESTORE ============

IMPORTS_DIR = "/var/tmp/vps-manager-imports"


def _ls(path):
    """List entries of a (possibly root-owned) directory, ignoring errors."""
    out = run_cmd(f"sudo ls -1 {path} 2>/dev/null")
    return [x for x in out.split("\n") if x] if out else []


def _import_root(token):
    """Resolve an import token to the extracted archive's content directory."""
    if not token or not re.match(r"^[A-Za-z0-9_]+$", token):
        return None
    staging = os.path.join(IMPORTS_DIR, token)
    if not os.path.isdir(staging):
        return None
    # Archives created by this tool contain a single top-level directory.
    entries = [e for e in _ls(staging) if not e.startswith(".")]
    if len(entries) == 1 and run_cmd(f"sudo test -d {staging}/{entries[0]} && echo y") == "y":
        return os.path.join(staging, entries[0])
    return staging


@app.route("/api/import/upload", methods=["POST"])
def import_upload():
    """Receive a backup archive, extract it, and report what it contains."""
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"success": False, "message": "No file selected"}), 400
    if not f.filename.endswith(".tar.gz"):
        return jsonify({"success": False, "message": "File must be a .tar.gz archive"}), 400

    token = "import_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + os.urandom(3).hex()
    upload_path = f"/tmp/{token}.tar.gz"
    f.save(upload_path)

    # Validate it is a readable gzip tarball before doing anything with sudo.
    if run_cmd(f"tar tzf {upload_path} >/dev/null 2>&1 && echo ok") != "ok":
        run_cmd(f"rm -f {upload_path}")
        return jsonify({"success": False, "message": "Invalid or corrupted .tar.gz archive"}), 400

    staging = os.path.join(IMPORTS_DIR, token)
    run_cmd(f"sudo mkdir -p {staging}")
    run_cmd(f"sudo tar xzf {upload_path} -C {staging}")
    run_cmd(f"rm -f {upload_path}")

    root = _import_root(token)
    if not root:
        return jsonify({"success": False, "message": "Could not read archive contents"}), 400

    manifest = {}
    manifest_raw = run_cmd(f"sudo cat {root}/manifest.json 2>/dev/null")
    if manifest_raw:
        try:
            manifest = json.loads(manifest_raw)
        except ValueError:
            manifest = {}

    certbot_present = run_cmd(f"sudo test -d {root}/letsencrypt && echo yes") == "yes"
    www_dirs = []
    out = run_cmd(f"sudo du -sb {root}/www/* 2>/dev/null")
    if out:
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) == 2 and parts[0].isdigit():
                size = int(parts[0])
                www_dirs.append({
                    "name": os.path.basename(parts[1]),
                    "bytes": size,
                    "size": human_bytes(size),
                })

    mysql_dumps = [f[:-4] for f in _ls(f"{root}/mysql") if f.endswith(".sql")]

    return jsonify({
        "success": True,
        "token": token,
        "manifest": manifest,
        "nginx_configs": _ls(f"{root}/nginx/sites-available"),
        "apache_configs": _ls(f"{root}/apache2/sites-available"),
        "certbot": {
            "present": certbot_present,
            "domains": [d for d in _ls(f"{root}/letsencrypt/live") if d != "README"],
        },
        "www_dirs": www_dirs,
        "mysql": {"available": mysql_available(), "databases": mysql_dumps},
    })


def _step(name, status, detail):
    """Build one structured restore-step result for the UI."""
    return {"name": name, "status": status, "detail": detail}


def _dir_exists(path):
    return run_cmd(f"sudo test -d {path} && echo y") == "y"


def _restore_webserver(name, root_sub, live_dirs, rollback_sub, test_cmd, reload_cmd):
    """Restore a web server's site config dirs, with snapshot + rollback.

    Snapshots the current live dirs, copies the archived configs in, then runs
    the syntax test. On any failure the live dirs are reverted to the snapshot
    and the server is reloaded with the known-good config.
    """
    run_cmd(f"sudo mkdir -p {rollback_sub}")
    snapshots = {}  # live dir -> snapshot path (or None if it didn't exist)
    for d in live_dirs:
        snap = os.path.join(rollback_sub, os.path.basename(d))
        if _dir_exists(d):
            run_cmd(f"sudo cp -a {d} {snap}")
            snapshots[d] = snap
        else:
            snapshots[d] = None

    def _rollback():
        for live, snap in snapshots.items():
            run_cmd(f"sudo rm -rf {live}")
            if snap:
                run_cmd(f"sudo cp -a {snap} {live}")
            else:
                run_cmd(f"sudo mkdir -p {live}")
        run_cmd(reload_cmd)

    # Copy the archived configs into place.
    for d in live_dirs:
        sub = os.path.join(root_sub, os.path.basename(d))
        if _dir_exists(sub):
            run_cmd(f"sudo mkdir -p {d}")
            run_cmd(f"sudo cp -a {sub}/. {d}/")
    count = len(_ls(os.path.join(root_sub, "sites-available")))

    test = run_cmd_detailed(test_cmd)
    if not test["success"]:
        _rollback()
        err = _tail(test["stderr"] or test["stdout"]) or "unknown configuration error"
        return _step(name, "error",
                     f"Configuration test failed, so the restore was ROLLED BACK to the previous working config. "
                     f"The server was not changed. Reason: {err}")

    reload_res = run_cmd_detailed(reload_cmd)
    if not reload_res["success"]:
        _rollback()
        err = _tail(reload_res["stderr"] or reload_res["stdout"]) or "unknown reload error"
        return _step(name, "error",
                     f"Config test passed but reloading the server failed, so the restore was ROLLED BACK. Reason: {err}")

    return _step(name, "success",
                 f"Restored {count} config file(s); configuration test passed and the server was reloaded successfully.")


@app.route("/api/import/apply", methods=["POST"])
def import_apply():
    """Restore selected parts of a previously uploaded backup archive.

    Every component is snapshotted before being overwritten and automatically
    rolled back if its step fails. Returns a per-step report for the UI.
    """
    data = request.get_json() or {}
    token = data.get("token", "")
    root = _import_root(token)
    if not root:
        return jsonify({"success": False,
                        "message": "Import session not found — please re-upload the archive and try again.",
                        "steps": []}), 400

    selected_sites = data.get("sites", []) or []
    rollback_dir = os.path.join(IMPORTS_DIR, token + "_rollback")
    run_cmd(f"sudo rm -rf {rollback_dir}")
    run_cmd(f"sudo mkdir -p {rollback_dir}")
    steps = []

    # ---- Nginx ----
    if data.get("restore_nginx"):
        if _dir_exists(f"{root}/nginx/sites-available"):
            steps.append(_restore_webserver(
                "Nginx site configs", f"{root}/nginx",
                ["/etc/nginx/sites-available", "/etc/nginx/sites-enabled"],
                f"{rollback_dir}/nginx", "sudo nginx -t", "sudo systemctl reload nginx"))
        else:
            steps.append(_step("Nginx site configs", "skipped", "No Nginx configs were found in this archive."))

    # ---- Apache ----
    if data.get("restore_apache"):
        if _dir_exists(f"{root}/apache2/sites-available"):
            steps.append(_restore_webserver(
                "Apache site configs", f"{root}/apache2",
                ["/etc/apache2/sites-available", "/etc/apache2/sites-enabled"],
                f"{rollback_dir}/apache2", "sudo apachectl configtest", "sudo systemctl reload apache2"))
        else:
            steps.append(_step("Apache site configs", "skipped", "No Apache configs were found in this archive."))

    # ---- SSL / certbot ----
    if data.get("restore_certbot"):
        if _dir_exists(f"{root}/letsencrypt"):
            existed = _dir_exists("/etc/letsencrypt")
            snap = f"{rollback_dir}/letsencrypt"
            if existed:
                run_cmd(f"sudo cp -a /etc/letsencrypt {snap}")
            run_cmd("sudo mkdir -p /etc/letsencrypt")
            res = run_cmd_detailed(f"sudo cp -a {root}/letsencrypt/. /etc/letsencrypt/")
            if res["success"]:
                domains = [d for d in _ls(f"{root}/letsencrypt/live") if d != "README"]
                steps.append(_step("SSL certificates", "success",
                                   f"Restored {len(domains)} certificate(s): {', '.join(domains) or 'none'}. "
                                   f"Certificates are domain-bound and will work on this server's IP; "
                                   f"run 'certbot renew --dry-run' to confirm renewal."))
            else:
                run_cmd("sudo rm -rf /etc/letsencrypt")
                if existed:
                    run_cmd(f"sudo cp -a {snap} /etc/letsencrypt")
                steps.append(_step("SSL certificates", "error",
                                   f"Copy failed and was ROLLED BACK. Reason: {_tail(res['stderr']) or 'unknown error'}"))
        else:
            steps.append(_step("SSL certificates", "skipped", "No SSL certificates were found in this archive."))

    # ---- Website files ----
    if data.get("restore_site_files"):
        if _dir_exists(f"{root}/www"):
            restored, failed = [], []
            for site in _ls(f"{root}/www"):
                if selected_sites and site not in selected_sites:
                    continue
                dest = f"/var/www/{site}"
                backup = f"{rollback_dir}/www_{site}"
                existed = _dir_exists(dest)
                if existed:
                    run_cmd(f"sudo mv {dest} {backup}")  # fast rename for rollback
                run_cmd(f"sudo mkdir -p {dest}")
                res = run_cmd_detailed(f"sudo cp -a {root}/www/{site}/. {dest}/")
                if res["success"]:
                    run_cmd(f"sudo chown -R www-data:www-data {dest}")
                    if existed:
                        run_cmd(f"sudo rm -rf {backup}")
                    restored.append(site)
                else:
                    run_cmd(f"sudo rm -rf {dest}")
                    if existed:
                        run_cmd(f"sudo mv {backup} {dest}")  # rollback
                    failed.append(f"{site} ({_tail(res['stderr']) or 'copy error'})")
            if restored:
                steps.append(_step("Website files", "success",
                                   f"Restored {len(restored)} site(s) into /var/www and set ownership to www-data: {', '.join(restored)}."))
            if failed:
                steps.append(_step("Website files", "error",
                                   f"Failed and ROLLED BACK for: {'; '.join(failed)}."))
            if not restored and not failed:
                steps.append(_step("Website files", "skipped", "No matching website directories were found in this archive."))
        else:
            steps.append(_step("Website files", "skipped", "No website files were found in this archive."))

    # ---- MySQL databases ----
    if data.get("restore_mysql"):
        if not _dir_exists(f"{root}/mysql"):
            steps.append(_step("MySQL databases", "skipped", "No database dumps were found in this archive."))
        elif not mysql_available():
            steps.append(_step("MySQL databases", "error",
                               "MySQL client tools are not installed on this server, so the databases could not be "
                               "restored. Install MySQL first, then re-run the import."))
        else:
            selected_dbs = data.get("databases", []) or []
            run_cmd(f"sudo mkdir -p {rollback_dir}/mysql")
            restored, failed = [], []
            for f in _ls(f"{root}/mysql"):
                if not f.endswith(".sql"):
                    continue
                db = f[:-4]
                if selected_dbs and db not in selected_dbs:
                    continue
                if not _safe(db, _DB_RE):
                    failed.append(f"{db} (invalid database name)")
                    continue
                existed = _db_exists(db)
                if existed:
                    _dump_database(db, f"{rollback_dir}/mysql/{db}.sql")  # snapshot for rollback
                res = _import_sql(f"{root}/mysql/{f}")
                if res["success"]:
                    restored.append(db)
                else:
                    _drop_database(db)
                    if existed:
                        _import_sql(f"{rollback_dir}/mysql/{db}.sql")  # rollback
                    failed.append(f"{db} ({_tail(res['stderr']) or 'import error'})")
            if restored:
                steps.append(_step("MySQL databases", "success",
                                   f"Imported {len(restored)} database(s): {', '.join(restored)}. "
                                   f"Existing tables were dropped and recreated from the dump."))
            if failed:
                steps.append(_step("MySQL databases", "error",
                                   f"Failed and ROLLED BACK for: {'; '.join(failed)}."))
            if not restored and not failed:
                steps.append(_step("MySQL databases", "skipped", "No matching database dumps were found in this archive."))

    # Clean up staging + rollback (system is already in a consistent state).
    run_cmd(f"sudo rm -rf {os.path.join(IMPORTS_DIR, token)}")
    run_cmd(f"sudo rm -rf {rollback_dir}")

    actioned = [s for s in steps if s["status"] != "skipped"]
    if not actioned:
        return jsonify({"success": False,
                        "message": "Nothing was restored — either no items were selected or the archive had no matching content.",
                        "steps": steps}), 400

    errors = [s for s in steps if s["status"] == "error"]
    if errors:
        message = (f"Restore finished with {len(errors)} failure(s) (each was rolled back automatically). "
                   f"See the details below.")
    else:
        message = f"Restore completed successfully — {len(actioned)} item(s) restored."
    return jsonify({"success": not errors, "message": message, "steps": steps})


@app.route("/api/import/cancel", methods=["POST"])
def import_cancel():
    """Discard an uploaded archive that was not applied."""
    token = (request.get_json() or {}).get("token", "")
    if token and re.match(r"^[A-Za-z0-9_]+$", token):
        run_cmd(f"sudo rm -rf {os.path.join(IMPORTS_DIR, token)}")
    return jsonify({"success": True})


# ============ SERVER-TO-SERVER SYNC (rsync over SSH) ============

SYNC_DIR = "/tmp/vps-manager-sync"
sync_jobs = {}  # job_id -> {proc, log, remote, pwfile, ...}

_USER_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
_HOST_RE = re.compile(r"^[a-zA-Z0-9.:_-]+$")
_PATH_RE = re.compile(r"^/[a-zA-Z0-9._/-]+$")
_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def _safe(value, pattern):
    """Validate a value against a strict allowlist pattern (blocks shell injection)."""
    return bool(value) and bool(pattern.match(value)) and ".." not in value


def _build_ssh(data):
    """Build the ssh command used by rsync. Returns (ok, ssh_cmd, pwfile, error)."""
    port = str(data.get("port", "22"))
    if not re.match(r"^\d{1,5}$", port):
        return False, None, None, "Invalid SSH port."
    opts = f"-p {port} -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
    pwfile = None
    if data.get("auth") == "password":
        pw = data.get("password", "")
        if not pw:
            return False, None, None, "Password is required for password authentication."
        os.makedirs(SYNC_DIR, exist_ok=True)
        tmp = f"/tmp/.pw_{os.urandom(6).hex()}"
        with open(tmp, "w") as fh:
            fh.write(pw)
        pwfile = f"{SYNC_DIR}/.pw_{os.urandom(6).hex()}"
        run_cmd(f"sudo mv {shlex.quote(tmp)} {shlex.quote(pwfile)} && sudo chmod 600 {shlex.quote(pwfile)}")
        ssh = f"sshpass -f {shlex.quote(pwfile)} ssh {opts}"
    else:
        key = (data.get("key") or "").strip()
        if key:
            if not _safe(key, _PATH_RE):
                return False, None, None, "Invalid SSH key path."
            opts += f" -i {key}"
        opts += " -o BatchMode=yes"  # fail instead of hanging on a password prompt
        ssh = f"ssh {opts}"
    return True, ssh, pwfile, None


@app.route("/api/sync/test", methods=["POST"])
def sync_test():
    """Verify SSH connectivity to the target server before a large transfer."""
    data = request.get_json() or {}
    user, host = data.get("user", ""), data.get("host", "")
    if not _safe(user, _USER_RE):
        return jsonify({"success": False, "message": "Invalid remote username."}), 400
    if not _safe(host, _HOST_RE):
        return jsonify({"success": False, "message": "Invalid remote host."}), 400
    ok, ssh, pwfile, err = _build_ssh(data)
    if not ok:
        return jsonify({"success": False, "message": err}), 400
    res = run_cmd_detailed(f'sudo {ssh} {user}@{host} "echo connection_ok"', timeout=30)
    if pwfile:
        run_cmd(f"sudo rm -f {shlex.quote(pwfile)}")
    if res["success"] and "connection_ok" in res["stdout"]:
        return jsonify({"success": True, "message": f"Connected to {user}@{host} successfully."})
    return jsonify({"success": False,
                    "message": f"Connection to {user}@{host} failed: {_tail(res['stderr'] or res['stdout']) or 'no response (check host, port, and credentials).'}"}), 400


@app.route("/api/sync/start", methods=["POST"])
def sync_start():
    """Start a background rsync transfer of selected data to another server."""
    data = request.get_json() or {}
    user, host = data.get("user", ""), data.get("host", "")
    if not _safe(user, _USER_RE):
        return jsonify({"success": False, "message": "Invalid remote username."}), 400
    if not _safe(host, _HOST_RE):
        return jsonify({"success": False, "message": "Invalid remote host."}), 400

    dest_base = data.get("dest_base") or "/var/www"
    if not _safe(dest_base, _PATH_RE):
        return jsonify({"success": False, "message": "Invalid destination path."}), 400

    sites = data.get("sites", []) or []
    for s in sites:
        if not _safe(s, _NAME_RE):
            return jsonify({"success": False, "message": f"Invalid site name '{s}'."}), 400

    include_configs = bool(data.get("include_configs"))
    include_certbot = bool(data.get("include_certbot"))
    if not sites and not include_configs and not include_certbot:
        return jsonify({"success": False, "message": "Select at least one thing to transfer."}), 400

    ok, ssh, pwfile, err = _build_ssh(data)
    if not ok:
        return jsonify({"success": False, "message": err}), 400

    flags = "-az --info=progress2 --human-readable"
    if data.get("dry_run"):
        flags += " --dry-run"
    if data.get("delete"):
        flags += " --delete"
    rsync_path = ' --rsync-path="sudo rsync"' if data.get("remote_sudo", True) else ""
    remote = f"{user}@{host}"

    lines = ['echo "Starting transfer to %s"' % remote]
    if data.get("dry_run"):
        lines.append('echo "(DRY RUN — no files will actually be written)"')
    if sites:
        srcs = " ".join(f"/var/www/{s}" for s in sites)
        lines.append(f'echo "=== Website files -> {remote}:{dest_base} ==="')
        lines.append(f'rsync {flags}{rsync_path} -e "{ssh}" {srcs} {remote}:{dest_base}/')
    if include_configs:
        if os.path.exists(NGINX_SITES_AVAILABLE):
            lines.append('echo "=== Nginx configs ==="')
            lines.append(f'rsync {flags}{rsync_path} -e "{ssh}" /etc/nginx/sites-available /etc/nginx/sites-enabled {remote}:/etc/nginx/')
        if os.path.exists(APACHE_SITES_AVAILABLE):
            lines.append('echo "=== Apache configs ==="')
            lines.append(f'rsync {flags}{rsync_path} -e "{ssh}" /etc/apache2/sites-available /etc/apache2/sites-enabled {remote}:/etc/apache2/')
    if include_certbot and os.path.exists(LETSENCRYPT_DIR):
        lines.append('echo "=== SSL certificates ==="')
        lines.append(f'rsync {flags}{rsync_path} -e "{ssh}" /etc/letsencrypt {remote}:/etc/')
    lines.append('echo "All transfers finished."')

    job_id = "sync_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + os.urandom(3).hex()
    os.makedirs(SYNC_DIR, exist_ok=True)
    log = f"{SYNC_DIR}/{job_id}.log"
    script = " && \\\n".join(lines)
    full = f"sudo bash -c {shlex.quote(script)} > {shlex.quote(log)} 2>&1; echo EXIT_CODE:$? >> {shlex.quote(log)}"

    proc = subprocess.Popen(full, shell=True)
    sync_jobs[job_id] = {"proc": proc, "log": log, "remote": remote, "pwfile": pwfile,
                         "started": datetime.datetime.now().isoformat()}
    return jsonify({"success": True, "job_id": job_id,
                    "message": f"Transfer to {remote} started in the background."})


@app.route("/api/sync/status/<job_id>")
def sync_status(job_id):
    """Report progress/output of a running or finished sync job."""
    if not re.match(r"^[A-Za-z0-9_]+$", job_id):
        return jsonify({"success": False, "message": "Invalid job id."}), 400
    log = f"{SYNC_DIR}/{job_id}.log"
    job = sync_jobs.get(job_id)
    if not job and not os.path.exists(log):
        return jsonify({"success": False, "message": "Job not found."}), 404

    output = ""
    if os.path.exists(log):
        with open(log, errors="replace") as fh:
            output = fh.read()[-8000:]

    running = bool(job and job["proc"].poll() is None)
    if job and not running and job.get("pwfile"):
        run_cmd(f"sudo rm -f {shlex.quote(job['pwfile'])}")  # clean up password file
        job["pwfile"] = None

    done = not running and ("EXIT_CODE:" in output or (job and job["proc"].poll() is not None))
    ok = None
    if done:
        m = re.search(r"EXIT_CODE:(\d+)", output)
        code = int(m.group(1)) if m else (job["proc"].returncode if job else 1)
        ok = code == 0
    return jsonify({"success": True, "running": running, "done": done, "ok": ok, "output": output})


@app.route("/api/sync/cancel/<job_id>", methods=["POST"])
def sync_cancel(job_id):
    """Best-effort cancellation of a running sync job."""
    job = sync_jobs.get(job_id)
    if not job or job["proc"].poll() is not None:
        return jsonify({"success": False, "message": "No running transfer to cancel."}), 400
    run_cmd(f"sudo pkill -P {job['proc'].pid}")  # kill the sudo/rsync children
    job["proc"].terminate()
    if job.get("pwfile"):
        run_cmd(f"sudo rm -f {shlex.quote(job['pwfile'])}")
        job["pwfile"] = None
    return jsonify({"success": True, "message": "Transfer cancelled."})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
