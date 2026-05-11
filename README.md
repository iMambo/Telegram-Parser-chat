# Telegram-Parser-chat
Telegram Industrial Parser — мощный инструмент для сбора данных из Telegram-групп. Парсер автоматически собирает сообщения, медиафайлы и профили пользователей, сохраняя всё в базу данных SQLite (или PostgreSQL). Встроенная веб-панель позволяет управлять парсером и просматривать собранные данные через браузер.

https://img.shields.io/badge/Python-3.10%2B-blue
https://img.shields.io/badge/License-MIT-green
https://img.shields.io/badge/Termux-Supported-brightgreen

Документация Telegram Industrial Parser v1.02.01

📌 Содержание

1. Обзор
2. Требования
3. Файлы проекта
4. Установка
5. Конфигурация
6. Подготовка аккаунтов
7. Запуск
8. Веб-панель управления
9. Добавление групп
10. Просмотр данных
11. Решение проблем
12. Структура базы данных

---

Обзор

Telegram Industrial Parser — мощный инструмент для сбора данных из Telegram-групп. Парсер автоматически собирает сообщения, медиафайлы и профили пользователей, сохраняя всё в базу данных SQLite (или PostgreSQL). Встроенная веб-панель позволяет управлять парсером и просматривать собранные данные через браузер.

Ключевые возможности:

· Мультиаккаунтинг с ротацией при FloodWait
· Сбор сообщений всех типов (текст, фото, видео, голосовые, документы, стикеры)
· Сбор полных профилей пользователей (username, имя, фамилия, телефон, био, аватар)
· Автоматический сбор уникальных пользователей из сообщений
· Вступление в закрытые группы по инвайт-ссылкам
· Сохранение медиафайлов в структурированную файловую систему
· Чекпойнтинг — продолжение с того же места при перезапуске
· Веб-панель управления с просмотром чатов
· Логирование всех действий

---

Требования

· Python 3.10+
· Termux (Android) или обычный Linux/Windows
· Установленные библиотеки:
  ```
  pip install telethon aiohttp sqlalchemy aiosqlite Pillow
  ```
· Клонирование

```bash
git clone https://github.com/your-username/telegram-industrial-parser.git
cd telegram-industrial-parser
```

· Аккаунты Telegram (можно получить api_id и api_hash на my.telegram.org)

---

Файлы проекта

```markdown
|Файл | Описание|
|-------------|-------------|-------------|
|ps.py | Основной скрипт парсера |
|-------------|-------------|-------------|
|dashboard.html | Веб-панель управления |
|-------------|-------------|-------------|
|config.json | Конфигурация парсера |
|-------------|-------------|-------------|
|sessions/ | Хранилище аккаунтов для парсинга |
|-------------|-------------|-------------|
|groups.txt | Список групп для парсинга |
|-------------|-------------|-------------|
|invites.txt | Инвайт-ссылки для закрытых групп |
|-------------|-------------|-------------|
|parser.db | База данных SQLite |
|-------------|-------------|-------------|
|parser.log | Файл логов |
|-------------|-------------|-------------|
|status.json | Текущий статус для веб-панели |
```

---

Установка

Termux (Android)

```bash
# Обновляем пакеты
pkg update && pkg upgrade

# Устанавливаем Python
pkg install python

# Устанавливаем зависимости
pip install telethon sqlalchemy aiosqlite Pillow

# Создаём папку проекта
mkdir ~/telegram-parser
cd ~/telegram-parser

# Копируем файлы парсера в эту папку
# (ps.py и dashboard.html должны быть здесь)
```

Linux/Windows

```bash
# Создаём виртуальное окружение (рекомендуется)
python -m venv venv
source venv/bin/activate  # Linux
# или
venv\Scripts\activate     # Windows

# Устанавливаем зависимости
pip install telethon sqlalchemy aiosqlite Pillow

# Копируем файлы в папку проекта
```

---

Конфигурация

При первом запуске парсер автоматически создаст config.json с настройками по умолчанию. Отредактируй его:

