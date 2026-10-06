# TVS yönetim paneli — kurulum ve durum

6 Ekim 2026 kurulum kaydı: Supabase şeması uygulandı; anonim ve yönetici olmayan erişimi reddeden gerçek veritabanı kontrolleri geçti. atakan7495@gmail.com hesabı UUID üzerinden yönetici olarak yetkilendirildi. Herkese açık kayıt kapatıldı, minimum parola uzunluğu 12 ve güvenli parola değişimi etkinleştirildi. Vercel Production ortamına Supabase bağlantısı ve oturum şifreleme anahtarı eklendi. Önceki secret anahtarı iptal edildi. Kullanıcı gerçek yönetici girişini doğruladı. Yönetici RLS kayıt testi geçti. Yayın tokenı Production ortamına bağlandı. Mail/Turnstile kurulumu kullanıcının isteğiyle ertelendi; mail teslim testi yapılmadı.

Panel adresi `/admin/`. Yerel önizleme: `npm run admin:preview`, ardından http://127.0.0.1:8787/admin/.

Bu sürüm Supabase/Vercel bağlantıları olmadan **kapalı çalışır**. Demo şifresi, herkese açık kayıt ve giriş atlama bulunmaz. Kodun hazırlanması gerçek hesap, veritabanı veya mail teslimatının kurulduğu anlamına gelmez.

## 1. Supabase projesi

1. Şirketin kontrolündeki hesapta yeni proje açın. Müşteri verileri için uygun bölge seçin; hesapta iki aşamalı doğrulamayı etkinleştirin.
2. SQL Editor'da `supabase/admin.sql` dosyasını bir kez çalıştırın.
3. Authentication ayarlarından herkese açık kayıtları kapatın. Minimum şifre uzunluğunu 12 yapın; şifre politikasını ve Auth deneme limitlerini etkinleştirin.
4. Authentication > Users bölümünde yöneticinin gerçek e-posta adresiyle hesabını oluşturun. Güçlü, benzersiz şifreyi güvenli kanaldan teslim edin; Git'e veya sohbete yazmayın.
5. Kullanıcının UUID'sini SQL Editor'da ekleyin: `insert into public.cms_admins(user_id) values ('GERÇEK-UUID');`. E-posta adresi tek başına yetki vermez. Yetkiyi kaldırmak için bu kaydı silin.
6. Project Settings'den URL, publishable key ve secret key alın. Service-role key yalnızca Vercel sunucu ortamında kullanılacak. Tarayıcıya gönderilmez.

## 2. Vercel ortam değişkenleri

`.env.example` isimleri gösterir. Vercel > Project > Settings > Environment Variables bölümüne değerleri ekleyin:

- `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`
- `ADMIN_SESSION_KEY`: `node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"` ile üretin. Anahtar değişimi mevcut oturumları sonlandırır.
- `ADMIN_GITHUB_PUBLISH_TOKEN`: yalnızca Rwin74/tvstekstil deposuna erişen, süreli bir fine-grained GitHub token; Contents read/write. Başka repo veya hesap yetkisi vermeyin.

Production ortamını kullanın. Yönetim paneli sabit `https://www.tvstextile.com` kaynağını kabul eder; başka alan adı ve önizleme adresi giriş/yazma için kabul edilmez. Yeni dağıtım gerekir. Node 22 veya üstü kullanın.

## 3. Yayınlama

GitHub Actions hesapta kapalı olduğu için yayınlar Actions kullanmaz. Vercel Production ortamındaki ADMIN_GITHUB_PUBLISH_TOKEN yalnızca Rwin74/tvstekstil deposunda Contents read/write yetkisi taşır. Oluşturulan token 5 Kasım 2026 tarihinde sona erer; bu tarihten önce yenilenip Vercel ortamına bağlanmalıdır.

Taslağı kaydet veritabanındaki sürümü artırır; eşzamanlı eski sürümle yazmayı reddeder. Yayınla dört dilde aktif ürün alanlarını doğrular, yayınlanan kopyayı kaydeder ve sadece data/cms-revision.json dosyasına bir yayın işareti commit eder. Kişisel müşteri verileri, taslak içerikler veya gizli anahtarlar bu commit'e girmez. GitHub dosyasındaki SHA koşullu güncellenir; yarış durumunda zorla üzerine yazılmaz.

Bu commit Vercel'in normal main dağıtımını başlatır. tools/build_vercel.cjs yalnızca yayınlanmış Supabase projeksiyonunu genel API anahtarıyla indirir, çok dilli sayfaları/sitemap'i üretir ve bağlantı/SEO/çıktı kontrollerini çalıştırır. Production bağlantısı eksikse derleme durur. Doğrulanmış statik dosyalar _site klasörüne alınır; server kaynakları, tools, data, Supabase SQL dosyaları ve gizli ortam değerleri statik siteye kopyalanmaz. api dizinindeki Node fonksiyonları Vercel tarafından ayrı derlenir.

