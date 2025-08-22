# API Documentation - Extended Trading Bot v2

This document describes the internal API structure and integration with X10 Starknet exchange.

## 🔌 X10 Starknet Integration

### Authentication

The bot uses X10's perpetual trading client with Starknet account integration:

```python
from x10.perpetual.accounts import StarkPerpetualAccount
from x10.perpetual.trading_client.trading_client import PerpetualTradingClient
from x10.perpetual.configuration import STARKNET_MAINNET_CONFIG

# Account setup
account = StarkPerpetualAccount(
    vault=VAULT_ID,
    private_key=STARK_PRIVATE_KEY,
    public_key=STARK_PUBLIC_KEY,
    api_key=API_KEY,
)

# Client initialization
client = PerpetualTradingClient(STARKNET_MAINNET_CONFIG, account)
```

### Required Credentials

| Variable | Description | Example |
|----------|-------------|---------|
| `EXTENDED_API_KEY` | X10 API key | `378dcfd1d96b30cb...` |
| `EXTENDED_PUBLIC_KEY` | Starknet public key | `0x3841a2763991cd6...` |
| `EXTENDED_STARK_PRIVATE` | Starknet private key | `0x4f0bdced431f495...` |
| `EXTENDED_VAULT_ID` | Vault identifier | `111983` |

## 📊 Market Data API

### Price Information

```python
async def stats(self, symbol: str):
    """Get market statistics for a symbol"""
    return await self.c.markets_info.get_market_statistics(market_name=symbol)

async def best_bid_ask(self, symbol: str):
    """Get best bid and ask prices"""
    st = await self.stats(symbol)
    bid = getattr(st.data, "bid_price", None) or getattr(st.data, "best_bid", None)
    ask = getattr(st.data, "ask_price", None) or getattr(st.data, "best_ask", None)
    return Decimal(str(bid)), Decimal(str(ask))

async def last_price(self, symbol: str) -> Decimal:
    """Get last traded price"""
    st = await self.stats(symbol)
    lp = getattr(st.data, "last_price", None) or getattr(st.data, "mark_price", None)
    return Decimal(str(lp))
```

### Market Statistics Response

```python
# Example response structure
{
    "data": {
        "last_price": "112593.0",
        "mark_price": "112590.5",
        "bid_price": "112592.0",
        "ask_price": "112594.0",
        "best_bid": "112592.0",
        "best_ask": "112594.0",
        "volume_24h": "1234567.89",
        "price_change_24h": "2.34",
        "high_24h": "113000.0",
        "low_24h": "111000.0"
    }
}
```

## 💰 Account API

### Position Management

```python
async def position(self, symbol: str):
    """Get current position for a symbol"""
    res = await self.c.account.get_positions(
        market_names=[symbol], 
        position_side=PositionSide.LONG
    )
    size = Decimal("0")
    wap = Decimal("0")
    for p in (res.data or []):
        sz = getattr(p, "size", Decimal(0))
        if sz and Decimal(str(sz)) > 0:
            size = Decimal(str(sz))
            wap = Decimal(str(getattr(p, "open_price", 0)))
            break
    return size, wap
```

### Position Response Structure

```python
# Example position data
{
    "data": [
        {
            "symbol": "BTC-USD",
            "size": "0.0004",
            "open_price": "112500.0",
            "mark_price": "112593.0",
            "unrealized_pnl": "0.037",
            "side": "LONG",
            "margin": "45.0"
        }
    ]
}
```

## 📋 Order Management API

### Order Placement

```python
async def place_limit(self, symbol: str, side: OrderSide, price: Decimal, 
                     size: Decimal, client_id: str, ttl_seconds: Optional[int] = None) -> Optional[int]:
    """Place a limit order"""
    expire_time = None
    if ttl_seconds:
        expire_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=ttl_seconds)
    
    resp = await self.c.place_order(
        market_name=symbol,
        amount_of_synthetic=size,
        price=price,
        side=side,
        time_in_force=TimeInForce.GTT,
        external_id=client_id,
        expire_time=expire_time,
    )
    return int(resp.data.id) if resp and getattr(resp, "data", None) else None

async def place_market_sell_ioc(self, symbol: str, size: Decimal, client_id: str):
    """Place a market sell order with IOC (Immediate or Cancel)"""
    last = await self.last_price(symbol)
    resp = await self.c.place_order(
        market_name=symbol,
        amount_of_synthetic=size,
        price=last,
        side=OrderSide.SELL,
        time_in_force=TimeInForce.IOC,
        external_id=client_id,
    )
    return int(resp.data.id) if resp and getattr(resp, "data", None) else None
```

### Order Cancellation

```python
async def cancel_order(self, order_id: int):
    """Cancel an order by ID"""
    await self.c.orders.cancel_order(order_id=order_id)
```

### Open Orders Query

```python
async def open_orders(self, symbol: str, side: Optional[OrderSide] = None):
    """Get open orders for a symbol"""
    kw = {"market_names": [symbol]}
    if side:
        kw["order_side"] = side
    res = await self.c.account.get_open_orders(**kw)
    return res.data or []
```

### Order Response Structure

```python
# Example order data
{
    "data": {
        "id": "12345678",
        "external_id": "BTC-USD:RISE:abc12345",
        "symbol": "BTC-USD",
        "side": "BUY",
        "type": "LIMIT",
        "qty": "0.0004",
        "price": "112500.0",
        "filled_qty": "0.0000",
        "status": "OPEN",
        "time_in_force": "GTT",
        "expire_time": "2025-01-22T14:30:00Z",
        "created_at": "2025-01-22T14:25:00Z"
    }
}
```

## 🏗️ Bot Internal API

### Core Classes

#### Branch Class

