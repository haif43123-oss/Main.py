import asyncio
import json
import os
import time
import logging
import random
import string
from datetime import datetime
from copy import deepcopy

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile, BufferedInputFile
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("BlastBot")

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
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789"
)

def sc(text: str) -> str:
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def _apply_style(obj, style: str | None):
    if style in ("primary", "success", "danger"):
        try:
            setattr(obj, "style", style)
        except Exception:
            pass
    return obj

def btn(
    text: str,
    callback_data: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = "primary"
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    if emoji_id:
        b = InlineKeyboardButton(text=label, callback_data=callback_data, icon_custom_emoji_id=emoji_id)
    else:
        b = InlineKeyboardButton(text=label, callback_data=callback_data)
    return _apply_style(b, style)

def btn_url(
    text: str,
    url: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = "primary"
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    if emoji_id:
        b = InlineKeyboardButton(text=label, url=url, icon_custom_emoji_id=emoji_id)
    else:
        b = InlineKeyboardButton(text=label, url=url)
    return _apply_style(b, style)

def style_btn(
    text: str,
    style: str = "primary",
    request_contact: bool = False,
    request_location: bool = False
) -> KeyboardButton:
    kb_btn = KeyboardButton(text=sc(text), request_contact=request_contact, request_location=request_location)
    return _apply_style(kb_btn, style)

def default_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [style_btn("🚀 Start Blast", style="success"), style_btn("📹 Videos", style="primary")],
            [style_btn("💰 Credits", style="primary"), style_btn("🛑 Stop Blast", style="danger")]
        ],
        resize_keyboard=True
    )

MAIN_OWNER = 8241730977
SUPER_ADMIN_NAME = "@Sakira540"
SUPER_ADMIN_LINK = "https://t.me/xtylishbedu"
SUPER_ADMINS = [8682912888]

BOT_TOKEN = "9273864914:AAGSMztMHacgkv_nhGhBNwo9EYzmnDxE_fQ"
LOG_CHANNEL_ID = -1004437456868

_DATA_FILE = "blast_bdata.json"
_VERSION = "v3.1"
_PROGRESS_UPDATE_INTERVAL = 1.0
_BACKGROUND_SCAN_INTERVAL = 60.0

# Speed settings: default is MEDIUM
SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

PREMIUM_PLANS = [
    {"id": "prem_1d", "title": "1 Day", "days": 1, "seconds": 86400, "price": 5},
    {"id": "prem_3d", "title": "3 Day", "days": 3, "seconds": 3 * 86400, "price": 10},
    {"id": "prem_7d", "title": "7 Day", "days": 7, "seconds": 7 * 86400, "price": 20},
    {"id": "prem_30d", "title": "30 Day", "days": 30, "seconds": 30 * 86400, "price": 60},
]

AUTO_MSG_WORKER_STARTED = False

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

class UserSession:
    __slots__ = ['uid', 'cancelled', 'sent', 'failed', 'task', 'start_time', 'lock', 'number', 'target_uid']

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

USER_SESSIONS = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES = []
LAST_SCAN_TIME = 0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
DEVICE_HEALTH_LOG = []
FB_DEVICE_COUNTS = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS = {}

class S(StatesGroup):
    send_number = State()
    send_message = State()
    send_speed = State()
    send_count = State()
    owner_send_number = State()
    owner_send_message = State()
    owner_send_speed = State()
    owner_send_count = State()
    admin_send_number = State()
    admin_send_message = State()
    admin_send_speed = State()
    admin_send_count = State()
    redeem_code = State()
    add_firebase = State()
    add_firebase_file = State()
    add_owner = State()
    add_admin = State()
    ban_user = State()
    unban_user = State()
    broadcast = State()
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
    give_prem_uid = State()
    give_prem_duration = State()
    import_db_file = State()
    auto_msg_text = State()
    auto_msg_custom_min = State()

def _default_data() -> dict:
    return {
        "owners": [MAIN_OWNER],
        "admins": [],
        "banned": [],
        "free_mode": False,
        "approved": [],
        "firebases": [],
        "users": {},
        "premium_users": {},
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
        "auto_msg": {
            "enabled": False,
            "target": "all_users",
            "text": "",
            "interval_minutes": 5,
            "last_msg_ids": {},
            "last_sent_at": 0
        }
    }

def load() -> dict:
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if not isinstance(data.get("auto_msg"), dict):
                data["auto_msg"] = deepcopy(default["auto_msg"])
            data["auto_msg"].setdefault("enabled", False)
            data["auto_msg"].setdefault("target", "all_users")
            data["auto_msg"].setdefault("text", "")
            data["auto_msg"].setdefault("interval_minutes", 5)
            data["auto_msg"].setdefault("last_msg_ids", {})
            data["auto_msg"].setdefault("last_sent_at", 0)
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            for uid_str, u in data.get("users", {}).items():
                if "credits" not in u:
                    u["credits"] = 0
                if "sms_history" not in u:
                    u["sms_history"] = []
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    d = _default_data()
    save(d)
    return d

def save(d: dict):
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def reg_user(uid: int, name: str, d: dict) -> bool:
    k = str(uid)
    if k not in d["users"]:
        d["users"][k] = {
            "name": name, "uses": 0, "credits": 0,
            "joined_at": int(time.time()),
            "refer_code": None, "referred_by": None,
            "sms_history": []
        }
        return True
    return False

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()), "uid": uid, "action": action, "details": details
    })
    if len(d["activity_log"]) > 1000:
        d["activity_log"] = d["activity_log"][-1000:]

def is_main_owner(uid: int) -> bool:
    return uid == MAIN_OWNER

def is_owner(uid: int, d: dict) -> bool:
    return uid in d.get("owners", [MAIN_OWNER]) or uid in SUPER_ADMINS

def is_admin(uid: int, d: dict) -> bool:
    return is_owner(uid, d) or uid in d.get("admins", [])

def is_banned(uid: int, d: dict) -> bool:
    return uid in d.get("banned", [])

def get_premium_record(uid: int, d: dict) -> dict | None:
    rec = d.get("premium_users", {}).get(str(uid))
    if not rec:
        return None
    if int(rec.get("expires_at", 0)) <= int(time.time()):
        return None
    return rec

def is_premium(uid: int, d: dict) -> bool:
    return get_premium_record(uid, d) is not None

def grant_user_premium(uid: int, seconds: int, label: str, granted_by: int, d: dict) -> int:
    now = int(time.time())
    existing = d.setdefault("premium_users", {}).get(str(uid), {})
    base = max(now, int(existing.get("expires_at", 0)))
    expires_at = base + seconds
    d["premium_users"][str(uid)] = {
        "expires_at": expires_at,
        "label": label,
        "granted_by": granted_by,
        "updated_at": now
    }
    return expires_at

def parse_duration_input(raw: str) -> tuple[int, str] | None:
    txt = raw.strip().lower()
    if not txt:
        return None
    try:
        if txt.endswith("h") or "hour" in txt or "hr" in txt:
            num_part = "".join(ch for ch in txt if ch.isdigit() or ch == ".")
            val = float(num_part)
            if val <= 0:
                return None
            return int(val * 3600), f"{val:g} Hour(s)"
        if txt.endswith("d") or "day" in txt:
            num_part = "".join(ch for ch in txt if ch.isdigit() or ch == ".")
            val = float(num_part)
            if val <= 0:
                return None
            return int(val * 86400), f"{val:g} Day(s)"
        val = float(txt)
        if val <= 0:
            return None
        return int(val * 86400), f"{val:g} Day(s)"
    except Exception:
        return None

def can_use(uid: int, d: dict) -> bool:
    if is_banned(uid, d):
        return False
    if is_admin(uid, d) or is_premium(uid, d):
        return True
    if d.get("free_mode"):
        return True
    if uid in d.get("approved", []):
        return True
    return False

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid): return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d): return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []): return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if is_premium(uid, d): return f"{em(EMOJI_STAR, '💎')} ᴘʀᴇᴍɪᴜᴍ"
    if uid in d.get("approved", []): return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"): return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"

def get_user_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)

def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {"credits": 0}
    d["users"][k]["credits"] = d["users"][k].get("credits", 0) + amount

def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    if k in d.get("users", {}):
        current = d["users"][k].get("credits", 0)
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
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    add_credits(new_uid, ref_credits, d)
    add_credits(referrer_uid, ref_credits, d)
    d["users"][str(new_uid)]["referred_by"] = referrer_uid
    save(d)
    return True, f"{em(EMOJI_GIFT, '🎉')} ᴡᴇʟᴄᴏᴍᴇ! ᴀᴀᴘᴋᴏ {ref_credits} ᴄʀᴇᴅɪᴛs ᴍɪʟᴇ ʜᴀɪɴ!", referrer_uid

async def send_random_video(bot: Bot, chat_id: int, caption: str = ""):
    d = load()
    videos = d.get("videos", [])
    if videos:
        video_item = random.choice(videos)
        try:
            await bot.send_video(chat_id, video=video_item, caption=caption, parse_mode="HTML")
        except Exception as e:
            log.error(f"Failed to send random video: {e}")

def kb(*rows) -> InlineKeyboardMarkup:
    out_rows = []
    for row in rows:
        built = []
        for item in row:
            if len(item) == 3:
                t, c, st = item
                built.append(btn(t, c, style=st))
            else:
                t, c = item
                built.append(btn(t, c, style="primary"))
        out_rows.append(built)
    return InlineKeyboardMarkup(inline_keyboard=out_rows)

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("ғᴀsᴛ ⚡", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", style="success"),
            btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", style="primary"),
            btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", style="primary")
        ],
        [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌", style="danger")]
    ])

