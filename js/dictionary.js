/**
 * TVS Tekstil - Ürün Sözlük Sistemi
 * Tekstil terimleri sözlüğü - her terim sadece 1 kez tanımlı
 * Türkçe temel dil, diğer diller sözlükten çevrilir
 */
const dictionary = {
  // === MALZEME TÜRLERİ ===
  "pamuk": { en: "Cotton", de: "Baumwolle", fr: "Coton" },
  "bambu": { en: "Bamboo", de: "Bambus", fr: "Bambou" },
  "organik": { en: "Organic", de: "Bio", fr: "Biologique" },
  "polyester": { en: "Polyester", de: "Polyester", fr: "Polyester" },
  "keten": { en: "Linen", de: "Leinen", fr: "Lin" },
  "modal": { en: "Modal", de: "Modal", fr: "Modal" },
  "mikrofiber": { en: "Microfiber", de: "Mikrofaser", fr: "Microfibre" },
  "muslin": { en: "Muslin", de: "Musselin", fr: "Mousseline" },
  "kadife": { en: "Velvet", de: "Samt", fr: "Velours" },
  "waffle": { en: "Waffle", de: "Waffel", fr: "Gaufre" },
  "bukle": { en: "Terry", de: "Frottee", fr: "Bouclette" },
  "jakarlı": { en: "Jacquard", de: "Jacquard", fr: "Jacquard" },
  "saten": { en: "Satin", de: "Satin", fr: "Satin" },
  "ranforce": { en: "Ranforce", de: "Ranforce", fr: "Ranforce" },
  "percale": { en: "Percale", de: "Perkal", fr: "Percale" },

  // === ÜRÜN TÜRLERİ ===
  "havlu": { en: "Towel", de: "Handtuch", fr: "Serviette" },
  "bornoz": { en: "Bathrobe", de: "Bademantel", fr: "Peignoir" },
  "paspas": { en: "Bath Mat", de: "Badematte", fr: "Tapis de bain" },
  "terlik": { en: "Slippers", de: "Hausschuhe", fr: "Pantoufles" },
  "kese": { en: "Bath Glove", de: "Waschhandschuh", fr: "Gant de bain" },
  "saç_bonesi": { en: "Hair Bonnet", de: "Haarhaube", fr: "Bonnet de bain" },
  "nevresim": { en: "Duvet Cover", de: "Bettbezug", fr: "Housse de couette" },
  "çarşaf": { en: "Bed Sheet", de: "Bettlaken", fr: "Drap" },
  "yastık": { en: "Pillow Case", de: "Kissenbezug", fr: "Taie d'oreiller" },
  "pike": { en: "Bedspread", de: "Tagesdecke", fr: "Couvre-lit" },
  "battaniye": { en: "Blanket", de: "Decke", fr: "Couverture" },
  "pijama": { en: "Pajamas", de: "Schlafanzug", fr: "Pyjama" },
  "sabahlık": { en: "Morning Gown", de: "Morgenmantel", fr: "Robe de chambre" },
  "şort": { en: "Shorts", de: "Shorts", fr: "Short" },
  "tişört": { en: "T-Shirt", de: "T-Shirt", fr: "T-shirt" },
  "elbise": { en: "Dress", de: "Kleid", fr: "Robe" },
  "tulum": { en: "Romper", de: "Strampler", fr: "Barboteuse" },
  "önlük": { en: "Bib", de: "Lätzchen", fr: "Bavoir" },
  "kundak": { en: "Swaddle", de: "Pucktuch", fr: "Emmaillotage" },
  "plaj_havlusu": { en: "Beach Towel", de: "Strandtuch", fr: "Serviette de plage" },
  "pareo": { en: "Pareo", de: "Pareo", fr: "Paréo" },
  "hamam": { en: "Hammam Towel", de: "Hamam-Tuch", fr: "Serviette de hammam" },
  "masa_örtüsü": { en: "Tablecloth", de: "Tischdecke", fr: "Nappe" },
  "runner": { en: "Table Runner", de: "Tischläufer", fr: "Chemin de table" },
  "peçete": { en: "Napkin", de: "Serviette", fr: "Serviette de table" },
  "perde": { en: "Curtain", de: "Vorhang", fr: "Rideau" },
  "yastık_kılıfı": { en: "Cushion Cover", de: "Kissenhülle", fr: "Housse de coussin" },

  // === NİTELİKLER ===
  "karışımlı": { en: "Blended", de: "Mischgewebe", fr: "Mélangé" },
  "baskılı": { en: "Printed", de: "Bedruckt", fr: "Imprimé" },
  "nakışlı": { en: "Embroidered", de: "Bestickt", fr: "Brodé" },
  "iplik_boyalı": { en: "Yarn Dyed", de: "Garnfärbung", fr: "Teint en fil" },
  "premium": { en: "Premium", de: "Premium", fr: "Premium" },
  "lüks": { en: "Luxury", de: "Luxus", fr: "Luxe" },
  "set": { en: "Set", de: "Set", fr: "Ensemble" },
  "bebek": { en: "Baby", de: "Baby", fr: "Bébé" },
  "çocuk": { en: "Kids", de: "Kinder", fr: "Enfants" },
  "takım": { en: "Set", de: "Set", fr: "Ensemble" },
  "yatak": { en: "Bed", de: "Bett", fr: "Lit" },

  // === EKLİ TÜRKÇE FORMLAR (takım → takımı gibi) ===
  "takımı": { en: "Set", de: "Set", fr: "Ensemble" },
  "seti": { en: "Set", de: "Set", fr: "Ensemble" },
  "havlusu": { en: "Towel", de: "Handtuch", fr: "Serviette" },
  "bornozı": { en: "Bathrobe", de: "Bademantel", fr: "Peignoir" },
  "çarşafı": { en: "Bed Sheet", de: "Bettlaken", fr: "Drap" },
  "örtüsü": { en: "Cover", de: "Bezug", fr: "Housse" },
  "kılıfı": { en: "Case", de: "Bezug", fr: "Taie" },
  "takımları": { en: "Set", de: "Set", fr: "Ensemble" },

  // === İNGİLİZCE KUMAŞ ADLARI (kullanıcı İngilizce girebilir) ===
  "cotton": { en: "Cotton", de: "Baumwolle", fr: "Coton" },
  "bamboo": { en: "Bamboo", de: "Bambus", fr: "Bambou" },
  "linen": { en: "Linen", de: "Leinen", fr: "Lin" },
  "polyester": { en: "Polyester", de: "Polyester", fr: "Polyester" },
  "satin": { en: "Satin", de: "Satin", fr: "Satin" },
  "velvet": { en: "Velvet", de: "Samt", fr: "Velours" },
  "muslin": { en: "Muslin", de: "Musselin", fr: "Mousseline" },
};