```python
@dataclass
class Branch:
    branch_id: int
    symbol: str
    buy_price: Decimal
    size: Decimal
    wap: Decimal
    stop_price: Decimal
    active: bool = True
    sells: Dict[str, SellLeg] = field(default_factory=dict)
    created_at: Optional[datetime.datetime] = None
    last_updated: Optional[datetime.datetime] = None
```

#### SellLeg Class

```python
@dataclass
class SellLeg:
    leg: str              # "L1", "L2", "L3"
    target_pct: Decimal   # Target profit percentage
    size: Decimal         # Order size
    order_id: Optional[int] = None
    client_id: Optional[str] = None
    price: Optional[Decimal] = None
```

### Bot State Management

#### State Persistence

```python
def _save_state(self):
    """Save bot state to JSON file"""
    data = {
        "branches": {},
        "next_branch_id": self.next_branch_id,
        "rise_anchor": {s: str(a) if a is not None else None for s, a in self.rise_anchor.items()},
    }
    # Serialize branches and sell legs
    # ...

def _load_state(self):
    """Load bot state from JSON file"""
    # Deserialize state data
    # Reconstruct branches and anchors
    # ...
```

#### State File Structure

```json
{
  "branches": {
    "BTC-USD": {
      "1": {
        "branch_id": 1,
        "symbol": "BTC-USD",
        "buy_price": "112500.0",
        "size": "0.0004",
        "wap": "112500.0",
        "stop_price": "112387.5",
        "active": true,
        "created_at": "2025-01-22T14:25:00+00:00",
        "last_updated": "2025-01-22T14:26:00+00:00",
        "sells": {
          "L1": {
            "leg": "L1",
            "target_pct": "0.003",
            "size": "0.00013",
            "order_id": 12345678,
            "client_id": "BTC-USD:BR1:S:L1:abc123",
            "price": "112837.5"
          }
        }
      }
    }
  },
  "next_branch_id": {
    "BTC-USD": 2,
    "HYPE-USD": 1
  },
  "rise_anchor": {
    "BTC-USD": "112400.0",
    "HYPE-USD": "41.850"
  }
}
```

## 🔧 Configuration API

### Market Configuration

```python
# config.py structure

MARKETS = ["BTC-USD", "HYPE-USD"]  # Active trading pairs

# Order sizes per pair
BUY_QTY = {
    "BTC-USD": 0.0004,
    "HYPE-USD": 1.0,
}

# Rise trigger percentages
BUY6_STEP_PCT = {
    "BTC-USD": 0.003,   # 0.3%
    "HYPE-USD": 0.003,  # 0.3%
}

# Sell profit levels (3 levels per pair)
SELL_STEPS_PCT = {
    "BTC-USD": [0.003, 0.006, 0.009],      # [0.3%, 0.6%, 0.9%]
    "HYPE-USD": [0.002, 0.004, 0.006],     # [0.2%, 0.4%, 0.6%]
}

# Stop-loss percentages
BRANCH_SL_PCT = -0.001  # -0.1%

# Size split for sell orders
SELL_SPLIT = [0.33, 0.33, 0.34]  # L1: 33%, L2: 33%, L3: 34%
```

### Precision Settings

```python
# Price precision (decimal places)
PRICE_PRECISION = {
    "BTC-USD": 0,     # Whole numbers
    "HYPE-USD": 1,    # 1 decimal place
}

# Size precision (decimal places)  
SIZE_PRECISION = {
    "BTC-USD": 4,     # 4 decimal places (0.0001)
    "HYPE-USD": 1,    # 1 decimal place (0.1)
}

# Minimum order sizes
MIN_ORDER_SIZES = {
    "BTC-USD": 0.0001,
    "HYPE-USD": 0.1,
}
```

## 🔍 Error Handling

### Common API Errors

```python
# Network errors
try:
    result = await api_call()
except aiohttp.ClientError as e:
    self.log(symbol, f"❌ Network error: {e}")

# API response errors
except Exception as e:
    self.log(symbol, f"❌ API error: {e}")

# Order placement errors
if not order_id:
    self.log(symbol, f"❌ Failed to place order")
```

### Rate Limiting

The bot includes built-in rate limiting:
- **Tick frequency**: 3 seconds between iterations
- **SELL checks**: Maximum once per 30 seconds
- **Order placement**: Respects exchange limits

## 📊 Monitoring API

### Log Categories

```python
# Price monitoring
self.log(symbol, f"📈 last={last} | pos={size} WAP={wap} | branches={active_cnt}")

# Order placement
self.log(symbol, f"🟢 BUY размещён {size}@{price}; anchor→{last}")

# Branch management
self.log(symbol, f"🆕 Ветка {b_id}: buy={price}, size={size}, SL={initial_stop}")

# Error conditions
self.log(symbol, f"⚠️ РАСХОЖДЕНИЕ: ветки={total_branches}, позиция={real_pos}")
```

### Health Check Endpoints

For external monitoring, you can query:

```bash
# Service status
systemctl is-active extended-bot-rise

# Log analysis
journalctl -u extended-bot-rise --since "1 hour ago" | grep -c "ERROR"

# State file validation
python -c "import json; print(json.load(open('bot_state.json'))['branches'])"
```

## 🔐 Security Considerations

### API Key Security

- **Scope**: Use trading-only API keys
- **Rotation**: Regular credential updates
- **Storage**: Secure `.env` file handling
- **Monitoring**: Log API usage patterns

### Order Security

- **Client IDs**: Unique identifiers prevent conflicts
- **Size validation**: Automatic size/precision checks
- **Stop-loss**: Mandatory loss protection
- **Position limits**: Configurable maximum exposure

---

**📚 For complete integration examples, see the main bot implementation in `extended-bot-v2.py`**
