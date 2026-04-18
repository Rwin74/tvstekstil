/**
 * TVS Tekstil - Hero Slider & Ürün Carousel
 * Full-page vertical slider (ana sayfa) + Ürün görsel carousel
 */
const Slider = {
    currentSlide: 0,
    totalSlides: 0,
    isAnimating: false,
    autoPlayInterval: null,

    /**
     * Hero slider'ı başlat
     */
    initHero() {
        const slider = document.getElementById('hero-slider');
        if (!slider) return;

        const slides = slider.querySelectorAll('.hero-slide');
        this.totalSlides = slides.length;
        if (this.totalSlides === 0) return;

        // İlk slide'ı aktif yap
        slides[0].classList.add('active');
        this.updateDots();

        // Otomatik geçiş
        this.startAutoPlay();

        // Tıklama ile kontrol
        this.bindHeroControls();

        // Touch desteği
        this.bindTouchEvents(slider);
    },

    /**
     * Slide'ı göster
     */
    goToSlide(index) {
        if (this.isAnimating) return;

        const slider = document.getElementById('hero-slider');
        if (!slider) return;

        const slides = slider.querySelectorAll('.hero-slide');
        if (index < 0) index = this.totalSlides - 1;
        if (index >= this.totalSlides) index = 0;

        this.isAnimating = true;

        // Mevcut slide'ı gizle
        slides[this.currentSlide].classList.remove('active');
        slides[this.currentSlide].classList.add('leaving');

        // Yeni slide'ı göster
        this.currentSlide = index;
        slides[this.currentSlide].classList.add('active');

        setTimeout(() => {
            slides.forEach(s => s.classList.remove('leaving'));
            this.isAnimating = false;
        }, 600);

        this.updateDots();
    },

    /**
     * Sonraki slide
     */
    next() {
        this.goToSlide(this.currentSlide + 1);
        this.restartAutoPlay();
    },

    /**
     * Önceki slide
     */
    prev() {
        this.goToSlide(this.currentSlide - 1);
        this.restartAutoPlay();
    },

    /**
     * Dotsları güncelle
     */
    updateDots() {
        const dots = document.querySelectorAll('.hero-dot');
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === this.currentSlide);
        });
    },

    /**
     * Otomatik geçiş başlat
     */
    startAutoPlay() {
        this.autoPlayInterval = setInterval(() => this.next(), 5000);
    },

    /**
     * Otomatik geçişi yeniden başlat
     */
    restartAutoPlay() {
        clearInterval(this.autoPlayInterval);
        this.startAutoPlay();
    },

    /**
     * Hero kontrol butonlarını bağla
     */
    bindHeroControls() {
        const prevBtn = document.getElementById('hero-prev');
        const nextBtn = document.getElementById('hero-next');

        if (prevBtn) prevBtn.addEventListener('click', () => this.prev());
        if (nextBtn) nextBtn.addEventListener('click', () => this.next());

        // Dot tıklama
        document.querySelectorAll('.hero-dot').forEach((dot, i) => {
            dot.addEventListener('click', () => {
                this.goToSlide(i);
                this.restartAutoPlay();
            });
        });

        // Klavye kontrolü
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight' || e.key === 'ArrowDown') this.next();
            if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') this.prev();
        });
    },

    /**
     * Touch/Swipe ve Mouse Drag desteği
     */
    bindTouchEvents(element) {
        let startY = 0;
        let startX = 0;
        let isDragging = false;

        // Touch Events
        element.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            startX = e.touches[0].clientX;
            isDragging = true;
            this.stopAutoPlay(); // Drag başlarken autoplay durdur
        }, { passive: true });

        element.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            const diffY = startY - e.changedTouches[0].clientY;
            const diffX = startX - e.changedTouches[0].clientX;
            this.handleSwipe(diffX, diffY);
            isDragging = false;
            this.startAutoPlay(); // Bırakınca tekrar başlat
        }, { passive: true });

        // Mouse Events
        element.addEventListener('mousedown', (e) => {
            startY = e.clientY;
            startX = e.clientX;
            isDragging = true;
            element.style.cursor = 'grabbing';
            this.stopAutoPlay();
            e.preventDefault(); // Metin seçimini engelle
        });

        element.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
        });

        element.addEventListener('mouseup', (e) => {
            if (!isDragging) return;
            const diffY = startY - e.clientY;
            const diffX = startX - e.clientX;
            this.handleSwipe(diffX, diffY);
            isDragging = false;
            element.style.cursor = '';
            this.startAutoPlay();
        });

        element.addEventListener('mouseleave', () => {
            if (isDragging) {
                isDragging = false;
                element.style.cursor = '';
                this.startAutoPlay();
            }
        });
    },

    /**
     * Swipe yönüne göre aksiyon al
     */
    handleSwipe(diffX, diffY) {
        // Yatay kaydırma daha baskınsa (horizontal slider için)
        // Dikey slide için Y eksenine bakıyoruz
        // Hero slider genelde dikey (mouse wheel) veya yatay (dots) olabilir.
        // CSS'e bakılırsa hero-slider dikey mi yatay mı?
        // Genelde hero sliderlar yataydır. Kodda 'leaving' class'ı var.

        // Eğer yatay swipe ise (X farkı Y farkından büyükse)
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
            if (diffX > 0) this.next(); // Sola sürükle -> Sonraki
            else this.prev();           // Sağa sürükle -> Önceki
        }
    },

    /**
     * Otomatik geçişi durdur
     */
    stopAutoPlay() {
        clearInterval(this.autoPlayInterval);
    },
};

/**
 * Ürün Görsel Carousel (Kategori sayfalarındaki ürün detay)
 */
const ProductCarousel = {
    currentImage: 0,

    init(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const images = container.querySelectorAll('.carousel-image');
        if (images.length === 0) return;

        images[0].classList.add('active');
        this.updateCarouselDots(containerId);
    },

    goTo(containerId, index) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const images = container.querySelectorAll('.carousel-image');
        if (index < 0) index = images.length - 1;
        if (index >= images.length) index = 0;

        images.forEach(img => img.classList.remove('active'));
        images[index].classList.add('active');
        this.currentImage = index;
        this.updateCarouselDots(containerId);
    },

    next(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const images = container.querySelectorAll('.carousel-image');
        this.goTo(containerId, (this.currentImage + 1) % images.length);
    },

    prev(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const images = container.querySelectorAll('.carousel-image');
        this.goTo(containerId, (this.currentImage - 1 + images.length) % images.length);
    },

    updateCarouselDots(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const dots = container.querySelectorAll('.carousel-dot');
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === this.currentImage);
        });
    }
};
