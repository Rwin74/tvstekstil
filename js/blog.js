/**
 * TVS Tekstil - Blog Verileri (Admin Panel Tarafından Oluşturuldu)
 * Tarih: 25.02.2026 16:15:48
 */
const blogPosts = [];

/**
 * Slug'a göre yazı getir
 */
function getPostBySlug(slug) {
    return blogPosts.find(p => p.slug === slug);
}

// Node.js ortamı için export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        blogPosts,
        getPostBySlug
    };
}
