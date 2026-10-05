# Facebook Test Publisher

سكريبت مستقل لتجربة النشر على صفحة Facebook تجريبية قبل ربطه ببرنامج ملوك العروض.

## Railway Variables

أضيفي في Service تجريبية مستقلة:

FACEBOOK_PAGE_ID=...
FACEBOOK_PAGE_ACCESS_TOKEN=...
META_GRAPH_VERSION=v24.0

## Start Command للاختبار النصي

python facebook_test_publisher.py text "اختبار نشر أوتوماتيك من Railway"

## اختبارات أخرى

### نص + لينك
python facebook_test_publisher.py link "اختبار عرض" "https://example.com"

### صورة من رابط مباشر
python facebook_test_publisher.py photo-url "اختبار صورة" "https://example.com/image.jpg"

### صورة موجودة داخل المشروع
python facebook_test_publisher.py photo-file "اختبار صورة" "./test.jpg"

## مهم

استخدمي صفحة تجريبية فقط في هذه المرحلة، ولا تضعي بيانات صفحة ملوك العروض الحقيقية حتى تنجح كل الاختبارات.
