# TVS Textile — tasarım ve SEO yenilemesi

Tarih: 4 Ekim 2026. Çalışma yalnızca ana klasördeki tvstextile.com içindir. TVSTÜRKÇE dosyaları bu yenilemede değiştirilmedi. Yeni site henüz GitHub’a veya canlı yayına gönderilmedi.

## Yeni yapı

Sıcak açık renkler, bordo vurgu, büyük fotoğraflar ve serif başlıklarla kurumsal bir ihracat sitesi hazırlandı. Ana sayfa, şirket, koleksiyonlar, satın alma rehberi, iletişim ve hata sayfası yenilendi. Mobil menü, yumuşak giriş animasyonları, klavye odağı ve hareket azaltma tercihi desteklenir. Ana içerik JavaScript çalışmadan da HTML içinde bulunur.

İngilizce ana dizindedir. Fransızca `/fr/`, Almanca `/de/`, İspanyolca `/es/` altındadır. Her dilde üç ana koleksiyon ve aşağıdaki 12 ürün sayfası bulunur. Toplam 85 HTML sayfası doğrulandı. Çok dilli metinler yayın öncesi ticari terminoloji açısından firma ve ana dil editörü tarafından gözden geçirilmelidir.

| Türkçe ürün | İngilizce sayfa | Fransızca terim | Almanca terim | İspanyolca terim |
|---|---|---|---|---|
| Müslin nevresim | `/collections/muslin-duvet-covers.html` | Gaze de coton housse de couette | Musselin Bettwäsche | Fundas nórdicas de muselina |
| Çarşaf | `/collections/fitted-sheets.html` | Drap housse | Spannbettlaken | Sábanas bajeras |
| Nevresim | `/collections/duvet-covers.html` | Housse de couette | Bettbezüge | Fundas nórdicas |
| Bornoz | `/collections/bathrobes.html` | Peignoir | Bademäntel | Albornoces |
| Havlu | `/collections/towels.html` | Serviettes de bain | Handtücher | Toallas |
| Sauna eteği | `/collections/sauna-wraps.html` | Kilts de sauna | Saunakilts | Pareos de sauna |
| Saç bandı | `/collections/spa-headbands.html` | Bandeaux de spa | Spa Stirnbänder | Diademas de spa |
| Makyaj temizleme mendili | `/collections/makeup-remover-cloths.html` | Lingettes démaquillantes | Abschminktücher | Toallitas desmaquillantes |
| Panço | `/collections/baby-ponchos.html` | Ponchos bébé | Baby Ponchos | Ponchos para bebé |
| Kundak | `/collections/baby-swaddles.html` | Langes bébé | Baby Pucktücher | Muselinas para bebé |
| Uyku tulumu | `/collections/baby-sleeping-bags.html` | Gigoteuses bébé | Baby Schlafsäcke | Sacos de dormir para bebé |
| Uyku arkadaşı | `/collections/baby-comforters.html` | Doudou | Baby Schmusetücher | Dou dou para bebé |

Dil sayfaları aynı dosya yolunun dil önekiyle bulunur; örneğin `/fr/collections/muslin-duvet-covers.html`. Çarşaf, verilen Fransızca “drap housse” terimine göre lastikli çarşaf olarak ele alındı. Düz çarşaf da satılıyorsa ayrı ve gerçek ürün bilgisiyle genişletilmeli.

## Düzeltilen SEO ve teknik sorunlar

