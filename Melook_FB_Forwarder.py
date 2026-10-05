import os
import re
import json
import asyncio
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit, urlencode, unquote

import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession

from egypt_offer_shortener import request_short_url


# =========================
# Helpers / Environment
# =========================

def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "").strip()
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
TELEGRAM_SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING", "").strip()
TELEGRAM_SOURCE = os.getenv("TELEGRAM_SOURCE", "EgyptOffersHunter").strip()

FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()
FACEBOOK_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
FACEBOOK_AMAZON_TAG = os.getenv("FACEBOOK_AMAZON_TAG", "").strip()
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v26.0").strip()

FACEBOOK_ENABLED = env_bool("FACEBOOK_ENABLED", True)
SOURCE_ENABLED = env_bool("SOURCE_ENABLED", True)

FORWARD_TEXT = env_bool("FORWARD_TEXT", True)
FORWARD_PHOTO = env_bool("FORWARD_PHOTO", True)
FORWARD_ALBUM = env_bool("FORWARD_ALBUM", False)
FORWARD_VIDEO = env_bool("FORWARD_VIDEO", False)

REWRITE_AMAZON_LINKS = env_bool("REWRITE_AMAZON_LINKS", True)
SKIP_DUPLICATES = env_bool("SKIP_DUPLICATES", True)

STATE_DIR = os.getenv("STATE_DIR", "/data").strip() or "/data"
STATE_FILE = os.getenv(
    "STATE_FILE",
    str(Path(STATE_DIR) / "facebook_forwarder_state.json")
).strip()

GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_VERSION}"

URL_RE = re.compile(r'https?://[^\s<>"\']+', re.I)
ASIN_RE = re.compile(
    r'/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)',
    re.I
)

# Used to generate unique Amazon linkId values.
_LAST_LINK_MS = 0


def normalize_source(source: str) -> str:
    source = source.strip()
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if source.startswith(prefix):
            source = source[len(prefix):]
            break
    return source.strip("/").lstrip("@")


def require_env():
    missing = []
    required = {
        "TELEGRAM_API_ID": TELEGRAM_API_ID,
        "TELEGRAM_API_HASH": TELEGRAM_API_HASH,
        "TELEGRAM_SESSION_STRING": TELEGRAM_SESSION_STRING,
        "FACEBOOK_PAGE_ID": FACEBOOK_PAGE_ID,
        "FACEBOOK_PAGE_ACCESS_TOKEN": FACEBOOK_PAGE_ACCESS_TOKEN,
    }

    if REWRITE_AMAZON_LINKS:
        required["FACEBOOK_AMAZON_TAG"] = FACEBOOK_AMAZON_TAG
        required["EGYPT_SHORT_BASE_URL"] = os.getenv("EGYPT_SHORT_BASE_URL", "").strip()
        required["EGYPT_SHORT_API_KEY"] = os.getenv("EGYPT_SHORT_API_KEY", "").strip()

    for key, value in required.items():
        if not value:
            missing.append(key)

    if missing:
        raise RuntimeError(
            "Missing required Railway variables: " + ", ".join(missing)
        )


# =========================
# State
# =========================

def load_state():
    path = Path(STATE_FILE)
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[state] Could not read state file: {exc}")
    return {"last_message_id": 0}


