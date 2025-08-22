# Extended Trading Bot v2 - X10 Starknet

Advanced cryptocurrency trading bot for X10 exchange on Starknet network with multi-branch strategy and intelligent "buy on rise" algorithm.

## 🚀 Features

- **"Buy on Rise" Strategy**: Automatic order placement when price rises by a configured percentage
- **Multi-Branch System**: Each purchase creates an independent branch with its own SELL orders and stop-loss
- **Sell Ladder**: Automatic placement of 3 SELL orders at different profit levels
- **Adaptive Stop-Loss**: Loss protection for each individual branch
- **Multi-Pair Trading**: Support for trading multiple pairs simultaneously
- **State Persistence**: State preservation between restarts
- **Order Re-placement**: Automatic re-placement of unfilled orders closer to market
- **Position Tracking**: Real-time monitoring and mismatch detection
- **TTL Management**: Time-to-live handling for buy orders

## 📊 Supported Trading Pairs

| Pair | Rise Trigger | Sell Levels | Notes |
|------|-------------|-------------|--------|
| **BTC-USD** | 0.3% | [0.3%, 0.6%, 0.9%] | Primary pair |
| **ETH-USD** | 0.4% | [0.4%, 0.8%, 1.2%] | Major altcoin |
| **SOL-USD** | 0.5% | [0.5%, 1.0%, 1.5%] | High volatility |
| **OP-USD** | 0.6% | [0.6%, 1.2%, 1.8%] | Layer 2 token |
| **HYPE-USD** | 0.3% | [0.2%, 0.4%, 0.6%] | Optimized settings |
| **DOGE-USD** | 0.8% | [0.8%, 1.6%, 2.4%] | Meme coin |

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Price Monitor │───▶│  Anchor Tracker │───▶│  Buy Trigger    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Stop Loss     │◀───│  Branch Manager │◀───│  Order Placer   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  State Manager  │
                       └─────────────────┘
```

## 🔧 Installation

### Prerequisites

- Python 3.8+
- X10 Starknet API access
- Linux/macOS environment (recommended)

### Environment Setup

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/extended-bot-v2.git
cd extended-bot-v2
```

2. **Create virtual environment:**
```bash
python3 -m venv bot-env
source bot-env/bin/activate  # Linux/macOS
# or bot-env\Scripts\activate  # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp env.example .env
# Edit .env file with your API credentials
```

### Environment Variables

Create a `.env` file with the following variables:

```env
EXTENDED_API_KEY=your_api_key_here
EXTENDED_PUBLIC_KEY=your_public_key_here
EXTENDED_STARK_PRIVATE=your_private_key_here
EXTENDED_VAULT_ID=your_vault_id_here
BOT_STATE_FILE=bot_state.json
```

## ⚙️ Configuration

### Main Configuration (`config.py`)

Key parameters you can adjust:

- **`MARKETS`**: Active trading pairs
- **`BUY_QTY`**: Purchase size for each pair
- **`BUY6_STEP_PCT`**: Rise percentage trigger for purchases
- **`SELL_STEPS_PCT`**: Profit levels for sales
- **`BRANCH_SL_PCT`**: Stop-loss percentage for each branch
- **`BUY_TTL_SECONDS`**: Time-to-live for buy orders (default: 300s)

### Example Configuration

```python
MARKETS = ["BTC-USD", "HYPE-USD"]

BUY_QTY = {
    "BTC-USD": 0.0004,   # 0.0004 BTC per trade
    "HYPE-USD": 1.0,     # 1.0 HYPE per trade
}

BUY6_STEP_PCT = {
    "BTC-USD": 0.003,    # 0.3% rise trigger
    "HYPE-USD": 0.003,   # 0.3% rise trigger
}
```

## 🚀 Running the Bot

### Local Development

```bash
source bot-env/bin/activate
python extended-bot-v2.py
```

### Production Deployment (systemd)

1. **Create service file:**
```bash
sudo cp extended-bot-rise.service /etc/systemd/system/
sudo systemctl daemon-reload
```

2. **Enable and start service:**
```bash
sudo systemctl enable extended-bot-rise
sudo systemctl start extended-bot-rise
```

3. **Monitor status:**
```bash
systemctl status extended-bot-rise
journalctl -u extended-bot-rise -f
```

## 📈 Trading Strategy

### Buy Algorithm

