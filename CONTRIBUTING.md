# Contributing to Extended Trading Bot v2

Thank you for your interest in contributing to Extended Trading Bot v2! This document provides guidelines for contributing to the project.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use the issue templates** when available
3. **Provide detailed information**:
   - Bot version and configuration
   - Steps to reproduce
   - Expected vs actual behavior
   - Log snippets (remove sensitive data)
   - Environment details (OS, Python version)

### Suggesting Features

1. **Check the roadmap** in Issues to see planned features
2. **Open a feature request** with:
   - Clear description of the feature
   - Use case and benefits
   - Possible implementation approach
   - Impact on existing functionality

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the coding standards
4. **Test thoroughly** with small amounts
5. **Commit with clear messages**: `git commit -m 'Add amazing feature'`
6. **Push to your fork**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

## 🔧 Development Setup

### Prerequisites

- Python 3.8+
- Git
- X10 Starknet testnet access (for testing)

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/extended-bot-v2.git
cd extended-bot-v2

# Create virtual environment
python3 -m venv bot-env
source bot-env/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Set up pre-commit hooks (if configured)
pre-commit install
```

### Testing Environment

```bash
# Copy environment template
cp env.example .env.test

# Configure with testnet credentials
# Edit .env.test with your test API keys

# Create test configuration
cp config.py config_test.py
# Modify config_test.py for small test amounts
```

## 📋 Coding Standards

### Python Style

- **PEP 8** compliance with line length up to 120 characters
- **Type hints** for function parameters and return values
- **Docstrings** for all public functions and classes
- **Descriptive variable names** (avoid single letters except for loop counters)

### Code Structure

```python
# Good example
async def place_limit_order(self, symbol: str, side: OrderSide, 
                           price: Decimal, size: Decimal, 
                           client_id: str) -> Optional[int]:
    """
    Place a limit order on the exchange.
    
    Args:
        symbol: Trading pair symbol (e.g., "BTC-USD")
        side: Order side (BUY or SELL)
        price: Order price
        size: Order size
        client_id: Unique client identifier
        
    Returns:
        Order ID if successful, None otherwise
    """
    try:
        # Implementation here
        return order_id
    except Exception as e:
        self.log(symbol, f"❌ Failed to place order: {e}")
        return None
```

### Configuration

- **All magic numbers** should be in `config.py`
- **Environment variables** for sensitive data
- **Clear documentation** for each configuration parameter

### Logging

- **Consistent emoji** usage for log categories
- **Structured logging** with symbol prefix
- **Appropriate log levels** (error, warning, info, debug)

```python
# Good logging examples
self.log(symbol, f"🟢 BUY placed {size}@{price}")
self.log(symbol, f"⚠️ Position mismatch: branches={x}, position={y}")
self.log(symbol, f"❌ API error: {error_message}")
```

## 🧪 Testing Guidelines

### Unit Tests

```python
# test_bot.py example
import unittest
from decimal import Decimal
from extended_bot_v2 import Bot

class TestBot(unittest.TestCase):
    def setUp(self):
        # Set up test bot with mock client
        pass
        
    def test_anchor_tracking(self):
        # Test anchor price tracking logic
        pass
        
    def test_branch_creation(self):
        # Test branch creation after buy fill
        pass
```

### Integration Tests

- **Use testnet** for live API testing
- **Small amounts** only (test configuration)
- **Cleanup** positions after tests
- **Document test scenarios**

### Manual Testing Checklist

Before submitting PR:

- [ ] Bot starts without errors
- [ ] Configuration loading works
- [ ] Price monitoring functions
- [ ] Buy order placement
- [ ] Branch creation
- [ ] Sell order placement
- [ ] Stop-loss functionality
- [ ] State persistence
- [ ] Service stop/restart

## 📝 Documentation

### Code Documentation

- **Docstrings** for all public methods
- **Inline comments** for complex logic
- **Type hints** for better IDE support

### README Updates

- Update **feature list** for new functionality
- Add **configuration examples** for new parameters
- Update **installation steps** if dependencies change

### API Documentation

- Document **new endpoints** or parameters
- Update **response structures** if changed
- Add **usage examples**

## 🚀 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Changelog

Update `CHANGELOG.md` with:
- **Added**: New features
- **Changed**: Modified functionality
- **Fixed**: Bug fixes
- **Removed**: Deprecated features

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version number incremented
- [ ] Tag created: `git tag v2.1.0`
- [ ] Release notes written

## 🔒 Security Guidelines

### Sensitive Data

- **Never commit** API keys or private keys
- **Use environment variables** for credentials
- **Sanitize logs** to remove sensitive information
- **Review code** for accidental data exposure

### Trading Safety

- **Test with small amounts** first
- **Validate all calculations** (especially money-related)
- **Include safeguards** against excessive trading
- **Document risk factors** clearly

## 🐛 Bug Fix Process

### Priority Levels

1. **Critical**: Security issues, data loss, trading errors
2. **High**: Major functionality broken
3. **Medium**: Minor features not working
4. **Low**: Cosmetic issues, documentation

### Fix Guidelines

- **Minimal changes** to fix the specific issue
- **Include tests** that verify the fix
- **Update documentation** if behavior changes
- **Consider edge cases** and similar issues

## 🏷️ Labeling System

### Pull Request Labels

- `feature`: New functionality
- `bugfix`: Bug fixes
- `documentation`: Documentation changes
- `refactor`: Code improvements without behavior change
- `breaking`: Breaking changes
- `security`: Security-related changes

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature request
- `documentation`: Documentation related
- `question`: Support request
- `duplicate`: Duplicate issue
- `wontfix`: Will not be implemented

## 🌟 Recognition

Contributors will be:
- **Listed** in the project contributors
- **Credited** in release notes for significant contributions
- **Thanked** in the community discussions

## 📞 Getting Help

- **GitHub Discussions**: For questions and general discussion
- **Issues**: For bug reports and feature requests
- **Documentation**: Check existing docs first
- **Code Review**: Ask for feedback on complex changes

## 🎯 Areas for Contribution

We especially welcome contributions in:

- **Testing**: More comprehensive test coverage
- **Documentation**: Better examples and guides
- **Performance**: Optimization of trading algorithms
- **Features**: New trading strategies or tools
- **Security**: Security audits and improvements
- **UI/Monitoring**: Better monitoring and alerting tools

---

**Thank you for contributing to Extended Trading Bot v2! 🚀**
