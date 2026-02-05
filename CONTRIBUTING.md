# Contributing to VPS Manager

Thank you for considering contributing to VPS Manager! This document provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS version, Python version, etc.)

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature has already been requested
- Clearly describe the feature and its use case
- Explain why it would be useful to most users

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes**:
   - Follow the existing code style
   - Add comments for complex logic
   - Keep functions focused and modular
3. **Test your changes** on a test VPS
4. **Update documentation** if needed
5. **Commit with clear messages**:
   ```
   Add feature: domain wildcard support
   Fix: nginx config validation error
   ```
6. **Submit the pull request**

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Keep lines under 100 characters when possible

### Testing

Before submitting:
- Test on Ubuntu 23.04 LTS
- Verify all API endpoints work
- Check both Nginx and Apache functionality
- Test error handling and rollback scenarios

## Development Setup

```bash
git clone https://github.com/yourusername/vps-manager.git
cd vps-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Questions?

Feel free to open an issue for any questions about contributing!
