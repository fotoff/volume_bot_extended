# Информация о доступе к серверам и структуре файлов

## 🖥️ **Доступ к серверам**

### **Сервер 1 (Основной)**
- **IP:** 91.201.114.128
- **Пользователь:** root
- **SSH ключ:** `/Users/viktorbubnov/.ssh/bot_server_key`
- **Команда подключения:**
  ```bash
  ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128
  ```

### **Сервер 2 (Дополнительный)**
- **IP:** 212.118.54.61
- **Пользователь:** root
- **SSH ключ:** `/Users/viktorbubnov/.ssh/bot_server_key`
- **Команда подключения:**
  ```bash
  ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61
  ```

## 📁 **Структура файлов на серверах**

### **Сервер 1 (91.201.114.128)**
```
/root/
├── bot-deployment/
│   ├── extended-bot-v2.py          # Основной файл бота
│   ├── config.py                   # Конфигурация
│   ├── requirements.txt            # Зависимости Python
│   ├── .env                        # Переменные окружения (API ключи)
│   ├── bot-env/                    # Виртуальное окружение Python
│   │   ├── bin/
│   │   ├── lib/
│   │   └── ...
│   └── bot_state.json              # Состояние бота (создается автоматически)
├── .ssh/
│   ├── authorized_keys             # Разрешенные SSH ключи
│   └── ...
└── ...
```

**Системный сервис:**
- **Имя:** `extended-bot-rise.service`
- **Статус:** `systemctl status extended-bot-rise`
- **Запуск:** `systemctl start extended-bot-rise`
- **Остановка:** `systemctl stop extended-bot-rise`
- **Перезапуск:** `systemctl restart extended-bot-rise`

### **Сервер 2 (212.118.54.61)**
```
/home/botuser/
├── bot/                            # ОСНОВНОЙ РАБОЧИЙ БОТ (обновленный)
│   ├── extended-bot.py             # Основной файл бота (обновленная версия v2)
│   ├── config.py                   # Конфигурация
│   ├── requirements.txt            # Зависимости Python
│   ├── .env                        # Переменные окружения (API ключи)
│   ├── venv/                       # Виртуальное окружение Python
│   │   ├── bin/
│   │   ├── lib/
│   │   └── ...
│   ├── multi_bot.py                # Мульти-бот (старая версия)
│   ├── test_api.py                 # Тест API
│   ├── test_sdk.py                 # Тест SDK
│   ├── utils/                      # Утилиты
│   └── bot_state.json              # Состояние бота (создается автоматически)
├── bot4/                           # Тестовая версия бота
│   ├── extended-bot-v4.py          # Основной файл бота (обновленная версия v2)
│   ├── config.py                   # Конфигурация
│   ├── requirements.txt            # Зависимости Python
│   ├── .env                        # Переменные окружения (API ключи)
│   ├── bot-env/                    # Виртуальное окружение Python
│   │   ├── bin/
│   │   ├── lib/
│   │   └── ...
│   ├── backup_20250821_235017/     # Резервная копия от 21 августа
│   ├── __pycache__/                # Кэш Python
│   └── bot_state.json              # Состояние бота (создается автоматически)
├── bot2/                           # Версия бота 2 (архивная)
├── bot3/                           # Версия бота 3 (архивная)
└── .bashrc, .profile               # Настройки пользователя

/root/
├── .ssh/                           # SSH ключи root
├── bot2/                           # Дополнительная папка бота
├── .docker/                        # Настройки Docker
├── .pm2/                           # Настройки PM2
└── .npm/                           # Настройки Node.js
```

**Системные сервисы:**
- **`extended-bot-rise.service`** - для папки `/home/botuser/bot/` (ОСНОВНОЙ)
- **`extended-bot-v4.service`** - для папки `/home/botuser/bot4/` (ТЕСТОВЫЙ)

## 🎯 **АКТУАЛЬНАЯ ИНФОРМАЦИЯ О БОТАХ**

### **Сервер 1 (91.201.114.128):**
- **Рабочая папка:** `/root/bot-deployment/`
- **Файл бота:** `extended-bot-v2.py`
- **Сервис:** `extended-bot-rise.service`
- **Статус:** Основной рабочий бот

