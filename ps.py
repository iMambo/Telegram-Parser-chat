#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Industrial Parser – full user profiles (bio, about) via GetFullUserRequest
Educational purposes only.
"""

import asyncio, json, logging, os, sys, re, time, io, mimetypes
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Set
from urllib.parse import parse_qs, unquote

try:
    from telethon import TelegramClient, errors, types, functions
    from telethon.tl.functions.users import GetFullUserRequest
    from telethon.sessions import SQLiteSession
    from telethon.network import ConnectionTcpFull
    import aiosqlite
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey
    from sqlalchemy.sql import select, or_
except ImportError as e:
    print("Установи зависимости: pip install telethon sqlalchemy aiosqlite Pillow")
    sys.exit(1)

CONFIG_PATH = "config.json"
STATUS_FILE = "status.json"
DASHBOARD_FILE = "dashboard.html"
DEFAULT_CONFIG = {
    "api_id": 0,
    "api_hash": "",
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
    "enable_user_json": True,
    "api_port": 8081
}

logger = logging.getLogger("parser")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(DEFAULT_CONFIG["log_file"])
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(fh); logger.addHandler(ch)

Base = declarative_base()
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, autoincrement=False)
    username = Column(String); title = Column(String)
    access_hash = Column(Integer, nullable=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, autoincrement=False)
    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    sender_id = Column(Integer); date = Column(DateTime)
    text = Column(Text); media_type = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String); first_name = Column(String)
    last_name = Column(String); phone = Column(String)
    bio = Column(Text); photo_path = Column(String)

class MediaFile(Base):
    __tablename__ = "media_files"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer); group_id = Column(Integer)
    type = Column(String); file_path = Column(String)

class ParserState(Base):
    __tablename__ = "parser_state"
    id = Column(Integer, primary_key=True, default=1)
    current_group_id = Column(Integer, nullable=True)

class TelegramParser:
    def __init__(self, config):
        self.config = config
        self.accounts: Dict[str, TelegramClient] = {}
        self.group_queue = asyncio.Queue()
        self.shutdown = False
        self.paused = False
        self.workers: List[asyncio.Task] = []
        self.status = {
            "accounts": 0, "account_names": [], "groups_total": 0,
            "groups_done": 0, "current_group": None,
            "messages_collected": 0, "users_collected": 0,
            "queue_size": 0, "paused": False
        }
        self._status_lock = asyncio.Lock()
        self._accounts_lock = asyncio.Lock()
        self._known_user_ids: Set[int] = set()

        db_url = f"sqlite+aiosqlite:///{config['sqlite_path']}" if config["db_type"] == "sqlite" else config.get("postgres_url","")
        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(bind=self.engine, class_=AsyncSession, expire_on_commit=False)
        self.media_dir = Path(config["media_dir"]); self.users_dir = Path(config["users_dir"])
        self.media_dir.mkdir(parents=True, exist_ok=True); self.users_dir.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with self.async_session() as session:
            result = await session.execute(select(User.id))
            self._known_user_ids = {row[0] for row in result.fetchall()}
        logger.info(f"Загружено пользователей в кэш: {len(self._known_user_ids)}")

    async def load_accounts(self):
        folder = Path(self.config["accounts_folder"]); folder.mkdir(exist_ok=True)
        api_id = self.config["api_id"]; api_hash = self.config["api_hash"]
        for f in folder.glob("*.session"):
            name = f.stem
            client = TelegramClient(str(f), api_id, api_hash,
                                    connection=ConnectionTcpFull, device_model="Parser",
                                    system_version="1.0", timeout=30)
            self.accounts[name] = client
        self._update_account_status()

    async def connect_accounts(self):
        for name, client in list(self.accounts.items()):
            try:
                await client.start()
                logger.info(f"Аккаунт {name} подключен")
            except Exception as e:
                logger.error(f"Ошибка подключения {name}: {e}")
                await client.disconnect()
                del self.accounts[name]
        self._update_account_status()

    async def add_account_from_session(self, session_path: str):
        async with self._accounts_lock:
            name = Path(session_path).stem
            if name in self.accounts:
                raise ValueError("Сессия с таким именем уже загружена")
            client = TelegramClient(session_path, self.config["api_id"], self.config["api_hash"],
                                    connection=ConnectionTcpFull, device_model="Parser",
                                    system_version="1.0", timeout=30)
            try:
                await client.start()
                self.accounts[name] = client
                logger.info(f"Новый аккаунт {name} добавлен и подключен")
                self._update_account_status()
            except Exception as e:
                await client.disconnect()
                raise RuntimeError(f"Не удалось запустить сессию: {e}")

    def _update_account_status(self):
        self.status["accounts"] = len(self.accounts)
        self.status["account_names"] = list(self.accounts.keys())

    async def reload_accounts(self):
        async with self._accounts_lock:
            for c in self.accounts.values():
                await c.disconnect()
            self.accounts.clear()
        await self.load_accounts()
        await self.connect_accounts()

    async def load_groups(self):
        gf = Path("groups.txt")
        if gf.exists():
            for line in gf.read_text().splitlines():
                if line := line.strip():
                    await self.group_queue.put(line)
        self._update_queue_size()

    async def worker(self, wid):
        while not self.shutdown:
            if self.paused:
                await asyncio.sleep(1); continue
            try:
                group_input = await asyncio.wait_for(self.group_queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            client = await self._get_available_account()
            if not client:
                await asyncio.sleep(5)
                self.group_queue.task_done(); continue
            try:
                entity = await client.get_entity(group_input)
            except ValueError:
                logger.error(f"Группа {group_input} не найдена")
                self.group_queue.task_done(); continue
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                self.group_queue.task_done(); continue

            async with self.async_session() as session:
                g = Group(id=entity.id, username=getattr(entity,'username',None),
                          title=entity.title, access_hash=entity.access_hash)
                await session.merge(g); await session.commit()

            async with self._status_lock:
                self.status["current_group"] = group_input; await self._write_status()

            logger.info(f"Worker {wid} парсит {group_input}")
            await self._parse_messages(client, entity, entity.id)
            await self._parse_users(client, entity, entity.id)

            async with self._status_lock:
                self.status["groups_done"] += 1
                self.status["current_group"] = None
                self._update_queue_size(); await self._write_status()
            self.group_queue.task_done()

    async def _get_available_account(self):
        for c in self.accounts.values():
            if c.is_connected(): return c
        return None

    async def _parse_messages(self, client, entity, gid):
        offset = 0
        while not self.shutdown and not self.paused:
            try:
                msgs = await client.get_messages(entity, limit=self.config["batch_size"], offset_id=offset)
                if not msgs: break
                for m in msgs:
                    if m.sender_id:
                        await self._fetch_and_save_user(m.sender_id, client)
                    await self._save_message(m, gid, client)
                    offset = m.id
                    async with self._status_lock: self.status["messages_collected"] += 1
                await asyncio.sleep(self.config["request_delay"])
            except errors.FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Ошибка сообщений: {e}"); break

    async def _fetch_and_save_user(self, user_id: int, client: TelegramClient):
        if user_id in self._known_user_ids:
            return
        async with self.async_session() as session:
            if await session.get(User, user_id):
                self._known_user_ids.add(user_id)
                return

        try:
            entity = await client.get_entity(user_id)
        except errors.FloodWaitError as e:
            logger.warning(f"FloodWait на get_entity для {user_id}: {e.seconds}s")
            await asyncio.sleep(e.seconds)
            return
        except Exception as e:
            logger.error(f"Не удалось получить сущность для {user_id}: {e}")
            return

        if not isinstance(entity, types.User):
            logger.debug(f"ID {user_id} не пользователь (тип: {type(entity).__name__}), пропускаем")
            self._known_user_ids.add(user_id)  # чтобы не повторять попытки
            return

        full_info = None
        try:
            full_info = await client(GetFullUserRequest(user_id))
        except errors.FloodWaitError as e:
            logger.warning(f"FloodWait на GetFullUser для {user_id}: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Ошибка GetFullUser для {user_id}: {e}")

        await self._save_user(entity, full_info, client)

    async def _save_user(self, user_entity, full_info, client):
        if not user_entity or not user_entity.id:
            return
        uid = user_entity.id
        if uid in self._known_user_ids:
            return

        async with self.async_session() as session:
            if await session.get(User, uid):
                self._known_user_ids.add(uid)
                return

            username = getattr(user_entity, 'username', None)
            first_name = getattr(user_entity, 'first_name', None)
            last_name = getattr(user_entity, 'last_name', None)
            phone = getattr(user_entity, 'phone', None)
            bio = None
            if full_info and hasattr(full_info, 'full_user') and hasattr(full_info.full_user, 'about'):
                bio = full_info.full_user.about
            elif full_info and hasattr(full_info, 'about'):
                bio = full_info.about

            photo_path = None
            if user_entity.photo:
                d = self.media_dir / "avatars"
                d.mkdir(exist_ok=True)
                try:
                    p = await client.download_profile_photo(user_entity, str(d / f"{uid}.jpg"))
                    if p: photo_path = str(p)
                except: pass

            u = User(id=uid, username=username, first_name=first_name,
                     last_name=last_name, phone=phone, bio=bio, photo_path=photo_path)
            session.add(u)
            await session.commit()
            self._known_user_ids.add(uid)
            async with self._status_lock:
                self.status["users_collected"] += 1

            if self.config["enable_user_json"]:
                data = {"id": u.id, "username": u.username, "first_name": u.first_name,
                        "last_name": u.last_name, "phone": u.phone, "bio": u.bio, "photo_path": u.photo_path}
                try:
                    with open(self.users_dir / f"{u.id}.json", "w") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except: pass

    async def _parse_users(self, client, entity, gid):
        try:
            participants = await client.get_participants(entity)
            for user in participants:
                if self.paused or self.shutdown: break
                if user.id not in self._known_user_ids:
                    if not isinstance(user, types.User):
                        continue
                    try:
                        full_info = await client(GetFullUserRequest(user.id))
                    except errors.FloodWaitError as e:
                        await asyncio.sleep(e.seconds)
                        continue
                    except Exception:
                        full_info = None
                    await self._save_user(user, full_info, client)
        except errors.ChatAdminRequiredError:
            logger.info(f"Нет прав на список участников в группе {gid}")
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logger.error(f"Ошибка сбора участников: {e}")

    async def _save_message(self, msg, gid, client):
        async with self.async_session() as sess:
            existing = await sess.get(Message, (msg.id, gid))
            if existing: return
            mt = None
            if msg.media:
                if isinstance(msg.media, types.MessageMediaPhoto): mt = "photo"
                elif isinstance(msg.media, types.MessageMediaDocument):
                    mt = "video" if msg.video else "audio" if msg.audio else "voice" if msg.voice else "sticker" if msg.sticker else "document"
            message = Message(id=msg.id, group_id=gid, sender_id=msg.sender_id,
                              date=msg.date, text=msg.text or "", media_type=mt)
            sess.add(message)
            if mt and msg.media:
                path = await self._download_media(msg, gid, mt, client)
                if path:
                    sess.add(MediaFile(message_id=msg.id, group_id=gid, type=mt, file_path=str(path)))
            await sess.commit()

    async def _download_media(self, msg, gid, mt, client):
        folder = self.media_dir / str(gid); folder.mkdir(exist_ok=True)
        ext = {"video":".mp4","voice":".ogg","sticker":".webp","audio":".mp3"}.get(mt, ".jpg")
        fname = f"{msg.id}_{mt}{ext}"; path = folder / fname
        try:
            await client.download_media(msg, str(path))
            return path
        except: return None

    async def _write_status(self):
        self.status["queue_size"] = self.group_queue.qsize()
        self.status["paused"] = self.paused
        with open(STATUS_FILE,"w") as f: json.dump(self.status, f, ensure_ascii=False)

    def _update_queue_size(self): self.status["queue_size"] = self.group_queue.qsize()

    async def add_group(self, name):
        await self.group_queue.put(name); self._update_queue_size()

    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused

    # ---------------------------- HTTP API ----------------------------
    async def start_api(self):
        port = self.config.get("api_port", 8081)
        server = await asyncio.start_server(self._handle_client, "0.0.0.0", port)
        logger.info(f"Панель: http://localhost:{port}")
        async with server:
            await server.serve_forever()

    async def _handle_client(self, reader, writer):
        try:
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10)
            raw = raw.decode()
            lines = raw.split("\r\n")
            method, path, _ = lines[0].split()
            headers = {}
            for l in lines[1:]:
                if ":" in l:
                    k,v = l.split(":",1); headers[k.strip().lower()] = v.strip()
            content_length = int(headers.get("content-length",0))
            body = b""
            if content_length>0:
                body = await asyncio.wait_for(reader.readexactly(content_length), timeout=10)

            if method == "GET":
                if path in ("/","/dashboard.html"):
                    await self._serve_file(writer, DASHBOARD_FILE, "text/html")
                elif path == "/status":
                    async with self._status_lock:
                        js = json.dumps(self.status, ensure_ascii=False)
                    await self._respond(writer, 200, js, "application/json")
                elif path == "/log":
                    if os.path.exists(self.config["log_file"]):
                        txt = "".join(open(self.config["log_file"]).readlines()[-50:])
                    else:
                        txt = "Лог пуст"
                    await self._respond(writer, 200, txt, "text/plain; charset=utf-8")
                elif path.startswith("/users"):
                    await self._handle_users(writer, path)
                elif path.startswith("/user_messages"):
                    await self._handle_user_messages(writer, path)
                elif path.startswith("/media"):
                    await self._handle_media(writer, path)
                else:
                    await self._respond(writer, 404, "Not found", "text/plain")
            elif method == "POST":
                if path == "/add_group":
                    data = parse_qs(body.decode())
                    group = data.get("group", [None])[0]
                    if group:
                        await self.add_group(group)
                        await self._respond(writer, 200, '{"status":"ok"}', "application/json")
                    else:
                        await self._respond(writer, 400, '{"error":"no group"}', "application/json")
                elif path == "/pause":
                    paused = self.toggle_pause()
                    await self._respond(writer, 200, json.dumps({"paused":paused}), "application/json")
                elif path == "/upload_session":
                    ctype = headers.get("content-type","")
                    if "multipart/form-data" not in ctype:
                        await self._respond(writer, 400, "Need multipart/form-data", "text/plain"); return
                    boundary = ctype.split("boundary=")[1].strip()
                    parts = body.split(f"--{boundary}".encode())
                    file_saved = False
                    for part in parts:
                        if b"Content-Disposition" in part and b"filename=" in part:
                            header_end = part.find(b"\r\n\r\n")
                            headers_part = part[:header_end].decode()
                            file_data = part[header_end+4:]
                            if file_data.endswith(b"\r\n"):
                                file_data = file_data[:-2]
                            fname_match = re.search(r'filename="([^"]+)"', headers_part)
                            if not fname_match: continue
                            orig_name = fname_match.group(1)
                            if not orig_name.endswith(".session"):
                                await self._respond(writer, 400, "Only .session files allowed", "text/plain"); return
                            dest = Path(self.config["accounts_folder"]) / orig_name
                            dest.write_bytes(file_data)
                            try:
                                await self.add_account_from_session(str(dest))
                                await self._respond(writer, 200, json.dumps({"status":"ok","account":orig_name}), "application/json")
                            except Exception as e:
                                await self._respond(writer, 500, json.dumps({"error":str(e)}), "application/json")
                            file_saved = True
                            break
                    if not file_saved:
                        await self._respond(writer, 400, "No file part found", "text/plain")
                elif path == "/reload_accounts":
                    await self.reload_accounts()
                    await self._respond(writer, 200, '{"status":"ok"}', "application/json")
                else:
                    await self._respond(writer, 404, "Not found", "text/plain")
        except Exception as e:
            logger.error(f"HTTP error: {e}")
        finally:
            writer.close(); await writer.wait_closed()

    async def _handle_users(self, writer, path):
        query = path.split("?",1)[1] if "?" in path else ""
        params = parse_qs(query)
        offset = int(params.get("offset", [0])[0])
        limit = min(int(params.get("limit", [100])[0]), 500)
        search = params.get("search", [None])[0]

        async with self.async_session() as session:
            stmt = select(User)
            if search:
                pattern = f"%{search}%"
                stmt = stmt.where(
                    or_(User.username.ilike(pattern),
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern))
                )
            stmt = stmt.order_by(User.id).offset(offset).limit(limit + 1)
            result = await session.execute(stmt)
            users = result.scalars().all()
            has_more = len(users) > limit
            if has_more:
                users = users[:limit]
            output = [{"id": u.id, "username": u.username,
                       "first_name": u.first_name, "last_name": u.last_name}
                      for u in users]
            await self._respond(writer, 200,
                json.dumps({"users": output, "has_more": has_more}, ensure_ascii=False),
                "application/json")

    async def _handle_user_messages(self, writer, path):
        if "?" not in path:
            await self._respond(writer, 400, '{"error":"missing user parameter"}', "application/json")
            return
        query = path.split("?",1)[1]
        params = parse_qs(query)
        user_input = params.get("user", [None])[0]
        if not user_input:
            await self._respond(writer, 400, '{"error":"user required"}', "application/json")
            return
        offset = int(params.get("offset", [0])[0])
        limit = min(int(params.get("limit", [50])[0]), 200)
        user_input = unquote(user_input).strip()

        async with self.async_session() as session:
            user = None
            if user_input.startswith("@"):
                user = (await session.execute(select(User).where(User.username == user_input[1:]))).scalar()
            elif user_input.isdigit():
                user = await session.get(User, int(user_input))
            else:
                user = (await session.execute(select(User).where(User.username == user_input))).scalar()

            if not user:
                await self._respond(writer, 404, '{"error":"user not found in DB"}', "application/json")
                return

            stmt = select(Message).where(Message.sender_id == user.id)\
                                  .order_by(Message.date.asc())\
                                  .offset(offset).limit(limit)
            result = await session.execute(stmt)
            messages = result.scalars().all()

            msg_ids = [(m.id, m.group_id) for m in messages]
            media_stmt = select(MediaFile).where(
                (MediaFile.message_id.in_([mid for mid,_ in msg_ids])) &
                (MediaFile.group_id.in_([gid for _,gid in msg_ids]))
            )
            media_res = await session.execute(media_stmt)
            media_map = {}
            for mf in media_res.scalars():
                key = (mf.message_id, mf.group_id)
                media_map.setdefault(key, []).append(mf)

            output = []
            for m in messages:
                key = (m.id, m.group_id)
                files = media_map.get(key, [])
                output.append({
                    "id": m.id,
                    "group_id": m.group_id,
                    "date": m.date.isoformat() if m.date else None,
                    "text": m.text,
                    "media_type": m.media_type,
                    "files": [{"type": f.type, "url": f"/media?file={f.file_path}"} for f in files]
                })

            await self._respond(writer, 200,
                json.dumps({
                    "user": {"id": user.id, "username": user.username,
                             "first_name": user.first_name, "last_name": user.last_name},
                    "messages": output
                }, ensure_ascii=False),
                "application/json")

    async def _handle_media(self, writer, path):
        if "?file=" not in path:
            await self._respond(writer, 400, "Missing file param", "text/plain")
            return
        file_path = unquote(path.split("?file=",1)[1])
        full_path = Path(file_path)
        if not full_path.exists():
            await self._respond(writer, 404, "File not found", "text/plain")
            return
        try:
            with open(full_path, "rb") as f:
                data = f.read()
            ct = mimetypes.guess_type(str(full_path))[0] or "application/octet-stream"
            resp = f"HTTP/1.1 200 OK\r\nContent-Type: {ct}\r\nContent-Length: {len(data)}\r\n\r\n"
            writer.write(resp.encode() + data)
            await writer.drain()
        except Exception as e:
            await self._respond(writer, 500, str(e), "text/plain")

    async def _serve_file(self, writer, path, ctype):
        try:
            with open(path,"r",encoding="utf-8") as f: content = f.read()
            await self._respond(writer, 200, content, ctype)
        except FileNotFoundError:
            await self._respond(writer, 404, "Dashboard not found", "text/plain")

    async def _respond(self, writer, code, body, ctype):
        resp = f"HTTP/1.1 {code} OK\r\nContent-Type: {ctype}\r\nContent-Length: {len(body.encode())}\r\n\r\n{body}"
        writer.write(resp.encode()); await writer.drain()

    async def run(self):
        await self.init_db()
        await self.load_accounts()
        await self.connect_accounts()
        await self.load_groups()
        for i in range(self.config["max_workers"]):
            self.workers.append(asyncio.create_task(self.worker(i)))
        async def status_writer():
            while not self.shutdown:
                async with self._status_lock: await self._write_status()
                await asyncio.sleep(2)
        asyncio.create_task(status_writer())
        asyncio.create_task(self.start_api())
        try:
            while not self.shutdown: await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown = True
            for w in self.workers: w.cancel()
            await asyncio.gather(*self.workers, return_exceptions=True)
            for c in self.accounts.values(): await c.disconnect()
            await self.engine.dispose()
            logger.info("Парсер остановлен")

async def main():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH,"w") as f: json.dump(DEFAULT_CONFIG, f, indent=2)
    with open(CONFIG_PATH) as f: config = json.load(f)
    parser = TelegramParser(config)
    await parser.run()

if __name__ == "__main__":
    asyncio.run(main())
