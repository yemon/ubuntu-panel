# Security Policy

## ⚠️ Security Warning

VPS Manager executes system commands with sudo privileges. This is necessary for managing server configurations but requires careful security considerations.

## Recommended Security Measures

### 1. Authentication
The default installation has **no authentication**. Before exposing to any network:

- Add Flask-Login or Flask-HTTPAuth
- Use strong passwords
- Consider OAuth2 for team access

### 2. Network Security
- **Firewall**: Restrict port 5000 to trusted IPs only
- **VPN**: Run behind a VPN or private network
- **Reverse Proxy**: Use Nginx/Apache with SSL
- **Never expose directly to the internet without authentication**

### 3. Sudo Configuration
Limit sudo permissions to specific commands:

```bash
# /etc/sudoers.d/vps-manager
www-data ALL=(ALL) NOPASSWD: /usr/sbin/nginx -t
www-data ALL=(ALL) NOPASSWD: /bin/systemctl reload nginx
www-data ALL=(ALL) NOPASSWD: /bin/systemctl reload apache2
www-data ALL=(ALL) NOPASSWD: /usr/sbin/apache2ctl configtest
# Add other specific commands as needed
```

### 4. File Permissions
```bash
chmod 750 /opt/vps-manager
chown -R www-data:www-data /opt/vps-manager
```

### 5. SSL/TLS
Always use HTTPS in production:
```bash
sudo certbot --nginx -d manager.yourdomain.com
```

### 6. Input Validation
The application validates:
- Configuration syntax before applying
- Rollback on errors
- Command injection prevention

However, always review code before deployment.

## Reporting Security Issues

**Please do not open public issues for security vulnerabilities.**

Instead, email security concerns to: [your-email@example.com]

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work on a fix.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Security Best Practices for Users

1. ✅ Run behind a firewall
2. ✅ Use strong authentication
3. ✅ Keep Python and dependencies updated
4. ✅ Monitor access logs
5. ✅ Use HTTPS only
6. ✅ Regular security audits
7. ✅ Limit sudo permissions
8. ❌ Never expose port 5000 directly to internet
9. ❌ Don't run as root user
10. ❌ Don't use default configurations in production