```json
{
    "api_id": 1234567,           // Твой api_id с my.telegram.org
    "api_hash": "abc123def456",  // Твой api_hash с my.telegram.org
    "accounts_folder": "sessions",
    "db_type": "sqlite",
    "sqlite_path": "parser.db",
    "batch_size": 100,           // Сколько сообщений за раз
    "media_dir": "media",        // Папка для медиафайлов
    "users_dir": "users",        // Папка для JSON-профилей
    "log_file": "parser.log",
    "max_workers": 5,            // Количество воркеров
    "request_delay": 0.3,        // Задержка между запросами
    "max_participants": 10000,
    "enable_user_json": true,    // Сохранять JSON-файлы пользователей
    "api_port": 8081             // Порт веб-панели
}
```

---

Подготовка аккаунтов

Способ 1: Через веб-панель

1. Запусти парсер: python ps.py
2. Открой веб-панель: http://localhost:8081
3. Во вкладке "Панель управления" → "Сессии"
4. Выбери .session файл и нажми "⬆️ Загрузить сессию"

Способ 2: Ручное создание

```python
# Создай файл create_session.py
from telethon import TelegramClient
import asyncio

async def main():
    api_id = 1234567    # Твой api_id
    api_hash = "abc123" # Твой api_hash

    client = TelegramClient("sessions/my_account", api_id, api_hash)
    await client.start()
    print("Сессия создана. Теперь скопируй sessions/my_account.session в папку проекта")
    await client.disconnect()

asyncio.run(main())
```

Запусти:

```bash
python create_session.py
```

Введи номер телефона и код подтверждения. Файл сессии сохранится в папке sessions/.

---

Запуск

```bash
# Запуск парсера
python ps.py
```

После запуска парсер:

1. Создаст таблицы в базе данных
2. Подключит все аккаунты из папки sessions/
3. Загрузит группы из groups.txt и invites.txt
4. Запустит воркеров для парсинга
5. Поднимет веб-панель на порту 8081

Логи выводятся в консоль и сохраняются в parser.log.

---

Веб-панель управления

Открой в браузере: http://localhost:8081

Вкладка "⚙️ Панель управления"

Элемент Описание
Статус Работает / На паузе
Аккаунтов Количество подключённых аккаунтов
Очередь Групп в очереди на парсинг
Текущая Группа, которая парсится сейчас
Завершено групп Сколько групп обработано
Сообщений Всего собрано сообщений
Пользователей Всего сохранено пользователей

Кнопки:

· ⏯️ Пауза — приостановить/возобновить парсинг
· 🔄 — обновить статистику
· ➕ — добавить группу по username или ID
· ⬆️ Загрузить сессию — добавить новый аккаунт
· 🔄 Перезагрузить все — перечитать все сессии из папки

Вкладка "💬 Чаты"

Поиск пользователя по ID или @username. При клике на пользователя из списка открывается чат со всеми его сообщениями. Медиафайлы можно открыть по ссылкам.

---

Добавление групп

Способ 1: Через файл groups.txt

Создай или отредактируй groups.txt, каждая строка — одна группа:

```
@chat_name
@another_group
1234567890
https://t.me/joinchat/abc123
```

Валидные форматы:

· @username — публичная группа/канал
· 1234567890 — ID группы
· https://t.me/+hash — инвайт-ссылка (положить в invites.txt)

Способ 2: Через веб-панель

В поле "username или ID" введи название группы и нажми "➕".

Способ 3: Через API

```bash
curl -X POST http://localhost:8081/add_group -d "group=@chat_name"
```

---

Просмотр данных

База данных SQLite

Для просмотра используй любой SQLite-клиент:

```bash
sqlite3 parser.db

# Показать всех пользователей
SELECT id, username, first_name, last_name FROM users;

# Показать количество сообщений по группам
SELECT g.title, COUNT(*) as cnt
FROM messages m JOIN groups g ON m.group_id = g.id
GROUP BY m.group_id;

# Показать последние 10 сообщений
SELECT * FROM messages ORDER BY date DESC LIMIT 10;
```

Медиафайлы

Медиа сохраняются в папку media/<group_id>/:

· Фото: 12345_photo.jpg
· Видео: 12345_video.mp4
· Голосовые: 12345_voice.ogg
· Документы: 12345_document.pdf
· Стикеры: 12345_sticker.webp

