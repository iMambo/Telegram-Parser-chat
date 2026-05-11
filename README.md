# Telegram Industrial Parser

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Termux](https://img.shields.io/badge/Termux-Supported-brightgreen)](https://termux.dev)

Мощный промышленный парсер Telegram-групп с веб-панелью управления. Собирает сообщения, медиафайлы и полные профили пользователей с автоматическим обходом ограничений.

## ✨ Возможности

| Возможность | Описание |
|:------------|:---------|
| 🚀 Мультиаккаунтинг | Автоматическая ротация аккаунтов при FloodWait |
| 📊 Типы сообщений | Текст, фото, видео, голосовые, документы, стикеры |
| 👤 Профили | Username, имя, фамилия, телефон, био, аватар |
| 🔒 Закрытые группы | Вступление по инвайт-ссылкам |
| 📁 Хранение | SQLite/PostgreSQL + файловая система |
| 🌐 Веб-панель | Управление парсером и просмотр чатов через браузер |
| 💾 Чекпойнтинг | Продолжение с места остановки |
| 📱 Termux | Полная поддержка Android без root |

## 📦 Установка

### Зависимости

```bash
pip install telethon sqlalchemy aiosqlite Pillow
