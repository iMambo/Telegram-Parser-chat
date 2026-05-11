
```markdown
# Telegram-Parser-chat

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Termux](https://img.shields.io/badge/Termux-Supported-brightgreen)](https://termux.dev)

Мощный промышленный парсер Telegram-групп с веб-панелью управления. Собирает сообщения, медиафайлы и полные профили пользователей с автоматическим обходом ограничений.

## Содержание

1. [Обзор](#обзор)
2. [Требования](#требования)
3. [Файлы проекта](#файлы-проекта)
4. [Установка](#установка)
5. [Конфигурация](#конфигурация)
6. [Подготовка аккаунтов](#подготовка-аккаунтов)
7. [Запуск](#запуск)
8. [Веб-панель управления](#веб-панель-управления)
9. [Добавление групп](#добавление-групп)
10. [Просмотр данных](#просмотр-данных)
11. [Решение проблем](#решение-проблем)
12. [Структура базы данных](#структура-базы-данных)

---

## Обзор

Telegram Industrial Parser — мощный инструмент для сбора данных из Telegram-групп. Парсер автоматически собирает сообщения, медиафайлы и профили пользователей, сохраняя всё в базу данных SQLite (или PostgreSQL). Встроенная веб-панель позволяет управлять парсером и просматривать собранные данные через браузер.

### Ключевые возможности

| Возможность | Описание |
|:------------|:---------|
| Мультиаккаунтинг | Ротация аккаунтов при FloodWait |
| Типы сообщений | Текст, фото, видео, голосовые, документы, стикеры |
| Профили пользователей | Username, имя, фамилия, телефон, био, аватар |
| Сбор пользователей | Автоматически из сообщений |
| Закрытые группы | Вступление по инвайт-ссылкам |
| Медиафайлы | Сохранение в структурированную файловую систему |
| Чекпойнтинг | Продолжение с места остановки |
| Веб-панель | Управление и просмотр чатов через браузер |
| Логирование | Все действия записываются |

---

## Требования

| Компонент | Версия/Описание |
|:----------|:----------------|
| Python | 3.10 или выше |
| ОС | Termux (Android), Linux, Windows |
| Библиотеки | telethon, sqlalchemy, aiosqlite, Pillow |

**Установка зависимостей:**

```bash
pip install telethon sqlalchemy aiosqlite Pillow
```

Клонирование репозитория:

```bash
git clone https://github.com/your-username/telegram-parser-chat.git
cd telegram-parser-chat
```

Получение API ключей: my.telegram.org

---

Файлы проекта

Файл Описание
ps.py Основной скрипт парсера
dashboard.html Веб-панель управления
config.json Конфигурация парсера
sessions/ Папка с файлами сессий аккаунтов
groups.txt Список групп для парсинга
invites.txt Инвайт-ссылки для закрытых групп
parser.db База данных SQLite
parser.log Файл логов
status.json Текущий статус для веб-панели

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
```

---

Конфигурация

При первом запуске парсер автоматически создаст config.json с настройками по умолчанию. Отредактируй его:

```json
{
    "api_id": 1234567,
    "api_hash": "abc123def456",
    "accounts_folder": "sessions",
    "db_type": "sqlite",
    "sqlite_path": "parser.db",
    "batch_size": 100,
    "media_dir": "media",
    "users_dir": "users",
    "log_file": "parser.log",
    "max_workers": 5,
    "request_delay": 0.3,
    "max_participants": 10000,
    "enable_user_json": true,
    "api_port": 8081
}
```

Параметры конфигурации

Параметр Тип Описание По умолчанию
api_id int API ID приложения Telegram 0
api_hash str API Hash приложения Telegram ""
accounts_folder str Папка с .session файлами "sessions"
db_type str sqlite или postgresql "sqlite"
sqlite_path str Путь к файлу БД "parser.db"
batch_size int Сообщений за запрос 100
media_dir str Папка для медиафайлов "media"
users_dir str Папка для JSON профилей "users"
log_file str Файл логов "parser.log"
max_workers int Количество воркеров 5
request_delay float Задержка между запросами (сек) 0.3
max_participants int Максимум участников для сбора 10000
enable_user_json bool Сохранять JSON файлы true
api_port int Порт веб-панели 8081

---

Подготовка аккаунтов

Способы создания сессий

Способ Описание Сложность
Веб-панель Загрузить .session через браузер Лёгкая
Скрипт Создать create_session.py и запустить Средняя

Способ 1: Через веб-панель