- Canlı `https://www.tvstextile.com/` sayfası kontrol sırasında canonical olarak yanlış `https://www.tvstekstil.com/` adresini gösteriyordu. Yeni sayfalar kendi tvstextile.com adreslerine işaret ediyor.
- Hem www’li hem www’siz adresler 200 yanıtı veriyordu. Vercel yapılandırmasına www’siz hosttan `https://www.tvstextile.com` adresine kalıcı yönlendirme eklendi. Canlı etkisi yayın sonrası doğrulanmalı.
- Sitemap ve robots içindeki domain tutarsızlıkları ve bozuk XML görsel URL’si giderildi. Yeni sitemap mevcut, indekslenebilir sayfaları içeriyor; boş eski dinamik detay sayfalarını içermiyor.
- Yanlış `lang="fr"` etiketleri yerine gerçek sayfa dili kullanılıyor. Karşılıklı hreflang, x-default ve her dilde kendine işaret eden canonical eklendi.
- Ürünlere ayrı başlık, meta açıklaması, görünür H1, kategori ilişkileri ve ürün brief’i metinleri eklendi. Anahtar kelime yığılması kullanılmadı.
- Organization, WebSite, WebPage, CollectionPage, ItemList ve BreadcrumbList verileri eklendi. Sertifika, yıldız puanı, sahte müşteri yorumu, fiyat veya stok bilgisi uydurulmadı.
- Eski kategori adresleri yeni koleksiyonlara kalıcı yönlendirme kurallarıyla eşlendi. Apache için `.htaccess`, Vercel için `vercel.json` hazırlandı.
- Eski boş blog yerine gerçek bir satın alma rehberine bağlantı verildi. Sahte yazı listesi kullanılmadı.
- Yerel `.private`, ZIP ve geliştirme araçlarının Vercel dağıtımına girmemesi için `.vercelignore` eklendi. Türkçe klasör ayrı site olduğu için bu dağıtımdan dışlandı.

## Mail ve form: mevcut hizmet korundu

Kullanıcının talebiyle mail hizmeti, kimlik bilgileri ve sunucu ayarları değiştirilmedi. Yeni form aynı `/admin/api/quotes` adresine POST yapar. Mevcut JSON sözleşmesi korunur:

`customerName`, `companyName`, `email`, `phone`, `notes`, `items`

`items` mevcut sistemdeki gibi `Iletisim Formu Mesaji` olarak gönderilir. Yeni ürün, ülke ve miktar alanları notes içine eklenir. E-posta uygulaması açma davranışı kullanılmaz. Başarı yalnızca API başarılı yanıt verdiğinde gösterilir; hata halinde girilen bilgiler korunur.

Eski HTML’de ayrıca kullanılmayan bir Formspree PLACEHOLDER action vardı. Aktif JavaScript ise `/admin/api/quotes` kullanıyordu; yeni form aktif hizmeti korur. Bu klasörde API sunucusunun kodu bulunmaması canlı hizmetin çalışmadığını kanıtlamaz. Önceki incelemede bu ayrım eksikti.

Gerçek mail gönderimi yapılmadı. API anahtarları, DNS mail kayıtları ve servis ayarları incelenmedi veya değiştirilmedi. Test, taklit yanıtlarla aynı endpoint ve veri sözleşmesinin korunmasını doğruladı. Yayın sonrası mevcut mail hizmetinde tek bir kontrollü gönderim kullanıcı tarafından kontrol edilebilir.

## Otorite için tamamlanması gereken gerçek bilgiler

Teknik SEO ve doğru şirket verileri temel oluşturur; arama görünürlüğü veya müşteri sayısı garanti değildir. Google, kullanıcıya yardımcı ve güvenilir içeriği önemser. Gerçek üretim fotoğrafları, ölçülebilir ürün bilgileri ve doğrulanabilir şirket bilgisi içerikleri güçlendirmek için gereklidir.

Şu bilgiler doğrulanınca sayfalara eklenmeli:

1. Gerçek fabrika, ekip, üretim ve ürün fotoğrafları. Şu anki fotoğraflar kategori atmosferi için mevcut dosyalardan kullanılıyor; katalog ürünü veya fabrika kanıtı olarak sunulmuyor.
2. Gerçek kumaş bileşimi, GSM, ölçüler, MOQ, üretim süresi ve sevkiyat koşulları. Şimdilik bunlar müşterinin görüşeceği brief bilgileri olarak yer alır.
3. Geçerli sertifikalar: kurum, belge numarası, kapsam ve doğrulama bağlantısı. Sürdürülebilirlik veya bebek güvenliği belgelenmeden iddia edilmedi.
4. Yayın izni alınmış müşteri referansları ve gerçek proje örnekleri.
5. Firmanın mevcut resmi sosyal profil adresleri ve ticari kimliği. Bilinmeyen profil veya unvan uydurulmadı.
6. Search Console üzerinden domain doğrulaması, sitemap gönderimi ve indeksleme kontrolü. Hesap erişimi olmadan yapılmadı.
7. İlgili ticaret kuruluşları, fuarlar, gerçek distribütörler ve sektör yayınlarından hak edilmiş bağlantılar. Dış site otoritesi bir HTML ayarıyla üretilemez.

