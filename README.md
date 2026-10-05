# Melook FB Forwarder v2

Reads new posts from Telegram channel `EgyptOffersHunter`, rewrites Amazon links
with a Facebook-specific affiliate tag, creates a NEW short link using the same
Egypt shortener service, then publishes to Facebook.

## Required Railway Variables

TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION_STRING=...
TELEGRAM_SOURCE=EgyptOffersHunter

FACEBOOK_PAGE_ID=...
FACEBOOK_PAGE_ACCESS_TOKEN=...
FACEBOOK_AMAZON_TAG=your-facebook-tag-21
META_GRAPH_VERSION=v26.0

EGYPT_SHORT_BASE_URL=https://YOUR-SHORT-DOMAIN
EGYPT_SHORT_API_KEY=...

FACEBOOK_ENABLED=true
SOURCE_ENABLED=true
REWRITE_AMAZON_LINKS=true

FORWARD_TEXT=true
FORWARD_PHOTO=true
FORWARD_ALBUM=false
FORWARD_VIDEO=false

SKIP_DUPLICATES=true
STATE_DIR=/data
STATE_FILE=/data/facebook_forwarder_state.json

## Start Command

python Melook_FB_Forwarder.py

## Link flow

Old Telegram short link
-> one-hop resolve to existing Amazon URL
-> extract ASIN
-> build new amazon.eg affiliate URL with FACEBOOK_AMAZON_TAG
-> call existing Egypt shortener API
-> replace old URL in Facebook post text with the NEW short URL

## Railway Volume

Mount a Railway Volume at `/data` if you want duplicate protection to survive redeploys.
