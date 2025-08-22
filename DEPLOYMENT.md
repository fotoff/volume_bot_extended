# 🚀 Руководство по развертыванию Extended Bot v2

## 📋 Обзор

**Extended Bot v2** - это продвинутый криптовалютный торговый бот с автоматической защитой прибыли (PnL) и управлением временем жизни ордеров (TTL). Данное руководство описывает процесс развертывания бота на Linux сервере.

## 🎯 Новые возможности v2.1

### TTL для SELL ордеров (30 дней)
- Автоматическое переразмещение SELL ордеров при истечении TTL
- Предотвращение "зависания" ордеров на бирже
- Автоматическое обновление цен при переразмещении

### Улучшенная PnL защита
- SELL ордера размещаются только выше WAP (Weighted Average Price)
- Защита от размещения ордеров в убыточной зоне
- Автоматическая проверка прибыльности перед размещением

### Автоматическое переразмещение
- Функция `check_sell_ttls()` проверяет TTL каждые 3 секунды
- Интегрирована в основной цикл бота
- Логирование всех операций с TTL

## 🖥️ Системные требования

### Минимальные требования
- **ОС**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 2 GB
- **CPU**: 2 ядра
- **Диск**: 10 GB свободного места
- **Python**: 3.8+

### Рекомендуемые требования
- **ОС**: Ubuntu 22.04 LTS
- **RAM**: 4 GB
- **CPU**: 4 ядра
- **Диск**: 20 GB SSD
- **Python**: 3.9+

## 🔧 Подготовка сервера

### 1. Обновление системы
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. Установка Python и зависимостей
```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv git curl

# CentOS/RHEL
sudo yum install -y python3 python3-pip git curl
```

### 3. Создание пользователя для бота
```bash
sudo useradd -m -s /bin/bash botuser
sudo usermod -aG sudo botuser
sudo passwd botuser
```

## 📥 Установка бота

### 1. Клонирование репозитория
```bash
cd /home/botuser
git clone https://github.com/fotoff/volume_bot_extended.git
cd volume_bot_extended
```

### 2. Создание виртуального окружения
```bash
python3 -m venv bot-env
source bot-env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Настройка переменных окружения
```bash
cp env.example .env
nano .env
```

**Содержимое .env файла:**
```env
EXTENDED_API_KEY=your_api_key_here
EXTENDED_PUBLIC_KEY=your_public_key_here
EXTENDED_STARK_PRIVATE=your_private_key_here
EXTENDED_VAULT_ID=your_vault_id_here
```

## ⚙️ Конфигурация

### 1. Основные настройки (`config.py`)
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

### 2. Настройка торговых пар
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

## 🚀 Развертывание через systemd

### 1. Создание service файла
```bash
sudo nano /etc/systemd/system/extended-bot-rise.service
```

**Содержимое файла:**
```ini
[Unit]
Description=Extended Bot (Rise Strategy)
After=network.target
Wants=network.target

[Service]
Type=simple
User=botuser
Group=botuser
WorkingDirectory=/home/botuser/volume_bot_extended
Environment=PATH=/home/botuser/volume_bot_extended/bot-env/bin
ExecStart=/home/botuser/volume_bot_extended/bot-env/bin/python extended-bot-v2.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

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

## 📊 Мониторинг и управление

### Основные команды
```bash
# Статус бота
sudo systemctl status extended-bot-rise

# Запуск/остановка
sudo systemctl start extended-bot-rise
sudo systemctl stop extended-bot-rise
sudo systemctl restart extended-bot-rise

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

## 🔄 Обновление бота

### 1. Остановка бота
```bash
sudo systemctl stop extended-bot-rise
```

### 2. Обновление файлов
```bash
cd /home/botuser/volume_bot_extended
git pull origin main
```

### 3. Обновление зависимостей (если нужно)
```bash
source bot-env/bin/activate
pip install -r requirements.txt
```

### 4. Запуск бота
```bash
sudo systemctl start extended-bot-rise
sudo systemctl status extended-bot-rise
```

## 🛠️ Устранение неполадок

### Частые проблемы

#### 1. Бот не запускается
```bash
# Проверить логи
sudo journalctl -u extended-bot-rise --since '5 minutes ago'

# Проверить права доступа
ls -la /home/botuser/volume_bot_extended/
sudo chown -R botuser:botuser /home/botuser/volume_bot_extended/
```

#### 2. Ошибки API
```bash
# Проверить переменные окружения
sudo -u botuser cat /home/botuser/volume_bot_extended/.env

# Проверить подключение к интернету
curl -I https://api.x10.exchange
```

#### 3. Проблемы с памятью
```bash
# Проверить использование памяти
free -h
ps aux | grep python

# Перезапустить бота
sudo systemctl restart extended-bot-rise
```

### Очистка состояния
```bash
# Очистить состояние бота (для свежего старта)
sudo -u botuser rm -f /home/botuser/volume_bot_extended/bot_state.json
sudo systemctl restart extended-bot-rise
```

## 🔒 Безопасность

### 1. Firewall
```bash
# Открыть только необходимые порты
sudo ufw allow ssh
sudo ufw enable
```

### 2. Обновления безопасности
```bash
# Автоматические обновления безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Мониторинг доступа
```bash
# Просмотр попыток входа
sudo journalctl -u ssh | grep "Failed password"
```

## 📈 Производительность

### Оптимизация
- **Частота тиков**: Настройте `TICK_SECONDS` в config.py
- **Размер позиций**: Адаптируйте `BUY_QTY` под размер аккаунта
- **TTL настройки**: Оптимизируйте под рыночные условия

### Мониторинг ресурсов
```bash
# Мониторинг CPU и памяти
htop
iotop

# Мониторинг диска
df -h
du -sh /home/botuser/volume_bot_extended/
```

## 📞 Поддержка

### Полезные команды для диагностики
```bash
# Полная информация о системе
sudo systemctl status extended-bot-rise --full

# Логи с деталями
sudo journalctl -u extended-bot-rise --since '1 hour ago' --no-pager

# Проверка конфигурации
sudo -u botuser python3 -c "from config import *; print(f'Markets: {MARKETS}')"
```

### Контакты
- **GitHub Issues**: [volume_bot_extended](https://github.com/fotoff/volume_bot_extended/issues)
- **Документация**: [README.md](README.md)
- **Журнал изменений**: [CHANGELOG.md](CHANGELOG.md)

---

**⚠️ Важно**: Всегда тестируйте изменения на тестовой среде перед применением в продакшене.
