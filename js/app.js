/**
 * TVS Tekstil - Ana Uygulama
 * Genel site mantığı, header, mobil menü, scroll efektleri
 */
const App = {
    /**
     * Uygulamayı başlat
     */
    async init() {
        // i18n başlat
        await I18n.init();
        // Fetch products first
        if (typeof fetchProducts === 'function') {
            await fetchProducts();
        }

        // Nav kategorilerini dinamik yükle
        this.renderNavCategories();

        // Kategori ürünlerini render et (eğer kategori sayfasındaysa)
        if (typeof renderCategoryPageProducts === 'function') {
            renderCategoryPageProducts();
        }

        // Header scroll efekti
        this.initHeaderScroll();

        // Mobil menü
        this.initMobileMenu();

        // Dil seçici
        this.initLangSwitcher();

        // Hero slider (sadece ana sayfada)
        Slider.initHero();

        // Smooth scroll
        this.initSmoothScroll();

        // Intersection Observer animasyonları
        this.initScrollAnimations();
    },

    /**
     * Header scroll efekti - scroll'da gölge ekle
     */
    initHeaderScroll() {
        const header = document.getElementById('main-header');
        if (!header) return;

        let lastScroll = 0;

        window.addEventListener('scroll', () => {
            const currentScroll = window.pageYOffset;

            if (currentScroll > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }

            lastScroll = currentScroll;
        }, { passive: true });
    },

    /**
     * Mobil menü toggle
     */
    initMobileMenu() {
        const toggle = document.getElementById('mobile-menu-toggle');
        const nav = document.getElementById('main-nav');
        const overlay = document.getElementById('menu-overlay');

        if (!toggle || !nav) return;

        toggle.addEventListener('click', () => {
            const isOpen = nav.classList.toggle('open');
            toggle.classList.toggle('open');
            if (overlay) overlay.classList.toggle('open', isOpen);
            document.body.style.overflow = isOpen ? 'hidden' : '';
        });

        // Overlay tıklama
        if (overlay) {
            overlay.addEventListener('click', () => {
                nav.classList.remove('open');
                toggle.classList.remove('open');
                overlay.classList.remove('open');
                document.body.style.overflow = '';
            });
        }

        // Menü linklerine tıklayınca kapat
        nav.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                nav.classList.remove('open');
                toggle.classList.remove('open');
                if (overlay) overlay.classList.remove('open');
                document.body.style.overflow = '';
            });
        });
    },

    /**
     * Dil seçici butonları
     */
    initLangSwitcher() {
        document.querySelectorAll('.lang-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const lang = btn.getAttribute('data-lang');
                I18n.setLanguage(lang);
            });
        });
    },

    /**
     * Smooth scroll
     */
    initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                const targetId = anchor.getAttribute('href');
                if (targetId === '#') return;

                const target = document.querySelector(targetId);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    },

    /**
     * Scroll animasyonları (fade-in efekti)
     */
    initScrollAnimations() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });

        document.querySelectorAll('.animate-on-scroll').forEach(el => {
            observer.observe(el);
        });
    },

    /**
     * Newsletter form
     */
    initNewsletter() {
        const form = document.getElementById('newsletter-form');
        if (!form) return;

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const email = form.querySelector('input[type="email"]').value;
            if (email) {
                // TODO: Newsletter API entegrasyonu
                alert(I18n.t('footer.newsletter_success') || 'Subscription successful!');
                form.reset();
            }
        });
    },

    /**
     * Nav ve footer kategori linklerini products.js'deki categories dizisinden doldur
     */
    renderNavCategories() {
        if (typeof categories === 'undefined' || !categories.length) return;

        // Base path: kategori/ altındaki sayfalar için '../' prefix gerekli
        const navContainer = document.getElementById('nav-categories-list');
        const footerContainer = document.getElementById('footer-categories-list');
        const base = (navContainer || footerContainer)?.getAttribute('data-base') || '';

        const navLinks = categories.map(cat => {
            const label = (typeof I18n !== 'undefined' && I18n.translateCategory)
                ? I18n.translateCategory(cat.id)
                : cat.id;
            return `<a href="${base}products.html#${cat.id}" class="nav-dropdown-item">${label}</a>`;
        }).join('\n');

        const footerLinks = categories.map(cat => {
            const label = (typeof I18n !== 'undefined' && I18n.translateCategory)
                ? I18n.translateCategory(cat.id)
                : cat.id;
            return `<a href="${base}products.html#${cat.id}">${label}</a>`;
        }).join('\n');

        if (navContainer) navContainer.innerHTML = navLinks;
        if (footerContainer) footerContainer.innerHTML = footerLinks;
    }
};

// Sayfa yüklendiğinde başlat
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
