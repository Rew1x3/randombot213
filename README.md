# Telegram Raffle Bot (python-telegram-bot 20.x)

Бот для проведения розыгрышей с обязательной проверкой подписки на канал через `get_chat_member`, хранением данных в БД и плановым/ручным завершением.

## Возможности

- Диалог создания розыгрыша после нажатия кнопки «Создать розыгрыш».
- Участие через кнопку «Участвовать» (если сообщение видно) и через deep-link:
  - `/start join_<ID_розыгрыша>`
- Обязательная проверка подписки перед добавлением участника в БД.
- Публикация сообщения о розыгрыше в указанном канале/чате (с кнопкой «Участвовать»).
- Автоматическое подведение итогов по времени окончания.
- Админ-команда скрытого типа:
  - `/select_winner <ID_розыгрыша> <telegram_id_победителя_1>`
  - 1-е место фиксируется заранее, остальные места выбираются случайно.
- PostgreSQL поддержан через параметр `DATABASE_URL` (SQLAlchemy, async).

## Требования

- Python 3.10+ (рекомендуется 3.11/3.12)
- Для проверки подписки бот должен иметь возможность вызывать `getChatMember` для вашего канала.
  - Для приватных каналов бот должен быть участником канала (часто достаточно быть в канале; права зависят от политики Telegram).

## Установка зависимостей

### Локально (Windows / macOS / Linux)

1. Создайте виртуальное окружение:
   - `python -m venv venv`
   - `venv\Scripts\activate` (Windows) или `source venv/bin/activate` (Linux/macOS)
2. Установите зависимости:
   - `pip install -r requirements.txt`
3. Создайте `.env`:
   - `cp .env.example .env` (или скопируйте вручную) и заполните `BOT_TOKEN`, `ADMIN_ID`, `SUBSCRIPTION_CHANNEL_ID`.
4. Запустите бота:
   - `python main.py`

### Ubuntu VPS (systemd)

1. Установите Python и зависимости:
   - `sudo apt update`
   - `sudo apt install -y python3 python3-venv python3-pip build-essential`
2. Разместите проект на VPS, например:
   - `/home/ubuntu/randombot`
3. Создайте виртуальное окружение и установите зависимости:
   - `cd /home/ubuntu/randombot`
   - `python3 -m venv venv`
   - `./venv/bin/pip install -r requirements.txt`
4. Настройте окружение:
   - `cp .env.example .env` (SQLite) или `cp .env.prod.example .env` (PostgreSQL) и заполните параметры.
5. Создайте systemd unit:

```ini
# /etc/systemd/system/telegram-raffle-bot.service
[Unit]
Description=Telegram Raffle Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/randombot
EnvironmentFile=/home/ubuntu/randombot/.env
ExecStart=/home/ubuntu/randombot/venv/bin/python /home/ubuntu/randombot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

6. Включите и запустите:
   - `sudo systemctl daemon-reload`
   - `sudo systemctl enable --now telegram-raffle-bot`
7. Логи:
   - `sudo journalctl -u telegram-raffle-bot -f`

## Использование

1. Откройте бота в Telegram и (если вы администратор) нажмите кнопку «Создать розыгрыш».
2. Укажите:
   - описание/название,
   - список призов,
   - количество победителей,
   - ID канала/чата для проверки подписки (или Enter для значения из `.env`),
   - ID канала/чата, куда нужно опубликовать сообщение о розыгрыше (или Enter, чтобы использовать тот же ID),
   - условия (опционально),
   - дату/время окончания (UTC).
3. Перед завершением по deep-link `/start join_<ID_розыгрыша>` пользователи смогут добавить себя в список.

## Админская команда

Команда доступна только администратору из `.env` (`ADMIN_ID`) и предназначена только для приватного чата.

Пример:
- `/select_winner 1 123456789`

## Список активных розыгрышей

В приватном чате с ботом:
- `/active_giveaways`

## Примечания по БД и миграциям

- При старте бот автоматически создаёт таблицы (если их нет).
- Для SQLite файл создаётся по пути `SQLITE_PATH`.

## Создание таблиц в MySQL

1. Убедитесь, что БД доступна по адресу из `DATABASE_URL` в формате:
   - `mysql+aiomysql://user:pass@host:3306/dbname`
2. Поставьте переменные окружения:
   - `DB_TYPE=mysql`
3. Прогоните скрипт (один раз):
```powershell
python scripts/create_tables.py
```

## Поддержка нескольких .env

В коде используется `ENV_FILE` (по умолчанию `.env`), поэтому вы можете хранить:
- `.env` для локальной разработки,
- `.env.prod` (или `/.env.prod.example` -> `.env`) для VPS,
и при необходимости задавать `ENV_FILE=/path/to/.env.prod`.

