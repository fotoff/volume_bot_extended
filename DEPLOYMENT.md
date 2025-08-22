# Deployment Guide - Extended Trading Bot v2

This guide covers deployment of the Extended Trading Bot v2 to production servers.

## 🚀 Quick Deployment

### Server Requirements

- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Python**: 3.8+
- **Memory**: 512MB RAM minimum
- **Storage**: 1GB free space
- **Network**: Stable internet connection

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and required packages
sudo apt install python3 python3-pip python3-venv git systemd -y

# Create deployment directory
sudo mkdir -p /root/bot-deployment
cd /root/bot-deployment
```

### 2. Deploy Bot Files

**Option A: Direct Upload**
```bash
# From local machine
scp -i ~/.ssh/bot_server_key extended-bot-v2.py root@YOUR_SERVER:/root/bot-deployment/
scp -i ~/.ssh/bot_server_key config.py root@YOUR_SERVER:/root/bot-deployment/
scp -i ~/.ssh/bot_server_key requirements.txt root@YOUR_SERVER:/root/bot-deployment/
scp -i ~/.ssh/bot_server_key .env root@YOUR_SERVER:/root/bot-deployment/
```

**Option B: Git Clone**
```bash
# On server
cd /root/bot-deployment
git clone https://github.com/your-username/extended-bot-v2.git .
```

### 3. Environment Setup

```bash
# Create virtual environment
python3 -m venv bot-env
source bot-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
nano .env  # Edit with your API credentials
```

### 4. Service Configuration

```bash
# Copy service file
sudo cp extended-bot-rise.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable extended-bot-rise

# Start the bot
sudo systemctl start extended-bot-rise

# Check status
sudo systemctl status extended-bot-rise
```

## ⚙️ Environment Configuration

### Required Environment Variables

Create `/root/bot-deployment/.env`:

```env
# X10 Starknet API Credentials
EXTENDED_API_KEY=your_api_key_here
EXTENDED_PUBLIC_KEY=0x_your_public_key_here
EXTENDED_STARK_PRIVATE=0x_your_private_key_here
EXTENDED_VAULT_ID=your_vault_id_here

# Bot Configuration
BOT_STATE_FILE=bot_state.json
```

### Security Notes

- **Never commit `.env` files to version control**
- **Use read-only API keys when possible**
- **Regularly rotate API credentials**
- **Monitor API usage and rate limits**

## 🔧 Service Management

### Systemd Service (`extended-bot-rise.service`)

```ini
[Unit]
Description=Extended Bot (Rise Strategy)
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bot-deployment
Environment=PATH=/root/bot-deployment/bot-env/bin
ExecStart=/root/bot-deployment/bot-env/bin/python /root/bot-deployment/extended-bot-v2.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Management Commands

```bash
# Service control
sudo systemctl start extended-bot-rise
sudo systemctl stop extended-bot-rise
sudo systemctl restart extended-bot-rise
sudo systemctl status extended-bot-rise

# Log monitoring
journalctl -u extended-bot-rise -f
journalctl -u extended-bot-rise --lines=100
journalctl -u extended-bot-rise --since "1 hour ago"

# Service information
systemctl is-active extended-bot-rise
systemctl is-enabled extended-bot-rise
```

## 📊 Monitoring & Maintenance

### Health Checks

**1. Service Status Check**
```bash
#!/bin/bash
# health_check.sh
if systemctl is-active --quiet extended-bot-rise; then
    echo "✅ Bot is running"
else
    echo "❌ Bot is not running"
    exit 1
fi
```

**2. Position Validation**
```bash
# Check bot state
cat /root/bot-deployment/bot_state.json | jq '.'

# Manual position check
cd /root/bot-deployment
source bot-env/bin/activate
python check_status_async.py
```

### Log Analysis

**Monitor key events:**
```bash
# Buy orders
journalctl -u extended-bot-rise | grep "🟢 BUY"

# Branch creation
journalctl -u extended-bot-rise | grep "🆕 Ветка"

# Sell orders
journalctl -u extended-bot-rise | grep "🟠 SELL"

# Errors and warnings
journalctl -u extended-bot-rise | grep -E "(ERROR|WARNING|❌|⚠️)"
```

### Performance Monitoring

**Resource Usage:**
```bash
# Memory usage
ps aux | grep "extended-bot-v2.py"

# System resources
htop
free -h
df -h
```

## 🔄 Update Procedures

### Safe Update Process

1. **Stop the bot:**
```bash
sudo systemctl stop extended-bot-rise
```

2. **Backup current state:**
```bash
cp bot_state.json bot_state.json.backup.$(date +%Y%m%d_%H%M%S)
```

3. **Update files:**
```bash
# Upload new files or git pull
git pull  # if using git
# or
scp -i ~/.ssh/bot_server_key extended-bot-v2.py root@YOUR_SERVER:/root/bot-deployment/
```

4. **Update dependencies (if needed):**
```bash
source bot-env/bin/activate
pip install -r requirements.txt
```

5. **Restart the bot:**
```bash
sudo systemctl start extended-bot-rise
```

6. **Verify operation:**
```bash
sudo systemctl status extended-bot-rise
journalctl -u extended-bot-rise --lines=20
```

### Rollback Procedure

If issues occur after update:

```bash
# Stop current version
sudo systemctl stop extended-bot-rise

# Restore backup files
cp extended-bot-v2.py.backup extended-bot-v2.py
cp bot_state.json.backup.TIMESTAMP bot_state.json

# Restart with previous version
sudo systemctl start extended-bot-rise
```

## 🔐 Security Best Practices

### Server Security

1. **SSH Security:**
```bash
# Disable password authentication
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart ssh
```

2. **Firewall Configuration:**
```bash
# Allow only necessary ports
sudo ufw allow ssh
sudo ufw enable
```

3. **Regular Updates:**
```bash
# Schedule automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Bot Security

- **API Key Permissions**: Use trading-only keys
- **Position Limits**: Set reasonable `BUY_QTY` values
- **Stop-Loss Settings**: Ensure `BRANCH_SL_PCT` is properly configured
- **Monitoring**: Set up alerts for unusual activity

## 🚨 Troubleshooting

### Common Issues

**1. Bot Won't Start**
```bash
# Check service logs
journalctl -u extended-bot-rise --lines=50

# Common causes:
# - Missing dependencies
# - Invalid API credentials
# - Permission issues
# - Configuration errors
```

**2. Position Mismatches**
```bash
# Check for warnings
journalctl -u extended-bot-rise | grep "РАСХОЖДЕНИЕ"

# Validate state file
cat bot_state.json | jq '.branches'
```

**3. Orders Not Placing**
```bash
# Check API connectivity
# Check account balance
# Verify market is active
# Check order size requirements
```

### Emergency Procedures

**Stop All Trading:**
```bash
sudo systemctl stop extended-bot-rise
# Manually close positions if needed
```

**Clear State (Fresh Start):**
```bash
sudo systemctl stop extended-bot-rise
rm bot_state.json
sudo systemctl start extended-bot-rise
```

## 📞 Support

For deployment issues:
1. Check logs: `journalctl -u extended-bot-rise`
2. Verify configuration: `cat .env` and `python -c "from config import *"`
3. Test connectivity: API endpoints reachable
4. Create GitHub issue with logs and configuration details

---

**⚠️ Always test deployments on small amounts before full production use.**