## Kontrol ve yayın

- `python tools/build_corporate.py`: ortak kaynak dosyasından siteyi yeniden üretir.
- `python tools/check_corporate.py`: 85 sayfada H1, meta açıklaması, canonical, yerel bağlantı, hreflang hedefleri, JSON-LD ve sitemap doğrulaması geçti.
- `node tools/check_enquiry.cjs`: mevcut form endpoint’i ve payload, başarı/hata/validasyon ve ürün seçimi testleri geçti. Gerçek mesaj göndermedi.
- `node --check js/corporate.js` ve `git diff --check` geçti.
- Tarayıcıda 1440px masaüstü ve 390px mobil görünüm, mobil menü, Fransızca ürün sayfası ve ürünün teklif formuna seçili gelmesi kontrol edildi. Yatay taşma görülmedi.
- Apache/Vercel yönlendirmeleri yapılandırmaya eklendi ancak yerel Python sunucusu bunları uygulamaz; dağıtım sonrası HTTP yanıtları kontrol edilmeli.
- Lighthouse puanı, organik sıralama ve gerçek mail teslimatı ölçülmedi. Bunlar başarılı kabul edilmedi.
- `.private/config.json`, mevcut mail hizmeti ve `TVSTÜRKÇE` bu tasarım çalışmasında değiştirilmedi.

## Her dilde SEO bağlantılarının güçlendirilmesi

İngilizce, Fransızca, Almanca ve İspanyolca için kategori ve ürün sayfalarına yerel dilde bağlam metinleri eklendi. Ana sayfa, şirket sayfası ve satın alma rehberi aynı dilde üç koleksiyona ve 12 ürünün tamamına bağlantı verir. Ürün sayfaları ilgili ürünlere ve satın alma rehberine bağlanır; kendi sayfasına giden gereksiz ürün kartı kaldırıldı. Böylece ana sayfadan başlayan tarama tüm indekslenebilir sayfalara ulaşır.

Ürün sayfalarında görünür `Ana sayfa → Koleksiyonlar → Kategori → Ürün` yolu ve aynı hiyerarşiye sahip BreadcrumbList vardır. Sayfa bağlantılarının metinleri gerçek ürün ve rehber adlarını içerir. Meta açıklamaları ürünün malzeme, ölçü, kullanım veya bakım gereksinimini konu alan özgün brief cümlesiyle güncellendi. İletişim, koleksiyonlar ve rehber başlıkları her dilde yerelleştirildi. Fotoğraf alt metinleri ve Open Graph dil bilgileri de yerelleştirildi.

Sitemap, HTML canonical adreslerinden oluşturulur ve her çok dilli sayfa için İngilizce, Fransızca, Almanca, İspanyolca ve x-default eşleşmelerini içerir. Sitemap ile HTML içindeki eşleşmeler birebir kontrol edilir. Eski, içeriksiz blog giriş sayfası noindex olarak tutuldu; rehber ve gerçek ürün sayfaları indekslenebilir.

`python tools/check_multilingual_seo.py` kontrol sonucu:

- 81 indekslenebilir URL: İngilizce 21, diğer üç dilde 20’şer sayfa. İngilizcedeki ek sayfa iletişim verileri açıklamasıdır.
- Ana sayfadan 81 URL’nin tamamına yerel HTML bağlantılarıyla ulaşılır.
- Her dilde başlık ve açıklamalar benzersizdir.
- HTML ve sitemap hreflang eşleşmeleri karşılıklıdır; eksik dil hedefi ve bağlantısız indekslenebilir sayfa yoktur.
- Mevcut mail API’si değiştirilmedi; mail sözleşmesi testleri tekrar geçti.

