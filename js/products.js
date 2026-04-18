/**
 * TVS Tekstil - Ürün Verileri (Admin Panel Tarafından Oluşturuldu)
 * Tarih: 25.02.2026 16:15:48
 */
const categories = [
    {
        "id": "home-textile",
        "name": "Home Textile",
        "icon": "📦",
        "image": "/img/uploads/1772020247663-186712405-0b11e90e-3aa9-4f9d-98e6-9438f52b9be4.webp"
    }
];

const products = [
    {
        "id": "7acc7990-513b-4fb4-971d-c1903b3bbbb8",
        "name": "Bed linen set",
        "tags": [
            "cotton",
            "bed linen",
            "set",
            "home-textile"
        ],
        "description": "Double size",
        "descTags": [
            "cotton",
            "bed linen",
            "set"
        ],
        "descTemplate": "Double size",
        "category": "home-textile",
        "price": 1000,
        "features": [
            "Cotton",
            "1_variants",
            "fast_shipping",
            "domestic"
        ],
        "image": "/img/uploads/1772020277727-555185618-0b11e90e-3aa9-4f9d-98e6-9438f52b9be4.webp",
        "images": [
            "/img/uploads/1772020277727-555185618-0b11e90e-3aa9-4f9d-98e6-9438f52b9be4.webp",
            "/img/uploads/1772022041909-273940588-WhatsApp-Image-2026-02-22-at-16.56.15.jpeg"
        ]
    }
];

/**
 * Ürünü kategoriye göre filtrele
 */
function getProductsByCategory(categoryId) {
    if (!categoryId || categoryId === 'all') return products;
    return products.filter(p => p.category === categoryId);
}

/**
 * Ürünü ID'ye göre bul
 * Updated to handle string UUIDs
 */
function getProductById(id) {
    return products.find(p => p.id == id);
}

/**
 * Benzer ürünleri getir
 */
function getRelatedProducts(product, limit = 4) {
    return products
        .filter(p => p.category === product.category && p.id !== product.id)
        .slice(0, limit);
}

// Node.js ortamı için export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        categories,
        products,
        getProductsByCategory,
        getProductById,
        getRelatedProducts
    };
}
