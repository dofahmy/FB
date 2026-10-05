import os
import sys
import requests

GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v24.0")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID", "").strip()
PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()

BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def require_env():
    missing = []
    if not PAGE_ID:
        missing.append("FACEBOOK_PAGE_ID")
    if not PAGE_ACCESS_TOKEN:
        missing.append("FACEBOOK_PAGE_ACCESS_TOKEN")
    if missing:
        raise RuntimeError("Missing environment variables: " + ", ".join(missing))


def _check_response(resp):
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        return {"raw": resp.text}

    if not resp.ok or "error" in data:
        raise RuntimeError(f"Meta API error: {data}")
    return data


def publish_text(message: str):
    url = f"{BASE}/{PAGE_ID}/feed"
    payload = {
        "message": message,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    return _check_response(requests.post(url, data=payload, timeout=60))


def publish_link(message: str, link: str):
    url = f"{BASE}/{PAGE_ID}/feed"
    payload = {
        "message": message,
        "link": link,
        "access_token": PAGE_ACCESS_TOKEN,
    }
    return _check_response(requests.post(url, data=payload, timeout=60))


def publish_photo_url(message: str, image_url: str):
    url = f"{BASE}/{PAGE_ID}/photos"
    payload = {
        "message": message,
        "url": image_url,
        "published": "true",
        "access_token": PAGE_ACCESS_TOKEN,
    }
    return _check_response(requests.post(url, data=payload, timeout=60))


def publish_photo_file(message: str, image_path: str):
    url = f"{BASE}/{PAGE_ID}/photos"
    with open(image_path, "rb") as f:
        files = {"source": f}
        payload = {
            "message": message,
            "published": "true",
            "access_token": PAGE_ACCESS_TOKEN,
        }
        return _check_response(
            requests.post(url, data=payload, files=files, timeout=120)
        )


def main():
    require_env()

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "  python facebook_test_publisher.py text \"hello\"\n"
            "  python facebook_test_publisher.py link \"caption\" \"https://example.com\"\n"
            "  python facebook_test_publisher.py photo-url \"caption\" \"https://example.com/image.jpg\"\n"
            "  python facebook_test_publisher.py photo-file \"caption\" \"/path/to/image.jpg\""
        )
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "text" and len(sys.argv) >= 3:
        result = publish_text(sys.argv[2])

    elif mode == "link" and len(sys.argv) >= 4:
        result = publish_link(sys.argv[2], sys.argv[3])

    elif mode == "photo-url" and len(sys.argv) >= 4:
        result = publish_photo_url(sys.argv[2], sys.argv[3])

    elif mode == "photo-file" and len(sys.argv) >= 4:
        result = publish_photo_file(sys.argv[2], sys.argv[3])

    else:
        raise RuntimeError("Invalid arguments. Run without arguments to see usage.")

    print("SUCCESS")
    print(result)


if __name__ == "__main__":
    main()
