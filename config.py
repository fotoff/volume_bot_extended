# -*- coding: utf-8 -*-
"""
Extended Trading Bot v2 Configuration for X10 Starknet

This configuration file defines trading parameters for the "buy on rise" strategy.
Each trading pair has customized settings optimized for its volatility and market behavior.

Supported Trading Pairs:
    - BTC-USD: 0.3% rise trigger, SELL levels [0.3%, 0.6%, 0.9%]
    - ETH-USD: 0.4% rise trigger, SELL levels [0.4%, 0.8%, 1.2%]
    - SOL-USD: 0.5% rise trigger, SELL levels [0.5%, 1.0%, 1.5%]
    - OP-USD: 0.6% rise trigger, SELL levels [0.6%, 1.2%, 1.8%]
    - HYPE-USD: 0.3% rise trigger, SELL levels [0.2%, 0.4%, 0.6%]
    - DOGE-USD: 0.8% rise trigger, SELL levels [0.8%, 1.6%, 2.4%]

Strategy: Buy on Rise
- Bot tracks minimum price (anchor) for each pair
- Places BUY order when price rises by configured percentage
- Creates independent branch with 3 SELL orders and stop-loss
"""

# Минимальные размеры и множители для каждой пары
MIN_ORDER_SIZES = {
    "BTC-USD": 0.0001,   # 0.0001 BTC
    "ETH-USD": 0.01,     # 0.01 ETH
    "SOL-USD": 0.1,      # 0.1 SOL
    "OP-USD": 10.0,      # 10.0 OP
    "HYPE-USD": 0.1,     # 0.1 HYPE
    "DOGE-USD": 100.0    # 100.0 DOGE
}

MIN_ORDER_MULTIPLIERS = {
    "BTC-USD": 10,        # 0.0001 * 4 = 0.0004 BTC
    "ETH-USD": 6,        # 0.01 * 6 = 0.06 ETH
    "SOL-USD": 5,       # 0.1 * 10 = 1.0 SOL
    "OP-USD": 10,        # 10 * 10 = 100.0 OP
    "HYPE-USD": 10,      # 0.1 * 10 = 1.0 HYPE
    "DOGE-USD": 6        # 100.0 * 6 = 600.0 DOGE
}

# BUY_QTY = MIN_ORDER_SIZES × MIN_ORDER_MULTIPLIERS
BUY_QTY = {pair: MIN_ORDER_SIZES[pair] * MIN_ORDER_MULTIPLIERS[pair] for pair in MIN_ORDER_SIZES}

# Вычисление количества знаков после запятой по минимальному размеру
def _precision_from_min_order(size: float) -> int:
    s = str(size)
    if "." in s:
        return len(s.split(".")[1].rstrip("0"))
    return 0

SIZE_PRECISION = {pair: _precision_from_min_order(sz) for pair, sz in MIN_ORDER_SIZES.items()}

# Точности цены для каждой пары
PRICE_PRECISION = {
    "BTC-USD": 0,    # 1 (0 знаков после запятой)
    "ETH-USD": 2,    # 0.01 (2 знака после запятой)
    "SOL-USD": 1,    # 0.1 (1 знак после запятой)
    "OP-USD": 4,     # 0.0001 (4 знака после запятой)
    "HYPE-USD": 1,   # 0.1 (1 знак после запятой)
    "DOGE-USD": 5    # 0.00001 (5 знаков после запятой)
}

# Включенные рынки: временно только BTC
MARKETS = ["BTC-USD", "HYPE-USD"]

# Частота опроса (Tick)
TICK_SECONDS = 3

# Время жизни лимитного BUY ордера (сек.)
BUY_TTL_SECONDS = 300

# Время жизни SELL ордеров (30 дней в секундах)
# SELL ордера автоматически переразмещаются при истечении TTL
SELL_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 дней

# Индивидуальные шаги BUY6+ для каждой пары
BUY6_STEP_PCT = {
    "BTC-USD": 0.003,
    "ETH-USD": 0.004,
    "SOL-USD": 0.005,
    "OP-USD": 0.006,
    "HYPE-USD": 0.003,
    "DOGE-USD": 0.008,
}

# Индивидуальные SELL‑ступени для каждой пары (три значения для лесенки продаж)
SELL_STEPS_PCT = {
    "BTC-USD": [0.003, 0.006, 0.009],
    "ETH-USD": [0.004, 0.008, 0.012],
    "SOL-USD": [0.005, 0.010, 0.015],
    "OP-USD": [0.006, 0.012, 0.018],
    "HYPE-USD": [0.002, 0.004, 0.006],
    "DOGE-USD": [0.008, 0.016, 0.024],
}

# Распределение размера позиции между тремя SELL ордерами
SELL_SPLIT = [0.30, 0.30, 0.40]

# Минимальная прибыль (PnL защита): WAP +0.05%
# Если расчетная цена SELL ниже WAP, ордер выставляется по цене WAP +0.05%
PNL_MIN_PCT = 0.0005

# Стоп-лосс на ветку (−2%)
BRANCH_SL_PCT = -0.02

# Максимальное количество веток для пары (по умолчанию не ограничено)
# Если установлено значение > 0, бот не будет создавать новые ветки при достижении лимита
MAX_BRANCHES_PER_PAIR = 0  # 0 = не ограничено, > 0 = максимальное количество веток

# Список всех пар (для информации)
ALL_PAIRS = list(MIN_ORDER_SIZES.keys())

# Для обратной совместимости - оставляем старые переменные
# BUY6_STEP_PCT и SELL_STEPS_PCT теперь словари, но для BTC-USD значения те же