Аватары пользователей сохраняются в media/avatars/<user_id>.jpg.

JSON-профили

Файлы users/<user_id>.json содержат:

```json
{
    "id": 123456789,
    "username": "user123",
    "first_name": "Иван",
    "last_name": "Петров",
    "phone": "+79001234567",
    "bio": "Описание профиля",
    "photo_path": "/path/to/photo.jpg"
}
```

---

Решение проблем

Парсер не видит группы

Убедись, что в groups.txt есть строки, и файл в той же папке, что и ps.py.

Веб-панель не открывается

· Проверь, что парсер запущен и в консоли есть строка: Панель: http://localhost:8081
· Если Termux, попробуй http://127.0.0.1:8081
· Проверь, что порт не занят другим приложением

Не собираются пользователи

Парсер собирает пользователей при наличии прав администратора в группе, либо извлекает sender_id из сообщений. Если sender_id — это канал или бот, они пропускаются.

Ошибка Cannot cast InputPeerChannel

Возникает, когда sender_id принадлежит каналу, а не пользователю. Парсер автоматически пропускает такие ID.

FloodWait

Telegram ограничивает количество запросов. Парсер автоматически ждёт указанное время и продолжает работу.

Не хватает памяти

Уменьши max_workers в конфиге до 1-2. Для Termux рекомендуется не более 3 воркеров.

---

Структура базы данных

Таблица groups

Поле Тип Описание
id INTEGER ID группы в Telegram
username TEXT @username
title TEXT Название группы
access_hash INTEGER Хеш доступа

Таблица messages

Поле Тип Описание
id INTEGER ID сообщения
group_id INTEGER ID группы
sender_id INTEGER ID отправителя
date DATETIME Дата сообщения
text TEXT Текст сообщения
media_type TEXT Тип медиа (photo/video/voice/sticker/document)

Таблица users

Поле Тип Описание
id INTEGER ID пользователя
username TEXT @username
first_name TEXT Имя
last_name TEXT Фамилия
phone TEXT Телефон
bio TEXT Описание "О себе"
photo_path TEXT Путь к аватару

Таблица media_files

Поле Тип Описание
id INTEGER ID записи
message_id INTEGER ID сообщения
group_id INTEGER ID группы
type TEXT Тип файла
file_path TEXT Путь к файлу

---

Просмотр БД через SQLite

```bash
sqlite3 parser.db

# Все пользователи
SELECT * FROM users;

# Топ-10 активных пользователей
SELECT sender_id, COUNT(*) as messages
FROM messages GROUP BY sender_id
ORDER BY messages DESC LIMIT 10;

# Сообщения конкретного пользователя
SELECT m.*, g.title
FROM messages m
JOIN groups g ON m.group_id = g.id
WHERE m.sender_id = 123456789
ORDER BY m.date DESC;
```

API эндпоинты

Метод Путь Описание
GET /status Статус парсера (JSON)
GET /log Последние 50 строк лога
GET /users Список пользователей (с пагинацией)
GET /user_messages Сообщения пользователя
POST /add_group Добавить группу
POST /pause Пауза/возобновление
POST /upload_session Загрузить сессию

Примеры API

```bash
# Статус
curl http://localhost:8081/status

# Пользователи (с пагинацией)
curl http://localhost:8081/users?offset=0&limit=100

# Поиск пользователя
curl http://localhost:8081/users?search=ivan

# Сообщения пользователя
curl http://localhost:8081/user_messages?user=123456789&limit=50

# Поставить на паузу
curl -X POST http://localhost:8081/pause
```

---

Горячие клавиши в консоли

· Ctrl+C — остановка парсера с сохранением состояния

---

🤝 Участие в разработке

Приветствуются Pull Request'ы! Для крупных изменений создайте Issue для обсуждения.

⚠️ Дисклеймер

Этот проект предназначен исключительно для образовательных целей. Используйте его в соответствии с законами вашей страны и правилами Telegram.

📄 Лицензия

MIT License — свободное использование, модификация и распространение.

---

⭐ Не забудьте поставить звезду, если проект полезен!