Шаг Действие
1 Запусти парсер: python ps.py
2 Открой веб-панель: http://localhost:8081
3 Перейди во вкладку "Панель управления" → "Сессии"
4 Выбери .session файл и нажми "⬆️ Загрузить сессию"

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
    print("Сессия создана!")
    await client.disconnect()

asyncio.run(main())
```

Запусти:

```bash
python create_session.py
```

---

Запуск

```bash
# Запуск парсера
python ps.py
```

Что происходит при запуске

Шаг Действие
1 Создаёт таблицы в базе данных
2 Подключает все аккаунты из папки sessions/
3 Загружает группы из groups.txt и invites.txt
4 Запускает воркеров для парсинга
5 Поднимает веб-панель на порту 8081

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

Кнопки управления

Кнопка Действие
⏯️ Пауза Приостановить/возобновить парсинг
🔄 Обновить статистику
➕ Добавить группу по username или ID
⬆️ Загрузить сессию Добавить новый аккаунт
🔄 Перезагрузить все Перечитать все сессии из папки

Вкладка "💬 Чаты"

Функция Описание
Список пользователей Все собранные пользователи
Поиск По ID или @username
Чат Просмотр сообщений конкретного пользователя
Медиа Открытие файлов по ссылкам

---

Добавление групп

Способы добавления

Способ Формат Пример
groups.txt По одной на строку @chat_name
Веб-панель Поле ввода + кнопка ➕ username или ID
API POST запрос curl -X POST .../add_group
invites.txt Инвайт-ссылки https://t.me/+hash

Валидные форматы

Формат Пример Описание
@username @chat_name Публичная группа/канал
ID 1234567890 ID группы
Инвайт-ссылка https://t.me/+hash Закрытая группа

---

Просмотр данных

Медиафайлы

Тип Путь Пример имени файла
Фото media/<group_id>/ 12345_photo.jpg
Видео media/<group_id>/ 12346_video.mp4
Голосовые media/<group_id>/ 12347_voice.ogg
Документы media/<group_id>/ 12348_document.pdf
Стикеры media/<group_id>/ 12349_sticker.webp
Аватары media/avatars/ 987654321.jpg

JSON-профили пользователей

Файлы users/<user_id>.json содержат:

```json
{
    "id": 123456789,
    "username": "user123",
    "first_name": "Иван",
    "last_name": "Петров",
    "phone": "+79001234567",
    "bio": "Описание профиля",
    "photo_path": "media/avatars/123456789.jpg"
}
```

---

Решение проблем

Проблема Решение
Парсер не видит группы Проверь, что groups.txt лежит в папке с ps.py
Веб-панель не открывается Проверь сообщение в консоли: Панель: http://localhost:8081
Пользователи не собираются Парсер собирает из сообщений, если нет прав админа
Ошибка Cannot cast InputPeerChannel ID каналов и ботов пропускаются автоматически
FloodWait Парсер автоматически ждёт. Увеличь request_delay
Не хватает памяти Уменьши max_workers до 1-2

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
phone TEXT Номер телефона
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

API эндпоинты

Метод Путь Описание Параметры
GET /status Статус парсера (JSON) —
GET /log Последние 50 строк лога —
GET /users Список пользователей offset, limit, search
GET /user_messages Сообщения пользователя user, offset, limit
POST /add_group Добавить группу group
POST /pause Пауза/возобновление —
POST /upload_session Загрузить сессию multipart/form-data
POST /reload_accounts Перезагрузить аккаунты —

Примеры API запросов

```bash
# Статус парсера
curl http://localhost:8081/status

# Список пользователей с пагинацией
curl "http://localhost:8081/users?offset=0&limit=100"

# Поиск пользователя
curl "http://localhost:8081/users?search=ivan"

# Сообщения конкретного пользователя
curl "http://localhost:8081/user_messages?user=@username&limit=50"

# Добавить группу в очередь
curl -X POST http://localhost:8081/add_group -d "group=@chat_name"

# Поставить парсер на паузу
curl -X POST http://localhost:8081/pause
```

---

Горячие клавиши

Клавиши Действие
Ctrl+C Остановка парсера с сохранением состояния

---

🤝 Участие в разработке

Приветствуются Pull Request'ы! Для крупных изменений создайте Issue для обсуждения.

⚠️ Дисклеймер

Этот проект предназначен исключительно для образовательных целей. Используйте его в соответствии с законами вашей страны и правилами Telegram.

📄 Лицензия

MIT License — свободное использование, модификация и распространение.

---

⭐ Не забудьте поставить звезду, если проект полезен!
