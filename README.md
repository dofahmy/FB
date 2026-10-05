Melook Make Forwarder v4

Flow:
EgyptOffersHunter -> Railway -> rewrite Amazon tag/link -> new short link -> Make Webhook -> Facebook Pages

Required Railway variables:
TELEGRAM_API_ID
TELEGRAM_API_HASH
TELEGRAM_SESSION_STRING
TELEGRAM_SOURCE=EgyptOffersHunter
MAKE_WEBHOOK_URL
FACEBOOK_AMAZON_TAG
EGYPT_SHORT_BASE_URL
EGYPT_SHORT_API_KEY

Optional:
SOURCE_ENABLED=true
REWRITE_AMAZON_LINKS=true
FORWARD_TEXT=true
FORWARD_PHOTO=true
FORWARD_ALBUM=false
FORWARD_VIDEO=false
SKIP_DUPLICATES=true
STATE_DIR=/data
STATE_FILE=/data/facebook_forwarder_state.json

Start:
python Melook_FB_Forwarder.py

Make receives:
message
telegram_message_id
has_image
image (multipart file)
