# Quick Start Guide - Extended Trading Bot v2

Get your trading bot running in minutes with this step-by-step guide.

## 🚀 5-Minute Setup

### Step 1: Prerequisites

```bash
# Check Python version (3.8+ required)
python3 --version

# Install git if not available
sudo apt install git python3-pip python3-venv
```

### Step 2: Download and Setup

```bash
# Clone repository
git clone https://github.com/your-username/extended-bot-v2.git
cd extended-bot-v2

# Create virtual environment
python3 -m venv bot-env
source bot-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configuration

```bash
# Copy environment template
cp env.example .env

# Edit with your credentials
nano .env
```

**Required `.env` settings:**
```env
EXTENDED_API_KEY=your_x10_api_key_here
EXTENDED_PUBLIC_KEY=0x_your_starknet_public_key
EXTENDED_STARK_PRIVATE=0x_your_starknet_private_key
EXTENDED_VAULT_ID=your_vault_id_number
```

### Step 4: Test Configuration

```bash
# Validate configuration
python3 -c "from config import MARKETS; print(f'Active markets: {MARKETS}')"

# Test API connection (optional)
python3 -c "
import asyncio
from extended_bot_v2 import Bot
async def test():
    # Quick connection test
    pass
"
```

### Step 5: Run the Bot

**Local Testing:**
```bash
python3 extended-bot-v2.py
```

**Production Deployment:**
```bash
# Install as service
sudo cp extended-bot-rise.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable extended-bot-rise
sudo systemctl start extended-bot-rise

# Check status
sudo systemctl status extended-bot-rise
```

## 📊 First Trading Session

### Monitor Your Bot

```bash
# Real-time logs
journalctl -u extended-bot-rise -f

# Recent activity
journalctl -u extended-bot-rise --lines=50
```

### Expected Behavior

You should see logs like:
```
[BTC-USD] 📈 last=112593 | pos=0 WAP=0 | branches=0
[BTC-USD] 🎯 Устанавливаем якорь на минимум: 112587
[HYPE-USD] 🎯 Проверка роста: last=41.875, anchor=41.850, trigger=41.975
```

### First Purchase

When price rises by the configured percentage:
```
[BTC-USD] 🟢 BUY размещён 0.0004@112920; anchor→112920
[BTC-USD] 🆕 Ветка 1: buy=112920, size=0.0004, SL=112807
[BTC-USD] 🟠 SELL L1 ветки 1 0.00013@113258
```

## ⚙️ Basic Configuration

### Modify Trading Pairs

Edit `config.py`:
```python
# Enable/disable pairs
MARKETS = ["BTC-USD", "HYPE-USD"]  # Add or remove pairs

# Adjust position sizes
BUY_QTY = {
    "BTC-USD": 0.0004,   # Start small for testing
    "HYPE-USD": 1.0,
}
```

### Adjust Sensitivity

```python
# Rise trigger percentages
BUY6_STEP_PCT = {
    "BTC-USD": 0.003,    # 0.3% - less sensitive
    "HYPE-USD": 0.005,   # 0.5% - more selective
}
```

### Risk Management

```python
# Stop-loss percentage
BRANCH_SL_PCT = -0.001  # -0.1% stop-loss

# Profit targets
SELL_STEPS_PCT = {
    "BTC-USD": [0.003, 0.006, 0.009],  # Conservative
    "HYPE-USD": [0.005, 0.010, 0.015], # More aggressive
}
```

## 🔍 Monitoring Commands

### Service Management

```bash
# Status check
systemctl status extended-bot-rise

# Stop bot
systemctl stop extended-bot-rise

# Restart bot
systemctl restart extended-bot-rise
```

### Log Analysis

```bash
# Filter by action type
journalctl -u extended-bot-rise | grep "🟢 BUY"     # Buy orders
journalctl -u extended-bot-rise | grep "🆕 Ветка"   # New branches
journalctl -u extended-bot-rise | grep "🟠 SELL"    # Sell orders
journalctl -u extended-bot-rise | grep "🛑"         # Stop losses

# Recent errors
journalctl -u extended-bot-rise | grep -E "(ERROR|❌|⚠️)" | tail -10
```

### Position Check

```bash
# View bot state
cat bot_state.json | python3 -m json.tool

# Count active branches
python3 -c "
import json
state = json.load(open('bot_state.json', 'r'))
for symbol, branches in state['branches'].items():
    active = sum(1 for b in branches.values() if b['active'])
    print(f'{symbol}: {active} active branches')
"
```

## 🚨 Safety Checklist

### Before Starting

- [ ] **Small amounts**: Use minimal `BUY_QTY` for testing
- [ ] **Testnet first**: If available, test on testnet
- [ ] **API permissions**: Ensure trading permissions are correct
- [ ] **Balance check**: Verify sufficient balance for trading
- [ ] **Stop-loss set**: Confirm `BRANCH_SL_PCT` is configured

### During Operation

- [ ] **Monitor regularly**: Check logs every few hours
- [ ] **Watch positions**: Ensure no unexpected large positions
- [ ] **API limits**: Monitor for rate limiting issues
- [ ] **System resources**: Check CPU/memory usage

### Emergency Stop

```bash
# Immediate stop
sudo systemctl stop extended-bot-rise

# Check final positions
python3 check_status_async.py  # If available

# Manual position cleanup if needed
# (Use exchange interface to close positions)
```

## 🔧 Troubleshooting

### Bot Won't Start

```bash
# Check service logs
journalctl -u extended-bot-rise --lines=20

# Common issues:
# 1. Missing API credentials
# 2. Invalid configuration
# 3. Python dependencies
# 4. File permissions
```

### No Trading Activity

Check:
1. **Market volatility**: Prices need to move for triggers
2. **Trigger percentages**: May be too high for current conditions
3. **Balance**: Ensure sufficient funds
4. **API connectivity**: Network issues

### Positions Not Closing

```bash
# Check sell orders
journalctl -u extended-bot-rise | grep "🟠 SELL" | tail -5

# Verify branches are active
cat bot_state.json | grep -A 5 '"active": true'
```

## 📈 Performance Tips

### Optimization

1. **Tick frequency**: Adjust `TICK_SECONDS` in config
2. **Pair selection**: Start with 1-2 pairs, expand gradually
3. **Size management**: Scale `BUY_QTY` based on account size
4. **Trigger tuning**: Adjust `BUY6_STEP_PCT` based on market conditions

### Monitoring

Set up external monitoring:
```bash
# Create monitoring script
cat > monitor.sh << 'EOF'
#!/bin/bash
if ! systemctl is-active --quiet extended-bot-rise; then
    echo "Bot is down!" | mail -s "Trading Bot Alert" your@email.com
fi
EOF

# Add to crontab
crontab -e
# Add: */5 * * * * /path/to/monitor.sh
```

## 💡 Pro Tips

1. **Start conservative**: Use small amounts and low sensitivity
2. **Paper trade first**: Run without real money to understand behavior
3. **Regular updates**: Keep configuration tuned to market conditions
4. **Backup strategy**: Always have manual override capability
5. **Risk management**: Never risk more than you can afford to lose

## 📞 Getting Help

If you encounter issues:

1. **Check logs first**: `journalctl -u extended-bot-rise`
2. **Review configuration**: Validate all settings
3. **Restart bot**: Often resolves temporary issues
4. **GitHub Issues**: Report bugs with logs and configuration
5. **Community**: Join discussions for tips and strategies

---

**🎯 Ready to trade? Start with small amounts and monitor closely!**
