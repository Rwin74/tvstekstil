# TVS butik keşfi entegrasyonu

Butik arama bölümü `/admin/butik/` adresindedir; yönetim panelindeki “Butik keşfi” bağlantısı buraya gider. Mevcut TVS yönetici hesabını kullanır. Ürün, şehir, genel arama ve anahtar kelimesiz potansiyel keşfi; kayıt, takip, JSON yedek, CSV ve Türkçe karakterli PDF bu bölümde bulunur. Yabancı metinlerin Türkçe karşılıkları ayrı alanlarda saklanır ve PDF'ye eklenir. Otomatik çeviri ayrıca servis anahtarı gerektirir; elle çeviri girişi anahtarsız çalışır.

## Yayına geçiş

1. Mevcut Supabase projesinin SQL Editor bölümünde `supabase/boutiques.sql` dosyasını çalıştırın. Bu ek kurulum mevcut CMS, ürün ve teklif tablolarını değiştirmez. Tekrar çalıştırılabilir. Bütün yetkili TVS yöneticileri aynı firma çalışma alanını paylaşır.
2. Vercel projesinde mevcut `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (veya `SUPABASE_ANON_KEY`) ve `ADMIN_SESSION_KEY` korunmalı. Butik modülü kullanıcı oturumunu kullanır; ayrı veritabanı parolası veya servis rolü anahtarı istemez.
3. Vercel Production ortamına `SEARCH_PROVIDER=serpapi` ve `SERPAPI_KEY` ekleyin. Anahtarı GitHub'a, tarayıcı koduna veya ekran görüntüsüne koymayın. Masaüstündeki Windows kasası otomatik olarak siteye aktarılmaz.
4. İsteğe bağlı çeviri için `TRANSLATION_PROVIDER=azure` veya `google`, `TRANSLATION_KEY` ve Azure gerekiyorsa `TRANSLATION_REGION` tanımlayın. Anahtar yoksa otomatik çeviri açıkça hata verir; uydurma çeviri üretmez.
5. Vercel'de Python 3.12 ve Fluid Compute etkin olmalı; `api/boutiques.py` için 120 saniye üst sınırı tanımlıdır. Mevcut statik site derlemesi ve Node API'leri korunur. Sonra entegrasyon dalını normal yayın sürecinden geçirin.
6. `https://www.tvstextile.com/admin/` üzerinden giriş yapın; “Butik keşfi” bölümünde gerçek bir arama, kaydetme, sayfa yenileme, PDF ve çıkış işlemlerini doğrulayın. Mevcut güvenlik politikası yalnızca bu kanonik alan adından yazma işlemlerine izin verir; Vercel preview alan adı için korumayı gevşetmeyin.
7. Masaüstü kayıtlarını aktarmak için masaüstünde “Ayarlar ve yedekleme”den JSON yedeği indirin, web bölümünde içe aktarın. Tekrarlanan firmalar atlanır; otomatik çift yönlü eşitleme yoktur. Web yükleme sınırı 4 MB'dır; büyük yedekleri desteklenen boyutta gruplar halinde aktarın. PDF için de seçimi filtrelerle küçültebilirsiniz.

## Doğrulama

- `npm ci` ve `npm test`: mevcut yönetici güvenliği + PGlite PostgreSQL motorunda migration, rol izinleri, sürüm çakışmaları, işlem bütünlüğü, geçmiş, önbellek ve kota.
- `python -m pip install -r requirements-dev.txt` ve `python -m pytest -q`: arama eleme, SSRF koruması, API, PDF, çeviri ve mevcut Node oturumuyla Python doğrulama uyumluluğu. Windows kasası testleri normal kullanıcı bağlamı gerektirir.
- `python tests/browser_check.py`: kurulu Microsoft Edge ile yalnızca yerel test verisi kullanan 18 uçtan uca kontrol. Arama ve kimlik sağlayıcıları bu testte kontrollü örnek yanıtlar verir; gerçek ücretli servis testi değildir.
- `node tools/build_vercel.cjs`: çok dilli sayfa kontrolleri ve statik çıktı. Yerel anahtarsız çalıştırmada mevcut CMS başlangıç verisini kullanır; canlı üretim CMS verisi ayrıca dağıtımda okunur.

Test sunucuları ve örnek veriler üretim dağıtımına dahil edilmez. API anahtarları ve firma kayıtları statik siteye yazılmaz. API'ye doğrudan erişimde de oturum ve Supabase yönetici rolü kontrol edilir. Cookie AES-GCM doğrulaması, aynı kaynak ve CSRF koruması kullanılır. Yetki her istekte tekrar kontrol edilir.

## Bu çalışma sırasında tamamlanan / bekleyen

Yerel kod, SQL motoru, tarayıcı ve site derlemesi testleri tamamlandı. Gerçek Supabase projesine migration uygulanması, Vercel ortam değişkenleri, dağıtım ve canlı sitedeki son kullanıcı testi henüz yapılmadı. Yerel testlerin geçmesi bu dış adımların tamamlandığı anlamına gelmez.

Arama, web sitelerinin erişilebilirliğine ve sağlayıcının kotasına bağlıdır. Sistem erişemediği siteleri doğrulanmış butik diye kabul etmez. Potansiyel firma, kesin tedarik talebi veya sipariş anlamına gelmez.