/**
 * Ürün adını seçili dile çevirir
 * @param {Object} product - Ürün objesi (name + tags)
 * @param {string} lang - Hedef dil kodu (en, de, fr)
 * @returns {string} Çevrilmiş ürün adı
 */
function translateProductName(product, lang) {
  if (lang === 'tr') return product.name;
  if (!product.tags || product.tags.length === 0) return product.name;

  const translated = product.tags.map(tag => {
    const entry = dictionary[tag];
    if (entry && entry[lang]) return entry[lang];
    return tag; // Sözlükte yoksa orijinalini göster
  });

  return translated.join(' ');
}

/**
 * Ürün açıklamasını seçili dile çevirir
 * @param {Object} product - Ürün objesi
 * @param {string} lang - Hedef dil kodu
 * @returns {string} Çevrilmiş açıklama
 */
function translateProductDescription(product, lang) {
  if (lang === 'tr') return product.description;
  if (!product.descTags || product.descTags.length === 0) return product.description;

  let result = product.descTemplate || '';
  product.descTags.forEach(tag => {
    const entry = dictionary[tag];
    const word = (entry && entry[lang]) ? entry[lang] : tag;
    result = result.replace(`{${tag}}`, word);
  });

  return result;
}

// Node.js ortamı için export
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    dictionary,
    translateProductName,
    translateProductDescription
  };
}