def premium_plans_kb(back_cb: str = "user:home") -> InlineKeyboardMarkup:
    rows = []
    for p in PREMIUM_PLANS:
        rows.append([
            btn(
                f"{p['title']} — ₹{p['price']}",
                f"prem:buy:{p['id']}",
                EMOJI_CROWN,
                "💎",
                style="success"
            )
        ])
    rows.append([btn("ʙᴀᴄᴋ", back_cb, EMOJI_GEAR, "🔙", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def auto_msg_kb() -> InlineKeyboardMarkup:
    d = load()
    cfg = d.get("auto_msg", {})
    enabled = cfg.get("enabled", False)
    cur_min = int(cfg.get("interval_minutes", 5))
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn(f"{'✅ ' if cur_min == 5 else ''}5 ᴍɪɴ", "owner:automsg:min:5", EMOJI_GEAR, "⏱", style="success" if cur_min == 5 else "primary"),
            btn(f"{'✅ ' if cur_min == 10 else ''}10 ᴍɪɴ", "owner:automsg:min:10", EMOJI_GEAR, "⏱", style="success" if cur_min == 10 else "primary"),
            btn("ᴄᴜsᴛᴏᴍ ᴍɪɴ", "owner:automsg:min:custom", EMOJI_STAR, "✏️", style="primary"),
        ],
        [
            btn("sᴇᴛ ᴜsᴇʀ ᴍsɢ", "owner:automsg:setup", EMOJI_BELL, "📝", style="success"),
            btn("sᴇɴᴅ ɴᴏᴡ (ᴅᴇʟ ᴘʀᴇᴠ)", "owner:automsg:now", EMOJI_ROCKET, "🚀", style="primary"),
        ],
        [
            btn(
                "sᴛᴏᴘ ᴀᴜᴛᴏ-ᴍsɢ" if enabled else "sᴛᴀʀᴛ ᴀᴜᴛᴏ-ᴍsɢ",
                "owner:automsg:toggle",
                EMOJI_CROSS if enabled else EMOJI_CHECK,
                "🛑" if enabled else "▶️",
                style="danger" if enabled else "success"
            ),
            btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="danger")
        ]
    ])

def progress_bar(current: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "░" * width
    filled = min(width, int(width * current / total))
    return "█" * filled + "░" * (width - filled)

def progress_text(sent: int, failed: int, total: int, credits: int = None, speed_label: str = "⚡ MEDIUM") -> str:
    bar = progress_bar(sent + failed, total)
    percent = int(((sent + failed) / total) * 100) if total > 0 else 0
    lines = [
        f"{em(EMOJI_WARNING, '⏳')} <b>{sc('sending sms...')}</b>\n",
        f"{bar} <b>{percent}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ: <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ: <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss: <b>{sent + failed}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ: <b>{speed_label}</b>\n",
    ]
    if credits is not None:
        lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs ʟᴇғᴛ: <b>{credits}</b>")
    lines.append(f"\n<i>{em(EMOJI_WARNING, '🛑')} sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀʏᴇɪɴ ᴀɢᴀʀ ʙᴇᴇᴄʜ ᴍᴇɪɴ ʀᴏᴋɴᴀ ʜᴏ.</i>")
    return "\n".join(lines)

def stop_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")]
    ])

def mask_number(number: str) -> str:
    if len(number) <= 4:
        return number
    return number[:2] + "******" + number[-4:]

def fmt_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

def fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"

def get_scan_status() -> str:
    global SCAN_STATUS, CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS

    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."

    if not CACHED_DEVICES:
        return f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs"

    device_count = len(CACHED_DEVICES)
    time_diff = time.time() - LAST_SCAN_TIME

    if time_diff < 60:
        return f"{em(EMOJI_CHECK, '🟢')} {device_count} ᴅᴇᴠɪᴄᴇs"
    elif time_diff < 300:
        return f"{em(EMOJI_WARNING, '🟡')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff/60)}ᴍ ᴏʟᴅ)"
    else:
        return f"{em(EMOJI_CROSS, '🔴')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff/60)}ᴍ ᴏʟᴅ)"

async def execute_auto_message_cycle(bot: Bot) -> tuple[bool, str]:
    """Send auto message to ALL users (DM) and delete each user's previous auto message."""
    d = load()
    cfg = d.get("auto_msg", {})
    text_body = (cfg.get("text") or "").strip()
    interval_min = max(1, int(cfg.get("interval_minutes", 5)))
    last_msg_ids = dict(cfg.get("last_msg_ids") or {})

    if not text_body:
        return False, "Message set nahi hai!"

    user_ids = [int(u) for u in d.get("users", {}).keys() if not is_banned(int(u), d)]
    if not user_ids:
        return False, "Koi user nahi mila!"

    sent_count = 0
    failed_count = 0
    new_last_ids = dict(last_msg_ids)

    for uid in user_ids:
        prev_mid = last_msg_ids.get(str(uid))
        if prev_mid:
            try:
                await bot.delete_message(chat_id=uid, message_id=int(prev_mid))
            except Exception:
                pass
        try:
            m = await bot.send_message(
                chat_id=uid,
                text=(
                    f"{em(EMOJI_BELL, '🔔')} <b>{sc('auto update')}</b> "
                    f"<i>({interval_min} {sc('min')})</i>\n\n{text_body}"
                ),
                parse_mode="HTML"
            )
            new_last_ids[str(uid)] = m.message_id
            sent_count += 1
        except Exception:
            failed_count += 1
        await asyncio.sleep(0.04)

    d = load()
    d.setdefault("auto_msg", {})["last_msg_ids"] = new_last_ids
    d["auto_msg"]["last_sent_at"] = int(time.time())
    save(d)
    return sent_count > 0, f"Users Sent: {sent_count} | Failed: {failed_count}"

