# Contributing to Enterprise Voice Control 🖖

Thank you for your interest in contributing to the Enterprise Voice Control project! We welcome contributions from developers, Star Trek fans, and smart home enthusiasts.

## 🌟 How to Contribute

### 🐛 Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Use the bug report template** when creating new issues
3. **Include system information**:
   - Raspberry Pi model and OS version
   - Python version
   - Node.js version
   - Hardware setup (microphone, speakers, etc.)
4. **Provide detailed steps to reproduce**
5. **Include relevant log files**:
   - `voice_system.log`
   - `control_center.log`
   - `audio_debug.log`

### 💡 Requesting Features

1. **Check existing feature requests** in the Issues tab
2. **Use the enhancement template**
3. **Describe the use case** and expected behavior
4. **Consider Star Trek theming** - how does it fit the Enterprise computer experience?
5. **Include mockups or examples** if applicable

### 🔧 Code Contributions

#### Getting Started

1. **Fork the repository**
2. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/enterprise-voice-control.git
   cd enterprise-voice-control
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

#### Development Setup

```bash
# Install Python dependencies
python3 -m venv pyatv_env
source pyatv_env/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install Node.js dependencies
npm install

# Install development tools
pip install black flake8 pytest
npm install -g prettier eslint
```

#### Code Standards

**Python Code:**
- Follow **PEP 8** style guidelines
- Use **Black** for code formatting: `black *.py`
- Use **type hints** where appropriate
- Add **docstrings** for functions and classes
- Maintain **Enterprise-D computer personality** in responses

**JavaScript/Node.js Code:**
- Use **ES6+ features** and modern JavaScript
- Follow **React Ink** best practices
- Use **Prettier** for formatting: `prettier --write *.js`
- Maintain **Star Trek UI theming**

**Example Python Function:**
```python
def activate_red_alert() -> bool:
    """
    Activates the red alert protocol with authentic TNG sounds and lighting.
    
    Returns:
        bool: True if red alert activated successfully, False otherwise.
    """
    try:
        # Implementation here
        return True
    except Exception as error:
        logger.error(f"Red alert activation failed: {error}")
        return False
```

#### Testing

**Python Tests:**
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_voice_control.py

# Run with coverage
python -m pytest --cov=. tests/
```

**Node.js Tests:**
```bash
# Run all tests
npm test

# Run specific test
npm test -- --grep "Enterprise Control"
```

#### Star Trek Theming Guidelines

When contributing to the Enterprise computer experience:

1. **Voice Responses:**
   - Use formal, precise language
   - Include Starfleet terminology when appropriate
   - Examples: "Acknowledged", "Working", "Please specify", "Confirmed"

2. **UI Elements:**
   - Use TNG-era color scheme (blue, amber, red)
   - Include appropriate Unicode symbols: 🚀 ⭐ 🖖 🔴
   - Maintain professional, technical aesthetic

3. **Audio Integration:**
   - Preserve authentic TNG computer sounds
   - Ensure red alert protocol matches show authenticity
   - Test audio timing and synchronization

#### Commit Guidelines

Use **conventional commits** format:

```
type(scope): description

feat(voice): add voice command macro system
fix(homekit): resolve Homebridge connection timeout
docs(readme): update installation instructions
style(ui): improve Enterprise control center styling
test(audio): add microphone detection tests
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### 📝 Documentation

- **Update README.md** for new features
- **Add inline comments** for complex logic
- **Include configuration examples**
- **Update troubleshooting guides**
- **Maintain Star Trek references** and terminology

### 🎯 Priority Areas

We're especially looking for contributions in:

1. **New MCP Server Integrations**
   - Additional Model Context Protocol servers
   - Custom enterprise-specific integrations

2. **HomeKit Device Support**
   - New device types and manufacturers
   - Advanced automation scenarios

3. **Audio Enhancements**
   - Additional TNG computer sounds
   - Voice synthesis improvements
   - Multi-room audio support

4. **Apple TV Features**
   - Enhanced app control
   - Content discovery improvements
   - Multi-device management

5. **Enterprise UI Improvements**
   - Additional Star Trek theming
   - Performance monitoring
   - Advanced diagnostics

### 🔍 Code Review Process

1. **All contributions require review**
2. **Automated tests must pass**
3. **Code must follow style guidelines**
4. **Documentation must be updated**
5. **Star Trek theming must be maintained**

### 📋 Pull Request Checklist

- [ ] **Code follows style guidelines**
- [ ] **All tests pass**
- [ ] **Documentation updated**
- [ ] **Star Trek theming maintained**
- [ ] **No hardcoded secrets or API keys**
- [ ] **Backward compatibility preserved**
- [ ] **Installation/setup tested**

### 🚀 Release Process

1. **Semantic Versioning** (MAJOR.MINOR.PATCH)
2. **Changelog maintenance**
3. **Release notes with Star Trek flair**
4. **Testing on multiple Pi configurations**

### 🤝 Community Guidelines

- **Be respectful** and inclusive
- **Help newcomers** get started
- **Share Star Trek enthusiasm** 🖖
- **Focus on constructive feedback**
- **Celebrate the Enterprise computer vision**

### 📧 Getting Help

- **GitHub Discussions** for questions and ideas
- **Issues** for bugs and feature requests
- **Wiki** for detailed documentation
- **Community Discord** (coming soon)

### 🖖 Recognition

Contributors will be recognized in:
- **README.md acknowledgments**
- **Release notes**
- **Special "Starfleet Engineering Corps" badge**

---

## 🌟 Special Thanks

This project exists because of the vision of Star Trek creators and the dedication of:
- **Open source community**
- **Star Trek fans worldwide**
- **Smart home enthusiasts**
- **Raspberry Pi developers**

*"The needs of the many outweigh the needs of the few."* - Spock

**Live long and prosper!** 🖖

---

*For technical questions, contact the maintainers or open a GitHub Discussion.*