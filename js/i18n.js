/**
 * TVS Tekstil - i18n (Internationalization) Motor
 * Sayfa yüklendiğinde sadece 1 dil dosyası yüklenir
 * data-i18n attribute ile otomatik çeviri
 */
const I18n = {
    currentLang: 'en',
    fallbackLang: 'en',
    translations: {},
    supportedLangs: ['en', 'de', 'fr'],
    langNames: {
        en: 'English',
        de: 'Deutsch',
        fr: 'Français'
    },
    langFlags: {
        en: '🇬🇧',
        de: '🇩🇪',
        fr: '🇫🇷'
    },
    /**
     * i18n motorunu başlat
     */
    async init() {
        // localStorage'dan dil tercihini al
        const saved = localStorage.getItem('tvs_lang');
        if (saved && this.supportedLangs.includes(saved)) {
            this.currentLang = saved;
        }

        // Dil dosyasını yükle
        await this.loadLanguage(this.currentLang);

        // Sayfayı çevir
        this.translatePage();

        // Dil seçici butonlarını güncelle
        this.updateLangSwitcher();

        // Statik ürün sayfaları için çeviri (Eğer kayıtlı dil TR değilse)
        this.translateProductDetail();

        // HTML lang attribute
        document.documentElement.lang = this.currentLang;
        console.log(this.currentLang);
    },

    /**
     * Dil dosyasını yükle
     */
    async loadLanguage(lang) {
        try {
            const basePath = this.getBasePath();
            const response = await fetch(`${basePath}lang/${lang}.json`);
            if (!response.ok) throw new Error(`Language file not found: ${lang}`);
            this.translations = await response.json();
            this.currentLang = lang;
        } catch (error) {
            console.error('Language load error:', error);
            // Fallback: Fransızca
            if (lang !== 'fr') {
                await this.loadLanguage('fr');
            }
        }
    },

    /**
     * Base path hesapla (alt dizinlerdeki sayfalar için)
     */
    getBasePath() {
        const path = window.location.pathname;
        // Eğer alt dizinlerdeyse bir üst dizine çık
        if (path.includes('/pages/') || path.includes('/urun/') || path.includes('/kategori/')) {
            return '../';
        }
        return './';
    },

    /**
     * Dil değiştir
     */
    async setLanguage(lang) {
        if (!this.supportedLangs.includes(lang)) return;

        localStorage.setItem('tvs_lang', lang);
        await this.loadLanguage(lang);
        this.translatePage();
        this.updateLangSwitcher();
        document.documentElement.lang = lang;

        // Ürün kartlarını yeniden render et (eğer varsa)
        if (typeof renderProducts === 'function') {
            renderProducts();
        }

        // Hero slider'ı yeniden render et (dil değişince başlık/alt başlık güncellenir)
        if (typeof renderHeroSlider === 'function') {
            renderHeroSlider();
        }

        // Kategori grid'ini yeniden render et
        if (typeof renderCategories === 'function') {
            renderCategories();
        }

        // Ürün detay sayfasını güncelle
        if (typeof renderProductDetail === 'function') {
            renderProductDetail();
        }

        // Statik ürün sayfaları için çeviri
        this.translateProductDetail();
    },

    /**
     * Sayfadaki tüm data-i18n elementlerini çevir
     */
    translatePage() {
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            const text = this.t(key);
            if (text) {
                el.textContent = text;
            }
        });

        // Placeholder çevirileri
        const placeholders = document.querySelectorAll('[data-i18n-placeholder]');
        placeholders.forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            const text = this.t(key);
            if (text) {
                el.placeholder = text;
            }
        });

        // Title çevirileri
        const titles = document.querySelectorAll('[data-i18n-title]');
        titles.forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            const text = this.t(key);
            if (text) {
                el.title = text;
            }
        });
    },

    /**
     * Çeviri al (nested key desteği: "nav.about")
     */
    t(key) {
        const keys = key.split('.');
        let result = this.translations;

        for (const k of keys) {
            if (result && typeof result === 'object' && k in result) {
                result = result[k];
            } else {
                return key; // Çeviri bulunamadı, key'i döndür
            }
        }

        return result;
    },

    /**
     * Dil seçici butonlarını güncelle
     */
    updateLangSwitcher() {
        // Aktif dili vurgula
        document.querySelectorAll('.lang-btn').forEach(btn => {
            const lang = btn.getAttribute('data-lang');
            btn.classList.toggle('active', lang === this.currentLang);
        });

        // Mobil dil seçici
        const mobileLangSelect = document.getElementById('mobile-lang-select');
        if (mobileLangSelect) {
            mobileLangSelect.value = this.currentLang;
        }
    },

    /**
     * Ürün adını çevir (dictionary.js kullanır)
     */
    translateProduct(product) {
        if (typeof translateProductName === 'function') {
            return translateProductName(product, this.currentLang);
        }
        return product.name;
    },

    /**
     * Ürün açıklamasını çevir
     */
    translateProductDesc(product) {
        if (typeof translateProductDescription === 'function') {
            return translateProductDescription(product, this.currentLang);
        }
        return product.description;
    },

    /**
     * Kategori adını çevir
     */
    translateCategory(categoryId) {
        // First try to get name from the categories array (loaded from products.js)
        if (typeof categories !== 'undefined' && Array.isArray(categories)) {
            const cat = categories.find(c => c.id === categoryId);
            if (cat && cat.name) return cat.name;
        }
        // Fallback: i18n key
        const translated = this.t(`categories.${categoryId}`);
        // If translation key returned equals the full key string, just show the id
        return (translated === `categories.${categoryId}`) ? categoryId : translated;
    },

    /**
     * Statik ürün detay sayfasındaki dinamik alanları çevir
     */
    translateProductDetail() {
        // Ürün adı elementini bul
        const nameEl = document.getElementById('product-name');
        if (!nameEl) return;

        // Product ID'yi al
        const pid = nameEl.getAttribute('data-product-id');
        if (!pid) return;

        // Global products dizisinden ürünü bul
        // Not: products.js sayfa başında yüklendiği için window.products veya products erişilebilir olmalı
        const product = (typeof products !== 'undefined' ? products : []).find(p => p.id == pid);
        if (!product) return;

        // Çevirileri uygula
        const translatedName = this.translateProduct(product);
        const translatedDesc = this.translateProductDesc(product);

        // DOM güncelle
        nameEl.textContent = translatedName;
        document.title = `${this.t('site_name') || 'TVS Textile'} | ${translatedName}`;

        const descEl = document.getElementById('product-desc');
        if (descEl) descEl.textContent = translatedDesc;

        // Görsel alt etiketlerini güncelle
        const mainImg = document.getElementById('main-image');
        if (mainImg) mainImg.alt = translatedName;

        document.querySelectorAll('.product-gallery-thumb').forEach(img => {
            img.alt = translatedName;
        });
    }
};