Bu çalışma site içi bağlantılardır. Üçüncü taraf sitelerden backlink yayımlanmadı, satın alınmadı veya müşteri adına mesaj gönderilmedi. Harici otorite için gerçek sektör ilişkileri ve doğrulanabilir referanslar gerekir.

## Firma ağzıyla içerik ve gerçek bilgiler

Kullanıcı tarafından doğrulanan bilgiler: TVS Textile 2021’de kuruldu; Akçeşme M. 2605 Sk. No: 40 Merkezefendi, Denizli adresindeki kendi fabrikasında üretim yapıyor. Şu an sertifikası bulunmuyor. Fransa, Almanya, Hollanda, İspanya ve Amerika Birleşik Devletleri hedef pazarlardır; bunlar mevcut müşteri listesi veya tamamlanmış ihracat referansı olarak sunulmadı.

48 ürün metni dört dilde firma ağzıyla yeniden yazıldı. Her ürünün ana anlatımı farklıdır: doku, yatak yüksekliği, kapama, robe kalıbı, towel formatları, sauna kapanışı, spa bandı kullanımı, bez yüzeyi, panço ölçüsü, kundak kullanım tanımı, uyku tulumu test gereksinimi ve doudou tasarım ayrıntıları ürününe göre ele alınır. Bunlar uydurulmuş müşteri hikâyeleri veya yaşanmış fabrika tecrübeleri olarak anlatılmaz; şirketin alıcıyla konuşacağı somut ürün konularıdır.

Ortak kategori paragrafları her ürün sayfasına tekrar eklenmez. Ürün açıklamaları, kategori anlatımı, şirket sayfası, rehber ve meta açıklamaları birinci çoğul şahısla düzenlendi. Navigasyon, adres, bağlantı listeleri ve teklif çağrıları gibi gerekli ortak site öğeleri korunur. Çeviriler aynı gerçekleri anlatır; farklı dillerde sahte hikâyeler üretilmedi.

İndekslenebilir 81 sayfada görünür içerik tarihi **4 Ekim 2026** olarak yer alır. WebPage/CollectionPage `dateModified` ve sitemap `lastmod` aynı gerçek düzenleme tarihini kullanır. Henüz yayınlanmamış sayfalar için yayın tarihi veya geçmiş tarihli makale uydurulmadı. Tarih kaynak dosyasında sabittir; yeniden derlemek veya sayfayı açmak tarihi ileri taşımaz. Sonraki gerçek içerik güncellemesinde editör tarafından değiştirilmeli.

`python tools/check_editorial.py` ana ürün paragraflarının birebir tekrarını, aynı dilde uzun ifade örtüşmesini ve tarih uyumunu kontrol eder. Bu yerel kontrol dünya genelinde intihal taraması veya Google sıralama garantisi değildir. İçerik yayınlanmadan önce fabrika/ürün bilgisi ve dil terminolojisi firma tarafından gözden geçirilmelidir.

Google’ın yaklaşımı, yalnızca “biz” kullanmak veya tarihi yenilemek değil, faydalı ve güvenilir içerik sunmaktır. Fabrika fotoğrafları ve doğrulanabilir ürün verileri geldikçe ilgili sayfalar daha somut hale getirilebilir.

## Kaynaklar

- [Google: çok dilli sayfalar ve hreflang](https://developers.google.com/search/docs/specialty/international/localized-versions)
- [Google: taranabilir bağlantılar ve açıklayıcı bağlantı metinleri](https://developers.google.com/search/docs/crawling-indexing/links-crawlable)
- [Google: faydalı ve güvenilir içerik](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
- [Google: başlık bağlantıları](https://developers.google.com/search/docs/appearance/title-link)
- [Google: yapay zekâ ile hazırlanan içerik ve kalite](https://developers.google.com/search/blog/2023/02/google-search-and-ai-content)
- [Google: faydalı, güvenilir ve özgün içerik](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)