### **Сервер 2 (212.118.54.61):**
- **ОСНОВНОЙ рабочий бот:** `/home/botuser/bot/`
  - **Файл:** `extended-bot.py` (обновленная версия v2)
  - **Сервис:** `extended-bot-rise.service`
  - **Статус:** Основной рабочий бот на сервере 2
  
- **ТЕСТОВЫЙ бот:** `/home/botuser/bot4/`
  - **Файл:** `extended-bot-v4.py` (обновленная версия v2)
  - **Сервис:** `extended-bot-v4.service`
  - **Статус:** Тестовый бот для экспериментов

## 🔧 **Основные команды управления**

### **Проверка статуса бота**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "systemctl status extended-bot-rise"

# Сервер 2 - ОСНОВНОЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "systemctl status extended-bot-rise"

# Сервер 2 - ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "systemctl status extended-bot-v4"
```

### **Запуск бота**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "systemctl start extended-bot-rise"

# Сервер 2 - ОСНОВНОЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "systemctl start extended-bot-rise"

# Сервер 2 - ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "systemctl start extended-bot-v4"
```

### **Остановка бота**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "systemctl stop extended-bot-rise"

# Сервер 2 - ОСНОВНОЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "systemctl stop extended-bot-rise"

# Сервер 2 - ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "systemctl stop extended-bot-v4"
```

### **Просмотр логов бота**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "journalctl -u extended-bot-rise -f"

# Сервер 2 - ОСНОВНОЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "journalctl -u extended-bot-rise -f"

# Сервер 2 - ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "journalctl -u extended-bot-v4 -f"
```

### **Очистка состояния бота**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "cd /root/bot-deployment && rm -f bot_state.json"

# Сервер 2 - ОСНОВНОЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "cd /home/botuser/bot && rm -f bot_state.json"

# Сервер 2 - ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "cd /home/botuser/bot4 && rm -f bot_state.json"
```

## 📝 **Обновление кода на серверах**

### **Загрузка файла на сервер 1**
```bash
scp -i /Users/viktorbubnov/.ssh/bot_server_key extended-bot-v2-server.py root@91.201.114.128:/root/bot-deployment/extended-bot-v2.py
```

### **Загрузка файла на сервер 2 - ОСНОВНОЙ бот**
```bash
scp -i /Users/viktorbubnov/.ssh/bot_server_key extended-bot-v2-server.py root@212.118.54.61:/home/botuser/bot/extended-bot.py
```

### **Загрузка файла на сервер 2 - ТЕСТОВЫЙ бот**
```bash
scp -i /Users/viktorbubnov/.ssh/bot_server_key extended-bot-v2-server.py root@212.118.54.61:/home/botuser/bot4/extended-bot-v4.py
```

## 🚨 **Важные замечания**

1. **SSH ключ** должен иметь права 600: `chmod 600 /Users/viktorbubnov/.ssh/bot_server_key`
2. **Публичный ключ** уже добавлен на оба сервера
3. **Виртуальные окружения** уже настроены на серверах
4. **API ключи** хранятся в файлах `.env` на серверах
5. **Состояние бота** (`bot_state.json`) создается автоматически при первом запуске
6. **На сервере 2** ОСНОВНОЙ бот работает из папки `bot/`, ТЕСТОВЫЙ из `bot4/`
7. **Оба бота** используют обновленную логику v2 с исправлениями

## 📊 **Мониторинг и управление**

### **Проверка активных процессов**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "ps aux | grep extended-bot"

# Сервер 2 - ОСНОВНОЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "ps aux | grep extended-bot"

# Сервер 2 - ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "ps aux | grep extended-bot-v4"
```

### **Проверка использования ресурсов**
```bash
# Сервер 1
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@91.201.114.128 "htop"

# Сервер 2
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "htop"
```

### **Проверка структуры папок на сервере 2**
```bash
# Основные папки
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "ls -la /home/botuser/"

# ОСНОВНОЙ рабочий бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "ls -la /home/botuser/bot/"

# ТЕСТОВЫЙ бот
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "ls -la /home/botuser/bot4/"

# Папка root
ssh -i /Users/viktorbubnov/.ssh/bot_server_key root@212.118.54.61 "ls -la /root/"
```

---
*Документ создан: 25 августа 2025*
*Последнее обновление: 25 августа 2025 - Добавлена информация об основном рабочем боте на сервере 2*