async def auto_message_loop(bot: Bot):
    global AUTO_MSG_WORKER_STARTED
    if AUTO_MSG_WORKER_STARTED:
        return
    AUTO_MSG_WORKER_STARTED = True
    log.info("Auto-Message Scheduler Loop (All Users DM) STARTED")
    while True:
        try:
            d = load()
            cfg = d.get("auto_msg", {})
            interval_sec = max(1, int(cfg.get("interval_minutes", 5))) * 60
            await asyncio.sleep(interval_sec)

            d = load()
            cfg = d.get("auto_msg", {})
            if cfg.get("enabled") and (cfg.get("text") or "").strip():
                ok, info = await execute_auto_message_cycle(bot)
                log.info(f"[AUTO-MSG-USERS] ok={ok} info={info}")
        except Exception as e:
            log.error(f"[AUTO-MSG-USERS] loop error: {e}")
            await asyncio.sleep(15)

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
                    "last_update": int(time.time())
                }
            LAST_SCAN_TIME = time.time()

            DEVICE_HEALTH_LOG.append({
                "timestamp": int(time.time()),
                "devices_found": len(devices),
                "dbs_scanned": len(fbs),
                "duration_sec": round(scan_duration, 2),
                "status": "healthy" if devices else "no_devices"
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
                            f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('background scanner active!')}</b>\n"
                            f"📱 Devices: <b>{len(devices)}</b> | 🔥 DBs: <b>{len(fbs)}</b>",
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        log.warning(f"Owner notify failed: {e}")
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

def get_cached_devices() -> list:
    return CACHED_DEVICES

async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    url = base_url.rstrip("/") + path
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if 200 <= r.status < 300:
                        return True
        except Exception as e:
            log.warning(f"fb_put attempt {attempt+1}: {e}")
        await asyncio.sleep(0.2 * (attempt + 1))
    return False

def device_is_online(device_data: dict) -> bool:
    return any([
        device_data.get("isOnline"),
        device_data.get("online"),
        device_data.get("connected"),
        device_data.get("status") in ("online", "active", True, 1)
    ])

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    current_fb_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]

    _dev_sem = asyncio.Semaphore(25)

    async def fetch_one(fb: dict):
        shallow_url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(shallow_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
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
                                async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r2:
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
                        except Exception as e:
                            log.warning(f"Device fetch {dev_id}: {e}")
                        return None

                    dev_ids = list(device_ids.keys())
                    for i in range(0, len(dev_ids), 30):
                        batch = dev_ids[i:i+30]
                        dev_results = await asyncio.gather(*(fetch_dev(did) for did in batch))
                        for res in dev_results:
                            if res:
                                results.append(res)
        except Exception as e:
            log.warning(f"fb_shallow_get {fb['url']}: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

async def send_sms_via_device(fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    return await fb_put(
        fb_url,
        f"/clients/{dev_id}/webhookEvent/sendSms.json",
        {
            "from": sim_slot,
            "to": to.strip(),
            "message": message.strip(),
            "isSended": False,
            "timestamp": int(time.time())
        }
    )

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

    channels = fj.get("channels", [])
    missing = []
    for ch in channels:
        if ch.get("required", True):
            if not await check_membership(bot, uid, ch["id"]):
                missing.append(ch)
    return len(missing) == 0, missing

def force_join_text(missing: list) -> str:
    lines = [
        f"{em(EMOJI_CROSS, '⛔')} <b>{sc('bot use karne ke liye pehle join karein!')}</b>\n\n",
        f"{em(EMOJI_BELL, '👇')} ɴɪᴄʜᴇ ᴅɪʏᴇ ɢᴀʏᴇ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:"
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join karne ke baad /start karein ya refresh dabayein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in missing:
        rows.append([btn_url(f"ᴊᴏɪɴ {ch.get('title', 'Channel')}", ch["link"], EMOJI_BELL, "🔔", style="success")])
    rows.append([btn("ʀᴇғʀᴇsʜ / ᴄʜᴇᴄᴋ", "fj:check", EMOJI_GEAR, "🔄", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    videos = d.get("videos", [])
    prem_active = sum(1 for u_id in d.get("premium_users", {}) if is_premium(int(u_id), d))
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ ʀᴇǫᴜɪʀᴇᴅ"
    fj = d.get("force_join", {})
    fj_status = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    am = d.get("auto_msg", {})
    am_status = f"{em(EMOJI_CHECK, '🟢')} {am.get('interval_minutes', 5)}ᴍ (ᴜsᴇʀs)" if am.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    fb_lines = []
    for fb_id, fb_data in list(FB_DEVICE_COUNTS.items())[:12]:
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {fb_data['label'][:18]}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    protected_count = len(PROTECTED_NUMBERS)

    txt = (
        f"{em(EMOJI_CROWN, '👑')} <b>{sc('owner panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍɪɴs  : <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs        : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_STAR, '💎')} ᴘʀᴇᴍɪᴜᴍ      : <b>{prem_active}</b>\n"
        f"{em(EMOJI_STAR, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs        : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs  : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_BELL, '📢')} ᴀᴜᴛᴏ-ᴍsɢ      : {am_status}\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {mode}\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ    : {fj_status}\n"
        f"{em(EMOJI_MONEY, '💳')} ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs : <b>{len(d.get('pricing', {}).get('plans', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ     : <b>{protected_count}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} ᴘᴇʀ ғɪʀᴇʙᴀsᴇ  :\n{fb_summary}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ       : {scan_info}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return txt[:3850] + "\n<i>...trimmed</i>" if len(txt) > 3900 else txt

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {})
    stats = d.get("stats", {})
    banned = d.get("banned", [])
    videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ ʀᴇǫᴜɪʀᴇᴅ"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    fb_lines = []
    for fb_id, fb_data in list(FB_DEVICE_COUNTS.items())[:10]:
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {fb_data['label'][:18]}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    protected_count = len(PROTECTED_NUMBERS)

    txt = (
        f"{em(EMOJI_SHIELD, '🛡')} <b>{sc('admin panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs        : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CROSS, '🚫')} ʙᴀɴɴᴇᴅ        : <b>{len(banned)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs  : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(d.get('firebases', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ     : <b>{protected_count}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} ᴘᴇʀ ғɪʀᴇʙᴀsᴇ  :\n{fb_summary}\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {mode}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ       : {scan_info}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return txt[:3850] + "\n<i>...trimmed</i>" if len(txt) > 3900 else txt

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    credits = udata.get("credits", 0)
    scan_info = get_scan_status()
    prem = get_premium_record(uid, d)
    prem_line = f"{em(EMOJI_CROWN, '💎')} ᴘʀᴇᴍɪᴜᴍ : <b>{fmt_time(int(prem['expires_at']))}</b>\n" if prem else ""

    return (
        f"{em(EMOJI_PHONE, '📱')} <b>sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}</b>\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"{em(EMOJI_STAR, '👤')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{prem_line}"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{credits}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs    : <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs    : <b>{len(fbs)}</b> ғɪʀᴇʙᴀsᴇ(s)\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {scan_info}\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    free_on = bool(d.get("free_mode"))
    mode_btn = btn(
        "ᴅɪsᴀʙʟᴇ ғʀᴇᴇ ᴍᴏᴅᴇ" if free_on else "ᴇɴᴀʙʟᴇ ғʀᴇᴇ ᴍᴏᴅᴇ",
        "owner:free:off" if free_on else "owner:free:on",
        EMOJI_CROSS if free_on else EMOJI_CHECK,
        "🔴" if free_on else "🟢",
        style="danger" if free_on else "success"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤", style="danger"),
            btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary")
        ],
        [
            btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"),
            btn("ᴍᴀɴᴀɢᴇ sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑", style="primary")
        ],
        [
            btn("ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡", style="primary"),
            btn("ᴠɪᴇᴡ ᴜsᴇʀs", "owner:users:list", EMOJI_STAR, "👥", style="primary")
        ],
        [
            btn("ʙᴀɴ ᴜsᴇʀ", "owner:ban", EMOJI_CROSS, "🚫", style="danger"),
            btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "owner:unban:menu", EMOJI_CHECK, "✅", style="success")
        ],
        [
            btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "owner:broadcast", EMOJI_BELL, "📢", style="primary"),
            btn("ᴀᴘɪ sᴛᴀᴛs", "owner:stats", EMOJI_STAR, "📊", style="primary")
        ],
        [
            btn("ᴀᴄᴛɪᴠɪᴛɪ ʟᴏɢ", "owner:activity", EMOJI_GEAR, "📜", style="primary"),
            btn("ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs", "owner:prem:plans", EMOJI_CROWN, "💎", style="success")
        ],
        [
            btn("ɢɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ", "owner:prem:give", EMOJI_GIFT, "🎁", style="success"),
            btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰", style="success")
        ],
        [
            btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💰", style="danger"),
            btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰", style="success")
        ],
        [
            btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "💰", style="danger"),
            btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗", style="primary")
        ],
        [
            btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️", style="primary"),
            btn("ᴀᴜᴛᴏ-ᴍsɢ (ᴜsᴇʀs)", "owner:automsg:menu", EMOJI_BELL, "⏱", style="success")
        ],
        [
            btn("ᴇxᴘᴏʀᴛ ᴅʙ", "owner:db:export", EMOJI_GEAR, "📤", style="primary"),
            btn("ɪᴍᴘᴏʀᴛ ᴅʙ", "owner:db:import", EMOJI_CHECK, "📥", style="success")
        ],
        [
            btn("ᴇxᴘᴏʀᴛ sᴄʀɪᴘᴛ", "owner:export_script", EMOJI_GEAR, "📤", style="danger"),
            btn("ᴘʀᴏᴛᴇᴄᴛ ɴᴜᴍʙᴇʀ", "owner:protect", EMOJI_LOCK, "🔒", style="danger")
        ],
        [
            btn("ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐", style="primary"),
            btn("ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ", "owner:track", EMOJI_STAR, "📊", style="primary")
        ],
        [
            btn("ᴘɪɴɢ", "bot:ping", EMOJI_ROCKET, "🏓", style="success"),
            btn("ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs", "owner:pricing:menu", EMOJI_MONEY, "💳", style="primary")
        ],
        [mode_btn],
        [btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "📤", style="danger"),
            btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary")
        ],
        [
            btn("ᴠɪᴇᴡ ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥", style="primary"),
            btn("ᴀᴘɪ sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊", style="primary")
        ],
        [
            btn("ʙᴀɴ ᴜsᴇʀ", "admin:ban", EMOJI_CROSS, "🚫", style="danger"),
            btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "admin:unban:menu", EMOJI_CHECK, "✅", style="success")
        ],
        [
            btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢", style="primary"),
            btn("ᴘɪɴɢ", "bot:ping", EMOJI_ROCKET, "🏓", style="success")
        ],
        [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤", style="success")],
        [
            btn("📹 ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹", style="primary"),
            btn("ᴘʀᴇᴍɪᴜᴍ", "user:prem:plans", EMOJI_CROWN, "💎", style="success")
        ],
        [
            btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳", style="primary"),
            btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁", style="primary")
        ],
        [
            btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥", style="primary"),
            btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊", style="primary")
        ],
        [
            btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰", style="success"),
            btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸", style="primary")
        ],
        [
            btn("ᴘɪɴɢ", "bot:ping", EMOJI_ROCKET, "🏓", style="primary"),
            btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️", style="primary")
        ],
    ])
R = Router()

# ========== START, /ADMIN & FORCE JOIN ==========

async def _send_panel_by_role(bot: Bot, chat_id: int, uid: int, d: dict, reply_to_msg: Message | None = None):
    target = reply_to_msg.answer if reply_to_msg else (lambda *a, **kw: bot.send_message(chat_id, *a, **kw))

    if is_owner(uid, d):
        await target(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await target(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await target(
            f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>\nAdmin se contact karein.",
            parse_mode="HTML"
        )
        return
    if not can_use(uid, d):
        await target(
            f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nPremium ya approval lein.",
            reply_markup=premium_plans_kb("user:home"),
            parse_mode="HTML"
        )
        return

    await target(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

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

    if code.startswith("REF"):
        if not d["users"].get(str(uid), {}).get("referred_by"):
            success, _, referrer = process_referral(uid, code, d)
            if success and referrer:
                try:
                    ref_name = d["users"].get(str(uid), {}).get("name", "Someone")
                    await msg.bot.send_message(
                        referrer,
                        f"{em(EMOJI_GIFT, '🎉')} <b>{ref_name}</b> ne aapka referral code use kiya!\n"
                        f"{em(EMOJI_MONEY, '💰')} Aapko +{d['settings']['ref_credits']} credits mile hain.\n"
                        f"{em(EMOJI_MONEY, '💰')} Unko bhi +{d['settings']['ref_credits']} credits mile hain.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
    save(d)

    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    await send_random_video(
        msg.bot,
        msg.chat.id,
        caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}"
    )
    await _send_panel_by_role(msg.bot, msg.chat.id, uid, d, reply_to_msg=msg)

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
        await msg.answer(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    await send_random_video(
        msg.bot,
        msg.chat.id,
        caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}"
    )
    await _send_panel_by_role(msg.bot, msg.chat.id, uid, d, reply_to_msg=msg)

@R.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    d = load()
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    await msg.answer(
        f"{em(EMOJI_CROSS, '🚫')} <b>Admin access nahi hai!</b>",
        parse_mode="HTML"
    )

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    d = load()
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("❌ Abhi bhi join nahi kiya!", show_alert=True)
        try:
            await cq.message.edit_text(
                force_join_text(missing),
                reply_markup=force_join_kb(missing),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except Exception:
            pass
        return

    await cq.answer("✅ Verified!", show_alert=True)
    await _send_panel_by_role(cq.bot, cq.message.chat.id, uid, d, reply_to_msg=cq.message)

# ========== PING HANDLER ==========

@R.callback_query(F.data == "bot:ping")
@R.message(Command("ping"))
async def handle_ping(event: CallbackQuery | Message):
    t0 = time.perf_counter()
    load()
    devices = get_cached_devices()
    db_ms = round((time.perf_counter() - t0) * 1000, 2)

    t1 = time.perf_counter()
    try:
        await event.bot.get_me()
    except Exception:
        pass
    api_ms = round((time.perf_counter() - t1) * 1000, 2)

    active_sends = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    txt = (
        f"{em(EMOJI_ROCKET, '🏓')} <b>{sc('pong! bot alive')}</b>\n\n"
        f"{em(EMOJI_STAR, '⚡')} <b>TG API Ping:</b> <code>{api_ms} ms</code>\n"
        f"{em(EMOJI_GEAR, '💾')} <b>Local DB Read:</b> <code>{db_ms} ms</code>\n"
        f"{em(EMOJI_FIRE, '🔥')} <b>Online Devices:</b> <b>{len(devices)}</b>\n"
        f"{em(EMOJI_CHECK, '🚀')} <b>Active Blasts:</b> <b>{active_sends}</b>\n"
        f"{em(EMOJI_MONEY, '🏎')} <b>Default Speed:</b> <b>MEDIUM ({SPEED_MEDIUM}s)</b>"
    )
    if isinstance(event, CallbackQuery):
        await event.answer(f"🏓 Pong! API: {api_ms}ms | DB: {db_ms}ms", show_alert=True)
        try:
            await event.message.answer(txt, parse_mode="HTML")
        except Exception:
            pass
    else:
        await event.answer(txt, parse_mode="HTML")

# ========== PREMIUM PLANS & GIVE PREMIUM ==========

def _premium_plans_summary_text() -> str:
    lines = [
        f"{em(EMOJI_CROWN, '💎')} <b>{sc('premium membership plans')}</b>\n"
    ]
    for p in PREMIUM_PLANS:
        lines.append(
            f"• <b>{p['title']}</b> — <b>₹{p['price']}</b> "
            f"<i>({p['days']}d access)</i>"
        )
    lines.append(
        f"\n{em(EMOJI_BELL, '📩')} <i>Plan select karein ya Owner {SUPER_ADMIN_NAME} se contact karein.</i>"
    )
    return "\n".join(lines)

@R.callback_query(F.data == "user:prem:plans")
async def user_prem_plans(cq: CallbackQuery):
    await cq.message.edit_text(
        _premium_plans_summary_text(),
        reply_markup=premium_plans_kb("user:home"),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:prem:plans")
async def owner_prem_plans(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.message.edit_text(
        _premium_plans_summary_text(),
        reply_markup=premium_plans_kb("owner:home"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("prem:buy:"))
async def prem_buy_select(cq: CallbackQuery):
    plan_id = cq.data.split("prem:buy:", 1)[1]
    plan = next((p for p in PREMIUM_PLANS if p["id"] == plan_id), None)
    if not plan:
        await cq.answer("❌ Plan not found!", show_alert=True)
        return

    uid = cq.from_user.id
    uname = f"@{cq.from_user.username}" if cq.from_user.username else "No Username"
    await cq.answer(f"💎 {plan['title']} — ₹{plan['price']}", show_alert=True)

    notify_owner = (
        f"💎 <b>NEW PREMIUM REQUEST</b>\n\n"
        f"👤 <b>User:</b> {cq.from_user.full_name} ({uname})\n"
        f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
        f"📦 <b>Plan:</b> <b>{plan['title']}</b> — <b>₹{plan['price']}</b>"
    )
    try:
        await cq.bot.send_message(MAIN_OWNER, notify_owner, parse_mode="HTML")
    except Exception:
        pass

    await cq.message.answer(
        f"{em(EMOJI_CROWN, '💎')} <b>Selected Plan: {plan['title']} (₹{plan['price']})</b>\n\n"
        f"Payment & activation ke liye Owner se contact karein: {SUPER_ADMIN_NAME}\n"
        f"Aapki User ID: <code>{uid}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [btn_url("ᴄᴏɴᴛᴀᴄᴛ ᴏᴡɴᴇʀ", SUPER_ADMIN_LINK, EMOJI_CROWN, "👑", style="success")],
            [btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="danger")]
        ]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:prem:give")
async def owner_give_prem_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.give_prem_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Give Premium (Step 1/2)</b>\n\n"
        f"Jisko premium dena hai uska <b>User ID</b> bhejo:\n"
        f"<i>Example: 123456789</i>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.give_prem_uid)
async def owner_give_prem_uid(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        target_uid = int(msg.text.strip())
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid numeric User ID bhejo.", parse_mode="HTML")
        return

    await state.update_data(prem_target_uid=target_uid)
    await state.set_state(S.give_prem_duration)
    await msg.answer(
        f"{em(EMOJI_CROWN, '💎')} <b>Give Premium to <code>{target_uid}</code> (Step 2/2)</b>\n\n"
        f"Kitne <b>din</b> ya kitne <b>ghante</b> ka premium dena hai?\n"
        f"• Days ke liye: <code>1d</code>, <code>3d</code>, <code>7d</code>, <code>30d</code> ya <code>5</code>\n"
        f"• Hours ke liye: <code>6h</code>, <code>12h</code>, <code>24h</code>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.give_prem_duration)
async def owner_give_prem_duration(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return

    parsed = parse_duration_input(msg.text)
    if not parsed:
        await msg.answer(
            f"{em(EMOJI_CROSS, '❌')} Invalid duration! Example: <code>7d</code>, <code>12h</code>, ya <code>3</code>",
            parse_mode="HTML"
        )
        return

    seconds, dur_label = parsed
    data_fsm = await state.get_data()
    target_uid = int(data_fsm.get("prem_target_uid"))
    await state.clear()

    expires_at = grant_user_premium(target_uid, seconds, dur_label, uid, d)
    log_activity(d, "grant_premium", uid, f"Gave {dur_label} premium to {target_uid}")
    save(d)

    exp_str = fmt_time(expires_at)
    try:
        await msg.bot.send_message(
            target_uid,
            f"{em(EMOJI_CROWN, '💎')} <b>Premium Activated!</b>\n\n"
            f"⏱ <b>Duration:</b> <b>{dur_label}</b>\n"
            f"📅 <b>Valid Till:</b> <b>{exp_str}</b>\n\n"
            f"Ab /start karke bot use karein!",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Premium Granted!</b>\n\n"
        f"🆔 <b>User ID:</b> <code>{target_uid}</code>\n"
        f"⏱ <b>Duration:</b> <b>{dur_label}</b>\n"
        f"📅 <b>Expires At:</b> <b>{exp_str}</b>",
        reply_markup=owner_kb(d),
        parse_mode="HTML"
    )

# ========== DATABASE EXPORT & IMPORT ==========

@R.callback_query(F.data == "owner:db:export")
async def owner_db_export(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("📤 Exporting DB...")
    raw_bytes = json.dumps(d, indent=2, ensure_ascii=False).encode("utf-8")
    doc = BufferedInputFile(raw_bytes, filename=f"backup_{_DATA_FILE}")
    await cq.message.reply_document(
        document=doc,
        caption=(
            f"{em(EMOJI_GEAR, '📤')} <b>Database Exported</b>\n"
            f"Users: <b>{len(d.get('users', {}))}</b> | "
            f"Firebases: <b>{len(d.get('firebases', []))}</b>"
        ),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:db:import")
async def owner_db_import_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.import_db_file)
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, '📥')} <b>Import Database (.json)</b>\n\n"
        f"Apni purani database <code>.json</code> file yahan upload karein.",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.import_db_file, F.document)
async def owner_db_import_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return

    doc = msg.document
    if not doc.file_name.lower().endswith(".json"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <code>.json</code> database file bhejein!", parse_mode="HTML")
        return

    try:
        file_info = await msg.bot.get_file(doc.file_id)
        buf = await msg.bot.download_file(file_info.file_path)
        imported = json.loads(buf.read().decode("utf-8"))
        if not isinstance(imported, dict):
            raise ValueError("Root must be JSON object")
    except Exception as e:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid JSON file: <code>{e}</code>", parse_mode="HTML")
        return

    merged = deepcopy(d)
    for key in ["users", "premium_users", "redeem_codes", "sms_history", "protected_numbers"]:
        if isinstance(imported.get(key), dict):
            merged.setdefault(key, {}).update(imported[key])

    for list_key in ["admins", "banned", "approved", "videos"]:
        if isinstance(imported.get(list_key), list):
            existing = set(merged.get(list_key, []))
            for item in imported[list_key]:
                if item not in existing:
                    merged.setdefault(list_key, []).append(item)

    if isinstance(imported.get("firebases"), list):
        seen_urls = {fb.get("url", "").rstrip("/") for fb in merged.get("firebases", [])}
        for fb in imported["firebases"]:
            u = fb.get("url", "").rstrip("/")
            if u and u not in seen_urls:
                seen_urls.add(u)
                merged.setdefault("firebases", []).append(fb)

    if isinstance(imported.get("owners"), list):
        for oid in imported["owners"]:
            if oid not in merged["owners"] and len(merged["owners"]) < 6:
                merged["owners"].append(oid)
    if MAIN_OWNER not in merged["owners"]:
        merged["owners"].insert(0, MAIN_OWNER)

    if isinstance(imported.get("stats"), dict):
        merged["stats"]["total_sent"] = max(
            merged["stats"].get("total_sent", 0),
            imported["stats"].get("total_sent", 0)
        )
        merged["stats"]["total_failed"] = max(
            merged["stats"].get("total_failed", 0),
            imported["stats"].get("total_failed", 0)
        )

    log_activity(merged, "db_import", uid, f"Imported {doc.file_name}")
    save(merged)
    await state.clear()

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Database Imported Successfully!</b>\n\n"
        f"👥 <b>Total Users:</b> <b>{len(merged.get('users', {}))}</b>\n"
        f"🔥 <b>Total Firebases:</b> <b>{len(merged.get('firebases', []))}</b>",
        reply_markup=owner_kb(merged),
        parse_mode="HTML"
    )

@R.message(S.import_db_file)
async def owner_db_import_invalid(msg: Message):
    await msg.answer(f"{em(EMOJI_CROSS, '❌')} Kripya <code>.json</code> file upload karein.", parse_mode="HTML")

# ========== AUTO-SEND TO ALL USERS + DELETE PREVIOUS MESSAGE LOOP ==========

def _auto_msg_panel_text(d: dict) -> str:
    cfg = d.get("auto_msg", {})
    status = f"{em(EMOJI_CHECK, '🟢')} <b>ACTIVE</b>" if cfg.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} <b>STOPPED</b>"
    mins = int(cfg.get("interval_minutes", 5))
    msg_txt = cfg.get("text") or "<i>Not Set</i>"
    tracked_users = len(cfg.get("last_msg_ids") or {})
    total_users = len(d.get("users", {}))
    return (
        f"{em(EMOJI_BELL, '⏱')} <b>{sc('auto message to all users')}</b>\n\n"
        f"• <b>Status:</b> {status}\n"
        f"• <b>Target:</b> <b>All Users (DM)</b> ({total_users} users)\n"
        f"• <b>Interval:</b> every <b>{mins}</b> minute(s)\n"
        f"• <b>Tracked Prev Msgs:</b> <b>{tracked_users}</b>\n"
        f"• <b>Message:</b>\n<blockquote>{msg_txt[:300]}</blockquote>"
    )

@R.callback_query(F.data == "owner:automsg:menu")
async def owner_automsg_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.clear()
    await cq.message.edit_text(_auto_msg_panel_text(d), reply_markup=auto_msg_kb(), parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^owner:automsg:min:(5|10)$"))
async def owner_automsg_preset_min(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    mins = int(cq.data.split(":")[-1])
    d.setdefault("auto_msg", {})["interval_minutes"] = mins
    save(d)
    await cq.answer(f"⏱ Har {mins} minute mein sab users ke paas jayega!", show_alert=True)
    await cq.message.edit_text(_auto_msg_panel_text(d), reply_markup=auto_msg_kb(), parse_mode="HTML")

@R.callback_query(F.data == "owner:automsg:min:custom")
async def owner_automsg_custom_min_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.auto_msg_custom_min)
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '⏱')} <b>Custom Minutes</b>\n\nKitne minutes ka interval chahiye? (e.g. <code>2</code>, <code>15</code>)",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:automsg:menu", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.auto_msg_custom_min)
async def owner_automsg_custom_min_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        mins = int(msg.text.strip())
        if mins < 1:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid number (>= 1) bhejein.", parse_mode="HTML")
        return
    d.setdefault("auto_msg", {})["interval_minutes"] = mins
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Interval set to <b>{mins}</b> minutes (All Users DM)!",
        reply_markup=auto_msg_kb(),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:automsg:setup")
async def owner_automsg_setup_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.auto_msg_text)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '📝')} <b>Set User Auto Message</b>\n\n"
        f"Jo message sab users ke paas bhejna hai woh text bhejein\n"
        f"<i>(Har baar naya aane par purana message automatically delete hoga)</i>:",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:automsg:menu", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.auto_msg_text)
async def owner_automsg_text_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    text_body = (msg.text or msg.caption or "").strip()
    if not text_body:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Khali message nahi ho sakta, text bhejein.", parse_mode="HTML")
        return

    d.setdefault("auto_msg", {})["text"] = text_body
    d["auto_msg"]["enabled"] = True
    save(d)
    await state.clear()

    ok, info = await execute_auto_message_cycle(msg.bot)
    d = load()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Auto-Message to All Users Started!</b> ({info}, ok={ok})\n\n"
        + _auto_msg_panel_text(d),
        reply_markup=auto_msg_kb(),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:automsg:toggle")
async def owner_automsg_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    cfg = d.setdefault("auto_msg", {})
    if not cfg.get("enabled") and not (cfg.get("text") or "").strip():
        await cq.answer("⚠️ Pehle 'Set User Msg' set karein!", show_alert=True)
        return
    cfg["enabled"] = not cfg.get("enabled", False)
    save(d)
    await cq.answer("🟢 Auto-Msg ON (Users)" if cfg["enabled"] else "🔴 Auto-Msg OFF", show_alert=True)
    await cq.message.edit_text(_auto_msg_panel_text(d), reply_markup=auto_msg_kb(), parse_mode="HTML")

@R.callback_query(F.data == "owner:automsg:now")
async def owner_automsg_now(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    ok, info = await execute_auto_message_cycle(cq.bot)
    d = load()
    await cq.answer(f"{'✅' if ok else '❌'} {info}", show_alert=True)
    try:
        await cq.message.edit_text(_auto_msg_panel_text(d), reply_markup=auto_msg_kb(), parse_mode="HTML")
    except TelegramBadRequest:
        pass

# ========== SMS BLAST FLOWS (DEFAULT MEDIUM: 0.2s) ==========

@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id

    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("⛔ Force Join compulsory hai!", show_alert=True)
        await cq.message.edit_text(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    if not can_use(uid, d):
        await cq.answer("💎 Premium ya approval chahiye!", show_alert=True)
        await cq.message.edit_text(
            _premium_plans_summary_text(),
            reply_markup=premium_plans_kb("user:home"),
            parse_mode="HTML"
        )
        return

    await state.set_state(S.send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo:", parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS:
        await msg.answer(f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{mask_number(number)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:cancel", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b> (Default: <b>MEDIUM</b>)",
        reply_markup=speed_kb("user"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    speed_map = {"user:speed:fast": SPEED_FAST, "user:speed:medium": SPEED_MEDIUM, "user:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.send_count)

    devices = get_cached_devices() or await get_all_online_devices(d)
    count = len(devices)
    credit_info = ""
    if not is_admin(uid, d) and not is_owner(uid, d) and not is_premium(uid, d):
        credit_info = f"\n{em(EMOJI_MONEY, '💰')} Your Credits: <b>{get_user_credits(uid, d)}</b>\n"

    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS{credit_info}\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:cancel", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo (e.g. 10):", parse_mode="HTML")
        return
    await state.clear()

    exempt_credits = is_admin(uid, d) or is_owner(uid, d) or is_premium(uid, d)
    if not exempt_credits:
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>Aapke paas credits nahi hain!</b>",
                reply_markup=premium_plans_kb("user:home"),
                parse_mode="HTML"
            )
            return
        if count > current_credits:
            count = current_credits

    devices = get_cached_devices() or await get_all_online_devices(d)
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=kb([("ʜᴏᴍᴇ", "user:home", "primary")]),
            parse_mode="HTML"
        )
        return

    await run_sms_blast_with_progress(
        msg.bot, msg, uid, fsmd.get("number", ""), fsmd.get("message", ""),
        count, devices, fsmd.get("send_speed", SPEED_MEDIUM)
    )

@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Super Admin SMS Send</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo:", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{number}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b> (Default: <b>MEDIUM</b>)",
        reply_markup=speed_kb("owner"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {"owner:speed:fast": SPEED_FAST, "owner:speed:medium": SPEED_MEDIUM, "owner:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.owner_send_count)
    devices = get_cached_devices() or await get_all_online_devices(load())
    count = len(devices)

    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo:", parse_mode="HTML")
        return
    await state.clear()
    devices = get_cached_devices() or await get_all_online_devices(load())
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi!",
            reply_markup=kb([("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", "primary")]),
            parse_mode="HTML"
        )
        return
    await run_sms_blast_with_progress(
        msg.bot, msg, msg.from_user.id, fsmd.get("number", ""), fsmd.get("message", ""),
        count, devices, fsmd.get("send_speed", SPEED_MEDIUM)
    )

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS Send</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo:", parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS:
        protector_uid = PROTECTED_NUMBERS[number]
        if not is_owner(msg.from_user.id, load()) and msg.from_user.id != protector_uid:
            await msg.answer(f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>", parse_mode="HTML")
            return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{mask_number(number)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b> (Default: <b>MEDIUM</b>)",
        reply_markup=speed_kb("admin"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {"admin:speed:fast": SPEED_FAST, "admin:speed:medium": SPEED_MEDIUM, "admin:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.admin_send_count)
    devices = get_cached_devices() or await get_all_online_devices(load())
    count = len(devices)

    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "admin:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo:", parse_mode="HTML")
        return
    await state.clear()
    devices = get_cached_devices() or await get_all_online_devices(load())
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi!",
            reply_markup=kb([("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", "primary")]),
            parse_mode="HTML"
        )
        return
    await run_sms_blast_with_progress(
        msg.bot, msg, msg.from_user.id, fsmd.get("number", ""), fsmd.get("message", ""),
        count, devices, fsmd.get("send_speed", SPEED_MEDIUM)
    )

async def run_sms_blast_with_progress(
    bot: Bot,
    msg: Message,
    uid: int,
    number: str,
    message: str,
    count: int,
    devices: list,
    speed: float = SPEED_DEFAULT
):
    await send_random_video(bot, msg.chat.id, caption=f"💣 <b>SMS Blast Started on {mask_number(number)}!</b>")

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old_session = USER_SESSIONS[uid]
            if old_session.task and not old_session.task.done():
                await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} <b>Ek sending already chal rahi hai!</b>", parse_mode="HTML")
                return
            del USER_SESSIONS[uid]

        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    d_init = load()
    is_regular_user = not (is_admin(uid, d_init) or is_owner(uid, d_init) or is_premium(uid, d_init))
    current_credits = get_user_credits(uid, d_init) if is_regular_user else None
    speed_label_display = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"

    try:
        progress_msg = await msg.answer(
            progress_text(0, 0, count, current_credits, speed_label_display),
            reply_markup=stop_send_kb(),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to send progress message: {e}")
        async with SESSIONS_LOCK:
            USER_SESSIONS.pop(uid, None)
        return

    sent_ok = 0
    sent_fail = 0
    msgs_left = count
    api_usage_delta = {}
    last_update_time = time.time()
    start_time = time.time()

    async def do_send():
        nonlocal sent_ok, sent_fail, msgs_left, last_update_time
        try:
            for device in devices:
                if msgs_left <= 0:
                    break
                async with session.lock:
                    if session.cancelled:
                        break

                fb_id = device["fb_id"]
                fb_url = device["fb_url"]
                dev_id = device["dev_id"]
                sims = device["sims"]
                sim_slots = [s.get("simSlotIndex", 0) for s in sims] if sims else [0]
                device_quota = min(3, msgs_left)
                device_sent = 0

                for sim in sim_slots:
                    async with session.lock:
                        if device_sent >= device_quota or msgs_left <= 0 or session.cancelled:
                            break

                    ok = await send_sms_via_device(fb_url, dev_id, sim, number, message)

                    async with session.lock:
                        if ok:
                            sent_ok += 1
                            device_sent += 1
                            msgs_left -= 1

                            if is_regular_user:
                                d_temp = load()
                                deduct_credits(uid, 1, d_temp)
                                d_temp["stats"]["total_sent"] = d_temp["stats"].get("total_sent", 0) + 1
                                k = str(uid)
                                if k in d_temp["users"]:
                                    d_temp["users"][k]["uses"] = d_temp["users"][k].get("uses", 0) + 1
                                d_temp.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                    "number": number,
                                    "message": message[:100],
                                    "timestamp": int(time.time()),
                                    "status": "sent"
                                })
                                save(d_temp)
                        else:
                            sent_fail += 1
                            msgs_left -= 1

                        if fb_id not in api_usage_delta:
                            api_usage_delta[fb_id] = {"sent": 0, "failed": 0}
                        api_usage_delta[fb_id]["sent" if ok else "failed"] += 1

                        now = time.time()
                        if (now - last_update_time >= _PROGRESS_UPDATE_INTERVAL or
                            (sent_ok + sent_fail) == count or
                            session.cancelled):
                            current_credits_live = get_user_credits(uid, load()) if is_regular_user else None
                            try:
                                await progress_msg.edit_text(
                                    progress_text(sent_ok, sent_fail, count, current_credits_live, speed_label_display),
                                    reply_markup=stop_send_kb() if not session.cancelled else None,
                                    parse_mode="HTML"
                                )
                            except TelegramBadRequest:
                                pass
                            last_update_time = now

                    await asyncio.sleep(speed)

        except Exception as e:
            log.error(f"Error in send loop for user {uid}: {e}")
        finally:
            async with session.lock:
                session.sent = sent_ok
                session.failed = sent_fail

    task = asyncio.create_task(do_send())
    session.task = task
    await task
    was_cancelled = session.cancelled

    async with SESSIONS_LOCK:
        USER_SESSIONS.pop(uid, None)

    d_final = load()
    if not is_regular_user:
        d_final["stats"]["total_sent"] = d_final["stats"].get("total_sent", 0) + sent_ok
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["sent"] += delta["sent"]
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
        k = str(uid)
        if k in d_final["users"]:
            d_final["users"][k]["uses"] = d_final["users"][k].get("uses", 0) + sent_ok
        d_final.setdefault("sms_history", {}).setdefault(str(uid), []).append({
            "number": number,
            "message": message[:100],
            "timestamp": int(time.time()),
            "status": "completed" if not was_cancelled else "stopped"
        })
    else:
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]

    duration = int(time.time() - start_time)
    log_activity(
        d_final,
        "sms_blast",
        uid,
        f"Sent: {sent_ok}, Failed: {sent_fail}, Total: {count}, Speed: {speed_label_display}, Duration: {fmt_duration(duration)}"
    )
    save(d_final)

    chan_log = (
        f"🚀 <b>SMS BLAST LOG</b>\n"
        f"🆔 <b>User:</b> <code>{uid}</code>\n"
        f"📞 <b>To:</b> <code>{number}</code>\n"
        f"✅ <b>Sent:</b> <b>{sent_ok}</b> | ❌ <b>Failed:</b> <b>{sent_fail}</b>\n"
        f"⚡ <b>Speed:</b> <b>{speed_label_display}</b> | ⏱ <b>{fmt_duration(duration)}</b>"
    )
    asyncio.create_task(send_channel_log(bot, chan_log))

    icon = em(EMOJI_CHECK, "✅") if (sent_fail == 0 and sent_ok > 0) else em(EMOJI_WARNING, "⚠️") if sent_ok > 0 else em(EMOJI_CROSS, "❌")
    credit_text = f"\n{em(EMOJI_MONEY, '💳')} Remaining Credits: <b>{get_user_credits(uid, load())}</b>" if is_regular_user else ""
    stopped_text = f"\n{em(EMOJI_CROSS, '🛑')} <b>Stopped!</b>" if was_cancelled else ""

    if is_owner(uid, load()):
        back_row = [btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    elif is_admin(uid, load()):
        back_row = [btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
    else:
        back_row = [
            btn("sᴇɴᴅ ᴀɢᴀɪɴ", "user:send", EMOJI_ROCKET, "📤", style="success"),
            btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")
        ]

    try:
        await progress_msg.edit_text(
            f"{icon} <b>SMS Blast Result</b>{stopped_text}\n\n"
            f"{em(EMOJI_PHONE, '📞')} To: <code>{mask_number(number)}</code>\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{sent_ok}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} Failed: <b>{sent_fail}</b>\n"
            f"{em(EMOJI_ROCKET, '⚡')} Speed: <b>{speed_label_display}</b>\n"
            f"{em(EMOJI_GEAR, '⏱')} Duration: <b>{fmt_duration(duration)}</b>"
            f"{credit_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_row]),
            parse_mode="HTML"
        )
    except Exception as e:
        log.error(f"Failed to edit final progress message: {e}")

@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await cq.answer("✅ Koi active sending nahi!", show_alert=True)
            return
        session.cancelled = True
    await cq.answer("🛑 Stop signal sent!", show_alert=True)

# ========== VIDEOS, PROTECT, TRACK, CREDITS, ADMIN & OWNER MENUS ==========

def videos_menu_kb(d: dict) -> InlineKeyboardMarkup:
    videos = d.get("videos", [])
    rows = [
        [btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕", style="success")],
        [btn("ʙᴜʟᴋ ᴅᴇʟᴇᴛᴇ ᴀʟʟ", "owner:videos:bulk_del", EMOJI_CROSS, "🗑", style="danger")]
    ]
    for idx, _ in enumerate(videos, 1):
        rows.append([
            btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx-1}", EMOJI_CROSS, "🗑", style="danger")
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>\n\nTotal Videos: <b>{len(d.get('videos', []))}</b>",
        reply_markup=videos_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.add_video)
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Add Video</b>\n\nVideo file ya URL/File ID bhejein:",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:videos:menu", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.add_video)
async def owner_videos_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    video_file_id = None
    if msg.video:
        video_file_id = msg.video.file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("video"):
        video_file_id = msg.document.file_id
    elif msg.text:
        video_file_id = msg.text.strip()
    if not video_file_id:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid Video send karein.", parse_mode="HTML")
        return
    d.setdefault("videos", []).append(video_file_id)
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} <b>Video Saved!</b>", reply_markup=videos_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    idx = int(cq.data.split("owner:videos:del:", 1)[1])
    videos = d.get("videos", [])
    if 0 <= idx < len(videos):
        videos.pop(idx)
        d["videos"] = videos
        save(d)
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>\n\nTotal Videos: <b>{len(d.get('videos', []))}</b>",
        reply_markup=videos_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    d["videos"] = []
    save(d)
    await cq.answer("🗑 All Videos Deleted!", show_alert=True)
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>\n\nTotal Videos: <b>0</b>",
        reply_markup=videos_menu_kb(d),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery):
    if not load().get("videos"):
        await cq.answer("❌ Koi video available nahi hai!", show_alert=True)
        return
    await cq.answer("📹 Sending video...")
    await send_random_video(cq.bot, cq.message.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!")

@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.protect_number)
    await cq.message.edit_text(
        f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\nNumber enter karein:",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number.", parse_mode="HTML")
        return
    PROTECTED_NUMBERS[number] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS
    log_activity(d, "number_protected", uid, f"Protected {number}")
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_LOCK, '🔒')} Protected: <code>{number}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.message.edit_text(f"{em(EMOJI_LOCK, '🔐')} <i>Koi number protected nahi hai.</i>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")
        return
    lines = [f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers</b>\n"]
    for num, p_uid in protected.items():
        disp = num if is_owner(uid, d) else mask_number(num)
        lines.append(f"• <code>{disp}</code> — by <code>{p_uid}</code>")
    rows = []
    if is_owner(uid, d):
        rows.append([btn("ʀᴇᴍᴏᴠᴇ", "owner:protected_remove", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    protected = d.get("protected_numbers", {})
    rows = [[btn(num, f"owner:protected_del:{num}", EMOJI_CROSS, "🗑", style="danger")] for num in protected]
    rows.append([btn("ʙᴀᴄᴋ", "owner:protected_list", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(f"{em(EMOJI_CROSS, '🗑')} <b>Remove Protected Number</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    num = cq.data.split("owner:protected_del:", 1)[1]
    d.get("protected_numbers", {}).pop(num, None)
    PROTECTED_NUMBERS.pop(num, None)
    save(d)
    await cq.answer("✅ Removed!", show_alert=True)
    await owner_protected_list(cq)

@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.track_number)
    await cq.message.edit_text(f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\nNumber enter karein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]), parse_mode="HTML")

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    number = msg.text.strip()
    await state.clear()
    matched = []
    for uid_str, hist in d.get("sms_history", {}).items():
        for entry in hist:
            if entry.get("number") == number:
                uname = d.get("users", {}).get(uid_str, {}).get("name", "Unknown")
                matched.append(f"• <code>{uid_str}</code> ({uname}) — {fmt_time(entry.get('timestamp', 0))}")
                break
    body = "\n".join(matched) if matched else "<i>Koi record nahi mila.</i>"
    await msg.answer(f"{em(EMOJI_STAR, '📊')} <b>Tracker: <code>{number}</code></b>\n\n{body}", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Add Credits to ALL Users</b>\n\nAmount bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]), parse_mode="HTML")

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amt = int(msg.text.strip())
        if amt <= 0:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejein.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    for u_str in users:
        add_credits(int(u_str), amt, d)
    log_activity(d, "add_credits_all", uid, f"+{amt} to {len(users)} users")
    save(d)
    for u_str in users:
        try:
            await msg.bot.send_message(int(u_str), f"{em(EMOJI_MONEY, '💰')} Aapko <b>+{amt}</b> credits mile hain!", parse_mode="HTML")
            await asyncio.sleep(0.04)
        except Exception:
            pass
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Added <b>{amt}</b> to <b>{len(users)}</b> users.", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits from ALL Users</b>\n\nAmount bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]), parse_mode="HTML")

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amt = int(msg.text.strip())
        if amt <= 0:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejein.", parse_mode="HTML")
        return
    await state.clear()
    count = 0
    for u_str, udata in d.get("users", {}).items():
        if is_admin(int(u_str), d):
            continue
        udata["credits"] = max(0, udata.get("credits", 0) - amt)
        count += 1
    log_activity(d, "deduct_credits_all", uid, f"-{amt} from {count} users")
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Deducted up to <b>{amt}</b> from <b>{count}</b> users.", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if is_banned(uid, d) or not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    cur = get_user_credits(uid, d)
    if cur < 2:
        await cq.answer("❌ Minimum 2 credits chahiye!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💸')} <b>Transfer Credits</b>\nBalance: <b>{cur}</b> (Max: <b>{cur//2}</b>)\n\nTarget User ID bhejein:",
        reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:home", "danger")]),
        parse_mode="HTML"
    )

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load()
    try:
        target = int(msg.text.strip())
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid User ID bhejein.", parse_mode="HTML")
        return
    if target == msg.from_user.id or str(target) not in d.get("users", {}):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid target user.", parse_mode="HTML")
        return
    await state.update_data(transfer_target=target)
    await state.set_state(S.transfer_credits_amount)
    half = get_user_credits(msg.from_user.id, d) // 2
    await msg.answer(f"Kitne credits transfer karne hain? (Max <b>{half}</b>):", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:home", "danger")]), parse_mode="HTML")

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        amt = int(msg.text.strip())
        if amt <= 0:
            raise ValueError
    except ValueError:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid number bhejein.", parse_mode="HTML")
        return
    target = int((await state.get_data()).get("transfer_target"))
    max_amt = get_user_credits(uid, d) // 2
    if amt > max_amt or not deduct_credits(uid, amt, d):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Max transfer <b>{max_amt}</b> hai.", parse_mode="HTML")
        return
    add_credits(target, amt, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(target, f"{em(EMOJI_MONEY, '💸')} Received <b>{amt}</b> credits from <code>{uid}</code>.", parse_mode="HTML")
    except Exception:
        pass
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Transferred <b>{amt}</b> credits to <code>{target}</code>!", reply_markup=kb([("ʜᴏᴍᴇ", "user:home", "primary")]), parse_mode="HTML")

# ========== OWNER & ADMIN PANEL ACTIONS ==========

@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

def fb_menu_kb(d: dict, page: int = 0) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    per_page = 8
    total_pages = max(1, (len(fbs) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    current_fbs = fbs[page * per_page:(page + 1) * per_page]
    rows = [[
        btn("ᴀᴅᴅ ғɪʀᴇʙᴀsᴇ", "owner:fb:add", EMOJI_CHECK, "➕", style="success"),
        btn("ᴀᴅᴅ ᴠɪᴀ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄", style="primary")
    ]]
    for fb in current_fbs:
        label = fb.get("label", fb["url"].replace("https://", ""))[:16]
        rows.append([
            btn(label, "noop", EMOJI_FIRE, "🔥", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑", style="danger")
        ])
    nav = []
    if page > 0:
        nav.append(btn("◀️ ᴘʀᴇᴠ", f"owner:fb:menu:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if page < total_pages - 1:
        nav.append(btn("ɴᴇxᴛ ▶️", f"owner:fb:menu:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.clear()
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b>", reply_markup=fb_menu_kb(d, page), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Add Firebase</b>\n\nFormat: <code>Label | https://xxx.firebaseio.com</code>", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:fb:menu:0", "danger")]), parse_mode="HTML")

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    text = msg.text.strip()
    if "|" in text:
        label, url = [x.strip() for x in text.split("|", 1)]
    else:
        url = text
        label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} URL must start with http/https.", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.setdefault("firebases", [])
    if not any(fb["url"] == url for fb in fbs):
        fbs.append({"id": str(int(time.time())), "url": url, "label": label, "added_at": int(time.time())})
        save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Saved <code>{url}</code>", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Bulk Add Firebase (.txt)</b>\n\nEk <code>.txt</code> file upload karein.", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:fb:menu:0", "danger")]), parse_mode="HTML")

@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    if not msg.document.file_name.endswith(".txt"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <code>.txt</code> file bhejein.", parse_mode="HTML")
        return
    f_info = await msg.bot.get_file(msg.document.file_id)
    raw = (await msg.bot.download_file(f_info.file_path)).read().decode("utf-8", errors="ignore")
    fbs = d.setdefault("firebases", [])
    existing = {fb["url"].rstrip("/") for fb in fbs}
    added = 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        label, url = ([x.strip() for x in line.split("|", 1)] if "|" in line else (line.replace("https://", "").split(".")[0][:20], line))
        url = url.rstrip("/")
        if url.startswith("http") and url not in existing:
            existing.add(url)
            fbs.append({"id": str(int(time.time() * 1000) + random.randint(1, 999)), "url": url, "label": label, "added_at": int(time.time())})
            added += 1
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Added <b>{added}</b> Firebases.", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    parts = cq.data.split(":")
    fb_id = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0
    d["firebases"] = [fb for fb in d.get("firebases", []) if fb["id"] != fb_id]
    save(d)
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("🗑 Removed!")
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>", reply_markup=fb_menu_kb(load(), page), parse_mode="HTML")

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    return (
        f"{em(EMOJI_STAR, '📊')} <b>{sc('api stats')}</b>\n\n"
        f"📤 Total Sent   : <b>{stats.get('total_sent', 0)}</b>\n"
        f"❌ Total Failed : <b>{stats.get('total_failed', 0)}</b>\n"
        f"🔥 Online Devs  : <b>{len(get_cached_devices())}</b>"
    )

@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_owner(cq.from_user.id, load()):
        return
    await cq.message.edit_text(api_stats_text(load()), reply_markup=kb([("ʀᴇғʀᴇsʜ", "owner:stats", "success"), ("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    rows = []
    if len(d.get("owners", [])) < 6:
        rows.append([btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕", style="success")])
    for oid in d.get("owners", []):
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (ᴍᴀɪɴ)", "noop", EMOJI_CROWN, "👑", style="primary")])
        else:
            rows.append([btn(f"{oid}", "noop", EMOJI_CROWN, "🔱", style="primary"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text("Super Admin Chat ID bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:owners:menu", "danger")]))

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        nid = int(msg.text.strip())
    except ValueError:
        await msg.answer("Valid ID bhejein.")
        return
    if nid not in d["owners"] and len(d["owners"]) < 6:
        d["owners"].append(nid)
        save(d)
    await state.clear()
    await msg.answer(f"✅ Added <code>{nid}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:owners:menu", "primary")]), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery):
    d = load()
    did = int(cq.data.split("owner:owners:del:", 1)[1])
    if did != MAIN_OWNER and did in d.get("owners", []):
        d["owners"].remove(did)
        save(d)
    await owner_owners_menu(cq)

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕", style="success")]]
    for aid in d.get("admins", []):
        rows.append([btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡", style="primary"), btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="danger")])
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text("Admin User ID bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:admins:menu", "danger")]))

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        nid = int(msg.text.strip())
    except ValueError:
        await msg.answer("Valid ID bhejein.")
        return
    if nid not in d.setdefault("admins", []):
        d["admins"].append(nid)
        save(d)
    await state.clear()
    await msg.answer(f"✅ Admin added <code>{nid}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:admins:menu", "primary")]), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery):
    d = load()
    did = int(cq.data.split("owner:admins:del:", 1)[1])
    if did in d.get("admins", []):
        d["admins"].remove(did)
        save(d)
    await owner_admins_menu(cq)

@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    d["free_mode"] = (cq.data == "owner:free:on")
    save(d)
    await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    items = list(d.get("users", {}).items())
    per = 10
    chunk = items[page * per:(page + 1) * per]
    lines = [f"{em(EMOJI_STAR, '👥')} <b>Users ({len(items)})</b>\n"]
    for u_str, udata in chunk:
        lines.append(f"• <code>{u_str}</code> — {udata.get('name', 'User')[:16]} | 💰{udata.get('credits', 0)}")
    rows = []
    nav = []
    if page > 0:
        nav.append(btn("◀️ ᴘʀᴇᴠ", f"{prefix}:users:pg:{page-1}", style="primary"))
    if (page + 1) * per < len(items):
        nav.append(btn("ɴᴇxᴛ ▶️", f"{prefix}:users:pg:{page+1}", style="primary"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", style="danger")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        return
    txt, mk = users_list_kb(d, "owner" if is_owner(uid, d) else "admin", 0)
    await cq.message.edit_text(txt, reply_markup=mk, parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        return
    parts = cq.data.split(":")
    txt, mk = users_list_kb(d, parts[0], int(parts[3]))
    await cq.message.edit_text(txt, reply_markup=mk, parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, load()) else "admin:home"
    await cq.message.edit_text("Ban karne ke liye User ID bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", back, "danger")]))

@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    try:
        bid = int(msg.text.strip())
    except ValueError:
        await msg.answer("Valid ID bhejein.")
        return
    if not is_admin(bid, d) and bid not in d.setdefault("banned", []):
        d["banned"].append(bid)
        save(d)
    await state.clear()
    await msg.answer(f"🚫 Banned <code>{bid}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home" if is_owner(msg.from_user.id, d) else "admin:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    banned = d.get("banned", [])
    if not banned:
        await cq.answer("✅ Koi banned nahi!", show_alert=True)
        return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    rows = [[btn(str(b), f"{prefix}:unban:do:{b}", EMOJI_CHECK, "🔓", style="success")] for b in banned]
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", style="danger")])
    await cq.message.edit_text("Unban select karein:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery):
    d = load()
    bid = int(cq.data.split(":")[-1])
    if bid in d.get("banned", []):
        d["banned"].remove(bid)
        save(d)
    await cq.answer(f"✅ Unbanned {bid}", show_alert=True)
    await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(cq.from_user.id, load()) else "admin:home"
    await cq.message.edit_text("Broadcast message bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", back, "danger")]))

@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    await state.clear()
    ok = fail = 0
    for u_str in d.get("users", {}):
        try:
            if msg.text:
                await msg.bot.send_message(int(u_str), f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n{msg.text}", parse_mode="HTML")
            else:
                await msg.copy_to(int(u_str))
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await msg.answer(f"✅ Sent: <b>{ok}</b> | ❌ Failed: <b>{fail}</b>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home" if is_owner(msg.from_user.id, d) else "admin:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery):
    if not is_owner(cq.from_user.id, load()):
        return
    try:
        script_path = os.path.abspath(__file__)
        await cq.message.reply_document(document=FSInputFile(script_path), caption=f"📤 Script Export — <b>{_VERSION}</b>", parse_mode="HTML")
    except Exception as e:
        await cq.answer(f"❌ {e}", show_alert=True)

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery):
    if not is_admin(cq.from_user.id, load()):
        return
    await cq.message.edit_text(api_stats_text(load()), reply_markup=kb([("ʙᴀᴄᴋ", "admin:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    fj = d.get("force_join", {})
    status = "🟢 ON" if fj.get("enabled") else "🔴 OFF"
    rows = [
        [btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", style="success"), btn("ʀᴇᴍᴏᴠᴇ", "owner:fj:remove", style="danger")],
        [btn("ᴛᴏɢɢʟᴇ ᴏɴ/ᴏғғ", "owner:fj:toggle", style="primary")],
        [btn("ʙᴀᴄᴋ", "owner:home", style="danger")]
    ]
    await cq.message.edit_text(f"{em(EMOJI_BELL, '🔗')} <b>Force Join</b>: {status}\nChannels: <b>{len(fj.get('channels', []))}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text("Channel ID bhejein (e.g. -100xxx):", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:fj:menu", "danger")]))

@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    try:
        cid = int(msg.text.strip())
    except ValueError:
        await msg.answer("Valid ID bhejein.")
        return
    await state.update_data(fj_channel_id=cid)
    await state.set_state(S.fj_add_link)
    await msg.answer("Channel invite link bhejein (https://...):")

@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("Valid https link bhejein.")
        return
    cid = str((await state.get_data()).get("fj_channel_id"))
    try:
        title = (await msg.bot.get_chat(int(cid))).title or "Channel"
    except Exception:
        title = "Channel"
    chs = [c for c in d.setdefault("force_join", {}).setdefault("channels", []) if str(c["id"]) != cid]
    chs.append({"id": cid, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = chs
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added {title}", reply_markup=kb([("ʙᴀᴄᴋ", "owner:fj:menu", "primary")]))

@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery):
    chs = load().get("force_join", {}).get("channels", [])
    rows = [[btn(c.get("title", "Ch")[:20], f"owner:fj:del:{c['id']}", style="danger")] for c in chs]
    rows.append([btn("ʙᴀᴄᴋ", "owner:fj:menu", style="primary")])
    await cq.message.edit_text("Remove channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery):
    d = load()
    cid = cq.data.split("owner:fj:del:", 1)[1]
    d["force_join"]["channels"] = [c for c in d.get("force_join", {}).get("channels", []) if str(c["id"]) != cid]
    save(d)
    await owner_fj_menu(cq)

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery):
    d = load()
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False)
    save(d)
    await owner_fj_menu(cq)

@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery):
    plans = load().get("pricing", {}).get("plans", [])
    txt = f"💳 <b>Credit Plans ({len(plans)})</b>\n" + "\n".join(f"• {p['name']}: ₹{p['price']} = {p['credits']}cr" for p in plans)
    rows = [
        [btn("ᴀᴅᴅ ᴘʟᴀɴ", "owner:pricing:add", style="success"), btn("ʀᴇᴍᴏᴠᴇ", "owner:pricing:remove", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", style="primary")]
    ]
    await cq.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text("Plan naam bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:pricing:menu", "danger")]))

@R.message(S.add_plan_name)
async def owner_pricing_name(msg: Message, state: FSMContext):
    await state.update_data(plan_name=msg.text.strip())
    await state.set_state(S.add_plan_price)
    await msg.answer("Price bhejein:")

@R.message(S.add_plan_price)
async def owner_pricing_price(msg: Message, state: FSMContext):
    try:
        await state.update_data(plan_price=float(msg.text.strip()))
    except ValueError:
        await msg.answer("Valid price bhejein.")
        return
    await state.set_state(S.add_plan_credits)
    await msg.answer("Credits bhejein:")

@R.message(S.add_plan_credits)
async def owner_pricing_credits(msg: Message, state: FSMContext):
    try:
        await state.update_data(plan_credits=int(msg.text.strip()))
    except ValueError:
        await msg.answer("Valid integer bhejein.")
        return
    await state.set_state(S.add_plan_link)
    await msg.answer("Payment link (https://...) bhejein:")

@R.message(S.add_plan_link)
async def owner_pricing_link(msg: Message, state: FSMContext):
    d = load()
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("Valid link bhejein.")
        return
    fd = await state.get_data()
    d.setdefault("pricing", {}).setdefault("plans", []).append({
        "id": str(int(time.time())),
        "name": fd.get("plan_name", "Plan"),
        "price": fd.get("plan_price", 0),
        "credits": fd.get("plan_credits", 0),
        "currency": "INR",
        "payment_link": link
    })
    save(d)
    await state.clear()
    await msg.answer("✅ Plan added!", reply_markup=kb([("ʙᴀᴄᴋ", "owner:pricing:menu", "primary")]))

@R.callback_query(F.data == "owner:pricing:remove")
async def owner_pricing_remove(cq: CallbackQuery):
    plans = load().get("pricing", {}).get("plans", [])
    rows = [[btn(p["name"][:20], f"owner:pricing:del:{p['id']}", style="danger")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "owner:pricing:menu", style="primary")])
    await cq.message.edit_text("Remove plan:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_pricing_del(cq: CallbackQuery):
    d = load()
    pid = cq.data.split("owner:pricing:del:", 1)[1]
    d["pricing"]["plans"] = [p for p in d.get("pricing", {}).get("plans", []) if p["id"] != pid]
    save(d)
    await owner_pricing_menu(cq)

@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery):
    codes = load().get("redeem_codes", {})
    txt = f"🎁 <b>Redeem Codes ({len(codes)})</b>\n" + "\n".join(f"• <code>{c}</code> ({v['credits']}cr, left:{v.get('uses_left',0)})" for c, v in list(codes.items())[:10])
    rows = [
        [btn("ɢᴇɴᴇʀᴀᴛᴇ", "owner:redeem:gen", style="success"), btn("ᴅᴇʟᴇᴛᴇ", "owner:redeem:del", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", style="primary")]
    ]
    await cq.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text("Credits amount bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:redeem:menu", "danger")]))

@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg: Message, state: FSMContext):
    try:
        await state.update_data(gen_credits=int(msg.text.strip()))
    except ValueError:
        await msg.answer("Valid number bhejein.")
        return
    await state.set_state(S.gen_redeem_uses)
    await msg.answer("Kitni baar use ho sakta hai?")

@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg: Message, state: FSMContext):
    d = load()
    try:
        uses = int(msg.text.strip())
        if uses < 1:
            raise ValueError
    except ValueError:
        await msg.answer("Valid number (>=1) bhejein.")
        return
    credits = int((await state.get_data()).get("gen_credits", 10))
    code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    d.setdefault("redeem_codes", {})[code] = {"credits": credits, "uses_left": uses, "created_by": msg.from_user.id, "used_by": []}
    save(d)
    await state.clear()
    await msg.answer(f"🎉 Code: <code>{code}</code> (+{credits}cr, {uses} uses)", reply_markup=kb([("ʙᴀᴄᴋ", "owner:redeem:menu", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del_menu(cq: CallbackQuery):
    codes = load().get("redeem_codes", {})
    rows = [[btn(c, f"owner:redeem:deldo:{c}", style="danger")] for c in list(codes.keys())[:20]]
    rows.append([btn("ʙᴀᴄᴋ", "owner:redeem:menu", style="primary")])
    await cq.message.edit_text("Delete code:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_del_do(cq: CallbackQuery):
    d = load()
    c = cq.data.split("owner:redeem:deldo:", 1)[1]
    d.get("redeem_codes", {}).pop(c, None)
    save(d)
    await owner_redeem_menu(cq)

@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text("User ID bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]))

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    try:
        await state.update_data(credit_uid=int(msg.text.strip()))
    except ValueError:
        await msg.answer("Valid ID bhejein.")
        return
    await state.set_state(S.add_credits_amount)
    await msg.answer("Kitne credits add karne hain?")

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    try:
        amt = int(msg.text.strip())
    except ValueError:
        await msg.answer("Valid number bhejein.")
        return
    target = int((await state.get_data()).get("credit_uid"))
    add_credits(target, amt, d)
    save(d)
    await state.clear()
    await msg.answer(f"✅ Added {amt} to <code>{target}</code>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text("User ID bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:home", "danger")]))

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    try:
        await state.update_data(deduct_uid=int(msg.text.strip()))
    except ValueError:
        await msg.answer("Valid ID bhejein.")
        return
    await state.set_state(S.deduct_credits_amount)
    await msg.answer("Kitne credits deduct karne hain?")

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    try:
        amt = int(msg.text.strip())
    except ValueError:
        await msg.answer("Valid number bhejein.")
        return
    target = int((await state.get_data()).get("deduct_uid"))
    ok = deduct_credits(target, amt, d)
    save(d)
    await state.clear()
    await msg.answer("✅ Deducted!" if ok else "❌ Insufficient balance.", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]))

@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery):
    ref_c = load().get("settings", {}).get("ref_credits", 3)
    await cq.message.edit_text(
        f"⚙️ <b>Settings</b>\nReferral Credits: <b>{ref_c}</b>",
        reply_markup=kb([("sᴇᴛ ʀᴇғ ᴄʀᴇᴅɪᴛs", "owner:settings:ref", "success"), ("ʙᴀᴄᴋ", "owner:home", "primary")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text("Referral credits bhejein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "owner:settings", "danger")]))

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    try:
        c = int(msg.text.strip())
        if c < 0:
            raise ValueError
    except ValueError:
        await msg.answer("Valid number bhejein.")
        return
    d.setdefault("settings", {})["ref_credits"] = c
    save(d)
    await state.clear()
    await msg.answer(f"✅ Referral credits = <b>{c}</b>", reply_markup=kb([("ʙᴀᴄᴋ", "owner:settings", "primary")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery):
    entries = load().get("activity_log", [])[-15:]
    txt = "\n".join(f"[{fmt_time(e.get('timestamp',0))}] <code>{e.get('uid')}</code> {e.get('action')}" for e in reversed(entries)) or "<i>Empty</i>"
    await cq.message.edit_text(f"📜 <b>Activity Log</b>\n\n{txt}", reply_markup=kb([("ʙᴀᴄᴋ", "owner:home", "primary")]), parse_mode="HTML")

@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if not can_use(uid, d):
        await cq.message.edit_text("⛔ Access nahi hai!", reply_markup=premium_plans_kb("user:home"), parse_mode="HTML")
        return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery):
    c = get_user_credits(cq.from_user.id, load())
    await cq.answer(f"💰 Credits: {c}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text("Redeem code enter karein:", reply_markup=kb([("ᴄᴀɴᴄᴇʟ", "user:home", "danger")]))

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()
    rec = d.get("redeem_codes", {}).get(code)
    if not rec or rec.get("uses_left", 0) <= 0 or uid in rec.get("used_by", []):
        await msg.answer("❌ Invalid / Expired / Already used code.", reply_markup=kb([("ʜᴏᴍᴇ", "user:home", "primary")]))
        return
    add_credits(uid, rec["credits"], d)
    rec["uses_left"] -= 1
    rec.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(f"🎉 +{rec['credits']} credits added!", reply_markup=kb([("ʜᴏᴍᴇ", "user:home", "primary")]))

@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery):
    d = load()
    code = generate_user_refer_code(cq.from_user.id, d)
    save(d)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"👥 <b>Referral</b>\nCode: <code>{code}</code>\nLink: https://t.me/{me.username}?start={code}",
        reply_markup=kb([("ʙᴀᴄᴋ", "user:home", "primary")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery):
    d = load()
    u = d.get("users", {}).get(str(cq.from_user.id), {})
    await cq.message.edit_text(
        f"📊 <b>Your Stats</b>\nCredits: <b>{u.get('credits',0)}</b> | Uses: <b>{u.get('uses',0)}</b>",
        reply_markup=kb([("ʙᴀᴄᴋ", "user:home", "primary")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery):
    plans = load().get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ Koi plan nahi!", show_alert=True)
        return
    rows = [[btn_url(f"Buy {p['name']} (₹{p['price']})", p["payment_link"], style="success")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "user:home", style="danger")])
    await cq.message.edit_text("💰 <b>Buy Credits</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery):
    await cq.message.edit_text(
        f"ℹ️ <b>Bot {_VERSION}</b>\nOwner: {SUPER_ADMIN_NAME}",
        reply_markup=kb([("ʙᴀᴄᴋ", "user:home", "primary")]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

# ========== ENTRYPOINT ==========

async def main():
    d = load()
    global PROTECTED_NUMBERS
    PROTECTED_NUMBERS = dict(d.get("protected_numbers", {}))

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)

    me = await bot.get_me()
    log.info(f"@{me.username} — {_VERSION} started!")

    asyncio.create_task(background_firebase_scanner(bot))
    asyncio.create_task(auto_message_loop(bot))

    try:
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>{_VERSION} Online!</b> (@{me.username})\n"
            f"• Default Speed: <b>MEDIUM ({SPEED_MEDIUM}s)</b>\n"
            f"• Auto-Msg Target: <b>All Users (DM)</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        log.warning(f"Owner notify failed: {e}")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