def save_state(state):
    path = Path(STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(path)


# =========================
# Amazon / short-link rewriting
# =========================

def _amazon_product_link(asin: str, tag: str) -> str:
    """Build the same canonical Amazon Egypt affiliate product-link shape."""
    global _LAST_LINK_MS

    asin = str(asin).strip().upper()
    now_ms = int(time.time() * 1000)
    _LAST_LINK_MS = max(now_ms, _LAST_LINK_MS + 1)

    fields = {
        "ref": "t_ac_spc_accepted_tile",
        "linkCode": "tr1",
        "tag": tag,
        "linkId": f"{asin}_{_LAST_LINK_MS}",
    }
    return f"https://www.amazon.eg/dp/{asin}?{urlencode(fields)}"


def _extract_asin(url: str):
    """Extract ASIN from an Amazon product URL."""
    try:
        parsed = urlsplit(url)
    except Exception:
        return None

    host = (parsed.hostname or "").lower()
    if "amazon." not in host:
        return None

    m = ASIN_RE.search(parsed.path)
    return m.group(1).upper() if m else None


def _shortener_host():
    try:
        return (urlsplit(os.getenv("EGYPT_SHORT_BASE_URL", "").strip()).hostname or "").lower()
    except Exception:
        return ""


def _resolve_one_hop(url: str):
    """
    Resolve our existing short URL without following all the way into Amazon.
    The shortener supports HEAD and returns Location: <full Amazon target>.
    """
    try:
        r = requests.head(
            url,
            allow_redirects=False,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        loc = r.headers.get("Location")
        if loc:
            return loc
    except Exception as exc:
        print(f"[links] HEAD failed for {url}: {type(exc).__name__}: {exc}")

    try:
        r = requests.get(
            url,
            allow_redirects=False,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        loc = r.headers.get("Location")
        if loc:
            return loc
    except Exception as exc:
        print(f"[links] GET failed for {url}: {type(exc).__name__}: {exc}")

    return None


def _decode_telegram_url(url: str) -> str:
    # Be conservative; only undo common HTML encoding that can leak into text.
    return url.replace("&amp;", "&").strip()


def rewrite_one_url(url: str) -> str:
    """
    Source short URL -> original Amazon target -> ASIN ->
    Facebook-tagged canonical Amazon URL -> NEW short URL.
    """
    raw = _decode_telegram_url(url)
    candidate = raw

    asin = _extract_asin(candidate)

    # If it is not already a canonical Amazon product URL, try resolving our
    # current Egypt short-link domain one hop.
    if not asin:
        short_host = _shortener_host()
        try:
            host = (urlsplit(candidate).hostname or "").lower()
        except Exception:
            host = ""

        if short_host and host == short_host:
            resolved = _resolve_one_hop(candidate)
            if resolved:
                candidate = resolved
                asin = _extract_asin(candidate)

    if not asin:
        # Not one of our supported Amazon product links. Leave untouched.
        return url

    full_fb_url = _amazon_product_link(asin, FACEBOOK_AMAZON_TAG)
    new_short = request_short_url(full_fb_url)

    if new_short != full_fb_url:
        print(f"[links] {asin}: old -> new Facebook short link")
    else:
        print(f"[links] {asin}: shortener unavailable, using full Facebook-tagged Amazon URL")

    return new_short


def rewrite_amazon_links_in_text(text: str) -> str:
    if not text or not REWRITE_AMAZON_LINKS:
        return text or ""

    def repl(match):
        original = match.group(0)

        # Preserve punctuation commonly attached after URLs.
        trailing = ""
        while original and original[-1] in ".,؛،!?)]}":
            trailing = original[-1] + trailing
            original = original[:-1]

        try:
            replaced = rewrite_one_url(original)
            return replaced + trailing
        except Exception as exc:
            print(f"[links] Failed rewriting {original}: {type(exc).__name__}: {exc}")
            return match.group(0)

    return URL_RE.sub(repl, text)


# =========================
# Meta publishing
# =========================

def meta_request(endpoint: str, *, data=None, files=None, timeout=120):
    url = f"{GRAPH_BASE}/{endpoint.lstrip('/')}"
    payload = dict(data or {})
    payload["access_token"] = FACEBOOK_PAGE_ACCESS_TOKEN

    resp = requests.post(
        url,
        data=payload,
        files=files,
        timeout=timeout
    )

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    if not resp.ok or "error" in body:
        raise RuntimeError(f"Meta API error: {body}")

    return body


def publish_text(message: str):
    if not message.strip():
        return None

    return meta_request(
        f"{FACEBOOK_PAGE_ID}/feed",
        data={"message": message},
    )


def publish_photo_file(message: str, image_path: str):
    """
    Publish as a real Page feed post:
      1) Upload photo as unpublished media.
      2) Create /feed post with message + attached_media.

    This keeps the text as the feed post message instead of relying only on
    a photo caption.
    """
    # Step 1: upload photo without publishing it as a standalone photo post.
    with open(image_path, "rb") as f:
        uploaded = meta_request(
            f"{FACEBOOK_PAGE_ID}/photos",
            data={"published": "false"},
            files={"source": f},
        )

    media_fbid = uploaded.get("id")
    if not media_fbid:
        raise RuntimeError(f"Meta photo upload returned no media id: {uploaded}")

    # Step 2: create the actual feed post with the text and uploaded photo.
    payload = {
        "message": message or "",
        "attached_media[0]": json.dumps({"media_fbid": media_fbid}),
    }
    result = meta_request(
        f"{FACEBOOK_PAGE_ID}/feed",
        data=payload,
    )
    print(f"[fb] feed post created with attached_media={media_fbid}")
    return result


# =========================
# Telegram message handling
# =========================

def get_message_text(msg) -> str:
    if not FORWARD_TEXT:
        return ""
    raw = (msg.message or "").strip()
    return rewrite_amazon_links_in_text(raw)


def is_photo_message(msg) -> bool:
    return bool(getattr(msg, "photo", None))


def is_video_message(msg) -> bool:
    document = getattr(msg, "document", None)
    if not document:
        return False

    for attr in getattr(document, "attributes", []) or []:
        if "video" in attr.__class__.__name__.lower():
            return True
    return False


async def publish_single_message(client, msg):
    if not FACEBOOK_ENABLED:
        print(f"[skip] Facebook disabled; message_id={msg.id}")
        return True

    text = get_message_text(msg)

    if FORWARD_PHOTO and is_photo_message(msg):
        with tempfile.TemporaryDirectory(prefix="melook_fb_") as tmp:
            image_path = await client.download_media(msg, file=tmp)

            if not image_path:
                print(f"[warn] Could not download photo for message_id={msg.id}")
                if text:
                    result = publish_text(text)
                    print(f"[fb] text fallback published: {result}")
                    return True
                return False

            result = publish_photo_file(text, image_path)
            print(f"[fb] photo published message_id={msg.id}: {result}")
            return True

    if is_video_message(msg):
        if not FORWARD_VIDEO:
            print(f"[skip] Video skipped message_id={msg.id}")
            return True
        print(
            "[skip] FORWARD_VIDEO=true but video publishing "
            f"is not implemented yet. message_id={msg.id}"
        )
        return False

    if text:
        result = publish_text(text)
        print(f"[fb] text published message_id={msg.id}: {result}")
        return True

    print(f"[skip] Nothing supported to publish for message_id={msg.id}")
    return True


async def process_message(client, msg, state):
    if not SOURCE_ENABLED:
        return

    if SKIP_DUPLICATES and msg.id <= int(state.get("last_message_id", 0)):
        print(f"[skip] duplicate/old message_id={msg.id}")
        return

    try:
        ok = await publish_single_message(client, msg)
        if ok:
            state["last_message_id"] = max(
                int(state.get("last_message_id", 0)),
                int(msg.id),
            )
            save_state(state)
    except Exception as exc:
        print(f"[error] message_id={msg.id}: {type(exc).__name__}: {exc}")


async def main():
    require_env()

    source = normalize_source(TELEGRAM_SOURCE)

    print("[startup] Melook FB Forwarder v3 - FEED + attached_media")\n    print(f"[startup] Telegram source: @{source}")
    print(f"[startup] Meta Graph version: {META_GRAPH_VERSION}")
    print(f"[startup] State file: {STATE_FILE}")
    print(f"[startup] Facebook enabled: {FACEBOOK_ENABLED}")
    print(f"[startup] Rewrite Amazon links: {REWRITE_AMAZON_LINKS}")
    print(f"[startup] Facebook Amazon tag: {FACEBOOK_AMAZON_TAG}")
    print(f"[startup] Short base: {os.getenv('EGYPT_SHORT_BASE_URL', '')}")
    print(f"[startup] Forward text: {FORWARD_TEXT}")
    print(f"[startup] Forward photo: {FORWARD_PHOTO}")
    print(f"[startup] Forward album: {FORWARD_ALBUM}")
    print(f"[startup] Forward video: {FORWARD_VIDEO}")

    state = load_state()
    print(f"[startup] last_message_id={state.get('last_message_id', 0)}")

    client = TelegramClient(
        StringSession(TELEGRAM_SESSION_STRING),
        int(TELEGRAM_API_ID),
        TELEGRAM_API_HASH,
    )

    await client.start()
    me = await client.get_me()
    print(
        "[telegram] Logged in as: "
        f"{getattr(me, 'username', None) or getattr(me, 'id', 'unknown')}"
    )

    entity = await client.get_entity(source)
    print(f"[telegram] Watching: {getattr(entity, 'title', source)}")

    @client.on(events.NewMessage(chats=entity))
    async def handler(event):
        msg = event.message
        print(f"[telegram] New message_id={msg.id}")
        await process_message(client, msg, state)

    print("[ready] Waiting for new Telegram posts...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
