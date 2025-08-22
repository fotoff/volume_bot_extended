# ⚡ Быстрый старт - Extended Bot v2

## 🎯 Что нового в v2.1

### 🆕 TTL для SELL ордеров (30 дней)
- Автоматическое переразмещение SELL ордеров при истечении TTL
- Предотвращение "зависания" ордеров на бирже
- Автоматическое обновление цен при переразмещении

### 🛡️ Улучшенная PnL защита
- SELL ордера размещаются только выше WAP (Weighted Average Price)
- Защита от размещения ордеров в убыточной зоне
- Автоматическая проверка прибыльности перед размещением

### 🔄 Автоматическое переразмещение
- Функция `check_sell_ttls()` проверяет TTL каждые 3 секунды
- Интегрирована в основной цикл бота
- Логирование всех операций с TTL

## 🚀 Быстрый запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/fotoff/volume_bot_extended.git
cd volume_bot_extended
```

### 2. Установка зависимостей
```bash
python3 -m venv bot-env
source bot-env/bin/activate  # Linux/macOS
# или bot-env\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
```bash
cp env.example .env
nano .env  # Отредактируйте с вашими API ключами
```

**Содержимое .env:**
```env
EXTENDED_API_KEY=your_api_key_here
EXTENDED_PUBLIC_KEY=your_public_key_here
EXTENDED_STARK_PRIVATE=your_private_key_here
EXTENDED_VAULT_ID=your_vault_id_here
```

### 4. Запуск бота
```bash
python extended-bot-v2.py
```

## ⚙️ Быстрая конфигурация

### Основные настройки (`config.py`)
```python
# Включенные рынки
MARKETS = ["BTC-USD", "HYPE-USD"]

# Время жизни BUY ордеров (5 минут)
BUY_TTL_SECONDS = 300

# Время жизни SELL ордеров (30 дней)
SELL_TTL_SECONDS = 30 * 24 * 60 * 60

# Минимальная прибыль для размещения SELL
PNL_MIN_PCT = 0.0005  # +0.05% от WAP

# Стоп-лосс на ветку (-2%)
BRANCH_SL_PCT = -0.02
```

### Настройка торговых пар
```python
# Триггеры роста для каждой пары
BUY6_STEP_PCT = {
    "BTC-USD": 0.003,    # 0.3%
    "HYPE-USD": 0.003,   # 0.3%
}

# Уровни прибыли для SELL ордеров
SELL_STEPS_PCT = {
    "BTC-USD": [0.003, 0.006, 0.009],
    "HYPE-USD": [0.002, 0.004, 0.006],
}
```

## 🔧 Развертывание на сервере

### 1. Создание systemd сервиса
```bash
sudo nano /etc/systemd/system/extended-bot-rise.service
```

**Содержимое:**
```ini
[Unit]
Description=Extended Bot (Rise Strategy)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bot-deployment
Environment=PATH=/root/bot-deployment/bot-env/bin
ExecStart=/root/bot-deployment/bot-env/bin/python extended-bot-v2.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Активация сервиса
```bash
sudo systemctl daemon-reload
sudo systemctl enable extended-bot-rise
sudo systemctl start extended-bot-rise
```

### 3. Проверка статуса
```bash
sudo systemctl status extended-bot-rise
```

## 📊 Мониторинг

### Основные команды
```bash
# Статус бота
sudo systemctl status extended-bot-rise

# Просмотр логов
sudo journalctl -u extended-bot-rise -f
sudo journalctl -u extended-bot-rise --since '1 hour ago'
```

### Ключевые сообщения в логах
- `🎯 Устанавливаем якорь на минимум` - новый якорь цены
- `🟢 BUY размещён` - размещен BUY ордер
- `🆕 Ветка создана` - создана новая ветка
- `🟠 SELL размещен` - размещен SELL ордер с PnL защитой
- `⏰ TTL истек для SELL` - переразмещение по TTL
- `⚠️ Пропускаем SELL` - PnL защита сработала

## 🛠️ Устранение неполадок

### Частые проблемы

#### 1. Бот не запускается
```bash
# Проверить логи
sudo journalctl -u extended-bot-rise --since '5 minutes ago'

# Проверить права доступа
ls -la /root/bot-deployment/
```

#### 2. Ошибки API
```bash
# Проверить переменные окружения
cat /root/bot-deployment/.env

# Проверить подключение к интернету
curl -I https://api.x10.exchange
```

#### 3. Очистка состояния
```bash
# Очистить состояние бота (для свежего старта)
rm -f /root/bot-deployment/bot_state.json
sudo systemctl restart extended-bot-rise
```

## 🔄 Обновление

### 1. Остановка бота
```bash
sudo systemctl stop extended-bot-rise
```

### 2. Обновление файлов
```bash
# Загрузить новые файлы
scp config.py root@server:/root/bot-deployment/
scp extended-bot-v2.py root@server:/root/bot-deployment/
```

### 3. Запуск бота
```bash
sudo systemctl start extended-bot-rise
sudo systemctl status extended-bot-rise
```

## 📚 Дополнительная документация

- **Полное руководство**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Описание изменений**: [CHANGELOG.md](CHANGELOG.md)
- **Основная документация**: [README.md](README.md)

## 🚨 Важные замечания

- **Тестирование**: Всегда тестируйте на небольших суммах
- **Мониторинг**: Регулярно проверяйте логи и статус бота
- **Безопасность**: Храните API ключи в безопасном месте
- **Риски**: Торговля криптовалютами связана с высокими рисками

---

**⚡ Готово!** Ваш Extended Bot v2 с новыми функциями TTL и PnL защиты готов к работе!
