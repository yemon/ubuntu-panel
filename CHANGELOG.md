# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-05

### Added
- Initial release
- System monitoring dashboard (hostname, OS, memory, disk, CPU, IP)
- Software installation management for 16+ packages
- Service management (start/stop/restart)
- Python package management via pip
- Domain and site management for Nginx and Apache
- Create new sites with form (PHP or Node.js)
- Git repository cloning during site creation
- Custom install commands support
- Let's Encrypt SSL automation
- Configuration file editor with syntax validation
- Enable/disable sites
- Delete sites with cleanup
- Automatic config rollback on errors
- Dark themed responsive UI
- Tabbed interface for better organization

### Security
- Added security warnings in documentation
- Included sudoers configuration examples
- Documented authentication recommendations

## [Unreleased]

### Added
- MySQL database backup and restore: dump selected databases (with sizes) into a backup and import them again, including in the import/restore flow
- MySQL restore snapshots each existing database first and rolls it back if the import fails
- Optional `MYSQL_USER`/`MYSQL_PASSWORD` in `.env`; falls back to root socket auth via sudo
- Server-to-server transfer via rsync over SSH: copy large websites, configs, and SSL certificates directly to another server (only changed data sent, resumable)
- Background transfer jobs with live progress log, connection test, dry-run, `--delete` mirror, key/password auth, and cancel
- Input validation (allowlist patterns) on rsync host/user/path/site parameters to prevent shell injection
- Automatic rollback on restore failure: each component is snapshotted before being overwritten and reverted to the previous working state if its step fails (web server config that fails its syntax test is never left applied)
- Verbose, per-step restore report in the UI (success / error / skipped) with clear explanations
- Clearer success and failure messages across install, service, backup, and import actions, surfacing the real underlying error instead of a generic failure
- Import / Restore: upload a backup `.tar.gz` and restore site configs, SSL certificates, and selected website files (for migrating to a new server)
- Import inspects the archive (source host, configs, certbot domains, website sizes) before restoring, with per-item selection
- Web server config is syntax-tested before reload during restore
- Import API endpoints: `/api/import/upload`, `/api/import/apply`, `/api/import/cancel`
- Session-based login page protecting all pages and API endpoints
- Credentials and session secret loaded from a `.env` file (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`)
- `.env.example` template and `/login` + `/logout` routes; logout button in the dashboard
- Backup & Export tab with full server backup support
- One-click download of all Nginx/Apache site configs as a single `.tar.gz`
- Every backup includes a `manifest.json` describing the server (web servers, sites, SSL, system info)
- Optional inclusion of Let's Encrypt / certbot SSL certificates
- Optional inclusion of website files from `/var/www`, with per-site selection and size display
- Saved backups list with download and delete actions
- Backup API endpoints: `/api/backup/info`, `/api/backup/configs`, `/api/backup/create`, `/api/backup/download/<file>`, `/api/backup/delete/<file>`

### Planned
- User authentication system
- Multi-user support with roles
- Database management interface
- Backup restore (re-apply an exported backup)
- Cron job management
- Log viewer
- Resource usage graphs
- Email notifications
- API key authentication
- Docker container management
