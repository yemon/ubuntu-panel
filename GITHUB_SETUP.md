# GitHub Repository Setup Guide

Follow these steps to publish VPS Manager to GitHub:

## 1. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `vps-manager`
3. Description: `Modern web-based control panel for managing Ubuntu VPS servers`
4. Choose **Public**
5. **Do NOT** initialize with README, .gitignore, or license (we already have these)
6. Click **Create repository**

## 2. Initialize Local Repository

```bash
cd vps_manager

# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: VPS Manager v1.0.0"

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/vps-manager.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## 3. Configure Repository Settings

### Topics/Tags
Add these topics to help people find your project:
- `vps`
- `server-management`
- `flask`
- `nginx`
- `apache`
- `ubuntu`
- `devops`
- `control-panel`
- `web-interface`

### About Section
**Description**: Modern web-based control panel for managing Ubuntu VPS servers

**Website**: (your demo URL if you have one)

### Enable Features
- ✅ Issues
- ✅ Discussions (optional, for community)
- ✅ Wiki (optional)

## 4. Add Screenshots (Optional but Recommended)

Take screenshots of:
1. Dashboard view
2. Software management tab
3. Domain creation form
4. Site list with configs

Save them in the `screenshots/` folder and update README.md:

```markdown
## 📸 Screenshots

![Dashboard](screenshots/dashboard.png)
![Domain Management](screenshots/domains.png)
```

## 5. Create First Release

```bash
# Tag the release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

Then on GitHub:
1. Go to **Releases** → **Create a new release**
2. Choose tag: `v1.0.0`
3. Release title: `v1.0.0 - Initial Release`
4. Description: Copy from CHANGELOG.md
5. Click **Publish release**

## 6. Update README.md

Replace `yourusername` in README.md with your actual GitHub username:

```bash
# In README.md, replace:
https://github.com/yourusername/vps-manager
# with:
https://github.com/YOUR_ACTUAL_USERNAME/vps-manager
```

## 7. Optional: Add Badges

Add more badges to README.md:
```markdown
![GitHub stars](https://img.shields.io/github/stars/YOUR_USERNAME/vps-manager)
![GitHub forks](https://img.shields.io/github/forks/YOUR_USERNAME/vps-manager)
![GitHub issues](https://img.shields.io/github/issues/YOUR_USERNAME/vps-manager)
```

## 8. Share Your Project

- Post on Reddit: r/selfhosted, r/homelab
- Share on Twitter/X with hashtags: #VPS #DevOps #Flask
- Submit to awesome lists
- Add to your portfolio

## Repository Structure

Your final structure should look like:
```
vps-manager/
├── .gitignore
├── LICENSE
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
├── GITHUB_SETUP.md
├── requirements.txt
├── install.sh
├── app.py
├── templates/
│   └── index.html
└── screenshots/
    └── .gitkeep
```

## Need Help?

If you encounter any issues:
1. Check GitHub's documentation: https://docs.github.com
2. Open an issue in your repository
3. Ask in GitHub Discussions

Good luck with your project! 🚀