1. **Anchor Tracking**: Bot tracks minimum price (anchor) for each pair
2. **Rise Detection**: When price rises by configured percentage from anchor
3. **Order Placement**: Places limit BUY order at current bid
4. **Branch Creation**: After fill, creates new independent branch

### Branch Management

Each branch operates independently with:
- **Unique ID**: Sequential numbering per symbol
- **Buy Price & Size**: Original purchase details
- **WAP (Weighted Average Price)**: For multiple fills
- **Stop-Loss**: Individual protection level
- **Sell Ladder**: 3 SELL orders at different profit levels

### Order Management

- **TTL Protection**: Buy orders auto-replaced if expired
- **Partial Fill Handling**: Remaining size re-placed closer to market
- **Deduplication**: Prevents multiple SELL orders per leg
- **Position Reconciliation**: Automatic mismatch detection and logging

## 🔍 Monitoring & Logging

### Log Categories

| Icon | Type | Description |
|------|------|-------------|
| 📈 | Price | Price monitoring and anchor updates |
| 🟢 | Buy | Buy order placement |
| 🆕 | Branch | New branch creation |
| 🟠 | Sell | Sell order placement |
| 🛑 | Stop-Loss | Stop-loss execution |
| ⚠️ | Warning | Position mismatches |
| 🔄 | State | Branch state changes |

### Example Log Output

```
[BTC-USD] 📈 last=112593 | pos=0 WAP=0 | branches=0
[BTC-USD] 🎯 Устанавливаем якорь на минимум: 112587
[HYPE-USD] 🟢 BUY размещён 1.0@41.9; anchor→41.888
[HYPE-USD] 🆕 Ветка 1: buy=41.9, size=1.00, SL=41.1
[HYPE-USD] 🟠 SELL L1 ветки 1 0.3@42.0
```

### State Management

The bot maintains persistent state in `bot_state.json`:
- Branch information and timestamps
- Anchor prices for each symbol
- Next branch ID counters

## 🔧 Management Commands

### Service Control

```bash
# Status check
systemctl status extended-bot-rise

# View logs
journalctl -u extended-bot-rise -f
journalctl -u extended-bot-rise --lines=50

# Control service
systemctl start extended-bot-rise
systemctl stop extended-bot-rise
systemctl restart extended-bot-rise
```

### Manual Operations

```bash
# Clear state (fresh start)
rm bot_state.json

# Check configuration
python -c "from config import *; print(f'Markets: {MARKETS}')"

# Validate environment
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API Key:', os.getenv('EXTENDED_API_KEY')[:10] + '...')"
```

## 🔧 Troubleshooting

### Common Issues

1. **Position Mismatch**
   - Symptom: `⚠️ РАСХОЖДЕНИЕ: ветки=X, позиция=Y`
   - Cause: State reset while position exists
   - Solution: Bot auto-detects and logs, consider manual position management

2. **Orders Not Placed**
   - Check: Real position > 0 and active branches exist
   - Verify: API credentials and permissions
   - Monitor: 30-second SELL check intervals

3. **TTL Expiration**
   - Symptom: `🔁 Переразмещаем BUY ближе к рынку`
   - Normal: Automatic re-placement closer to bid
   - Monitor: Ensure eventual fill

### Performance Optimization

- **Tick Frequency**: Adjust `TICK_SECONDS` for responsiveness vs. API limits
- **TTL Duration**: Balance `BUY_TTL_SECONDS` for market conditions
- **Position Sizing**: Configure appropriate `BUY_QTY` for account size

## 🔒 Security Considerations

- **API Keys**: Store securely in `.env` file, never commit to repository
- **Permissions**: Use trading-only API keys when possible
- **Monitoring**: Regular checks on bot behavior and positions
- **Risk Management**: Set appropriate position sizes and stop-losses

## ⚠️ Risk Disclaimer

- **High Risk**: Cryptocurrency trading involves substantial risk of loss
- **Automated Trading**: Bot decisions may not align with market conditions
- **Testing**: Always test with small amounts first
- **Monitoring**: Regular supervision recommended
- **No Guarantees**: Past performance does not guarantee future results

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

This project is for educational purposes only. Use at your own risk.

## 📞 Support

- **Issues**: Create GitHub Issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Check `docs/` folder for detailed guides

---

**⚡ Built with Python • 🚀 Powered by Starknet • 📈 Optimized for X10**