# Melook FB Forwarder v3

التعديل الأساسي في هذه النسخة:

- الصورة تُرفع أولًا إلى Facebook كـ unpublished media (`published=false`).
- بعدها يُنشأ بوست فعلي على `/feed`.
- النص يوضع في `message`.
- الصورة تُربط بالبوست من خلال `attached_media`.

الهدف: يظهر البوست للمستخدم العادي كنص كامل فوق الصورة، بدل الاعتماد على Caption خاص بمنشور الصور.

## Start Command

python Melook_FB_Forwarder.py

## Variables

نفس Variables نسخة v2 بدون أي تغيير، ومنها:

TELEGRAM_API_ID
TELEGRAM_API_HASH
TELEGRAM_SESSION_STRING
TELEGRAM_SOURCE=EgyptOffersHunter

FACEBOOK_PAGE_ID
FACEBOOK_PAGE_ACCESS_TOKEN
FACEBOOK_AMAZON_TAG
META_GRAPH_VERSION=v26.0

EGYPT_SHORT_BASE_URL
EGYPT_SHORT_API_KEY

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

## Expected log for a photo post

[fb] feed post created with attached_media=...
[fb] photo published message_id=...