Yayın anlık değildir. Vercel dağıtımını kontrol edin. Başarısız derlemede mevcut canlı sürüm korunur; veritabanındaki içerik ve taslak korunur. Başarısız yayın isteğinden sonra yeniden yükleyin ve tekrar yayınlayın.

Yeni ürünler üç koleksiyondan birine eklenebilir; üst sınır 200 üründür. Dört dilin alanları aktif ürün için zorunludur. Pasife alınan sayfalar kaldırılır; eski URL gerekiyorsa 301 yönlendirmesi ayrıca planlanmalıdır. Sayfa editörü ana sayfa/hakkımızda/rehber/iletişim başlığını, girişini ve SEO alanlarını düzenler; serbest HTML editörü değildir.
## 4. Teklifler: panel + mevcut mail

Önceki `/admin/api/quotes` bağlantısı kontrolde 404 dönüyordu. Bu sürüm aynı form yolunu yeni çift teslimat uç noktasına bağlar. Mail hizmetinin kimliği/SMTP bilgisi bilinmediğinden çalıştığı varsayılmaz.

Mail hizmeti doğrulanmadan form **başarı mesajı vermez**; 503 döner. Mevcut mail hesabının şifresi ve DNS kayıtları değiştirilmez. Çalışan hizmet için HTTPS JSON webhook adresi ve Bearer anahtarı `ENQUIRY_MAIL_WEBHOOK_URL` / `ENQUIRY_MAIL_WEBHOOK_SECRET` olarak bağlanmalıdır. Webhook mevcut alanları (`customerName,companyName,email,phone,notes,items`) ve `enquiryId` alır; hedef alıcı hizmet tarafında sabitlenmelidir. Kullanıcının adresi gönderici olarak kullanılmamalı, Reply-To olmalıdır. 2xx yanıtın anlamı hizmetin kabul ettiği teslimat olmalıdır; mail kutusuna gerçek teslim testi ayrıca şarttır.

Cloudflare Turnstile widget'ı oluşturun; yalnızca www.tvstextile.com alanına izin verin. `TURNSTILE_SITE_KEY` ve `TURNSTILE_SECRET_KEY` ekleyin. Form script'i ancak bağlantılar tamamlanınca doğrulamayı etkinleştirir. CAPTCHA doğrulanmadan veri veya mail gönderilmez. Mail denemesi önce panel kaydını oluşturur; teslim edilemeyen talepler panelde 'teslim edilemedi' olarak görünür. Yeniden gönderme/yinelenen mesaj deduplikasyonu bu sürümde yoktur; başarısızlık sonrası tekrar form göndermek ayrı kayıt oluşturabilir.

## Güvenlik ve gerçek ortam kabul kontrolleri

`npm test`, `npm audit`, mevcut site kontrolleri çalıştırılmalıdır. RLS ve Storage kuralları Supabase'e uygulandıktan sonra:

SQL Editor'da `supabase/security-check.sql` dosyasını çalıştırın. Anonim ve yönetici olmayan kullanıcıların taslak/mesaj okumasını ve yazmasını reddettiğini kontrol eder; işlemi rollback ile sonlandırır.

- Oturumsuz kullanıcı draft/teklif tablosunu okuyamamalı; normal Supabase kullanıcısı yönetici olamamalı.
- Yetkili hesap giriş, taslak kaydetme, yeni ürün/görsel yükleme ve çıkış akışını geçmeli.
- İki sekmede kayıt sürümü çakışması 409 vermeli; yönetici kaydı kaldırıldığında aktif oturum reddedilmeli.
- Yönetici ekleme yalnızca Supabase konsolunda olmalı; veritabanı RPC yetkileri ve anonim yayın projeksiyonu doğrulanmalı.
- Canlı yayın yeni ürünün dört URL'sini, hreflang ve sitemap'i oluşturmalı; mail testi hem kutuya hem panele ulaşmalı.
- SQL audit tablosu önceki içerik sürümlerini tutar; geri yükleme şu an SQL konsolundan yapılır. Düzenli veritabanı ve görsel yedekleri, uygun saklama politikası kurulmalıdır. Teklif kutusu son 100 kaydı gösterir.

Oturum 40 dakikayı veya sağlayıcı token süresini aşmaz. AES-GCM şifreli Secure/HttpOnly/SameSite çerez; CSRF ve kaynak kontrolü; her istekte kullanıcı/yetki doğrulama; kalıcı veritabanı tabanlı giriş limiti; SVG reddi, piksel ve dosya limiti, WebP dönüşümü; admin CSP ve no-store uygulanmıştır. RLS, private tekliflerin ve taslakların halka açık olmasını engeller. Supabase Storage yazma işlemleri sadece doğrulayan sunucuya açılır; mevcut görseller üzerine yazma/silme izni yoktur. Yetkili kullanıcının sağlayıcı API'sine kendi JWT'siyle doğrudan erişimi de RLS ile sınırlandırılır.

Sıfır güvenlik açığı garanti edilemez. Proje bağlantıları olmadan sağlayıcı RLS ve canlı hesap/mail testleri henüz doğrulanmış değildir.
