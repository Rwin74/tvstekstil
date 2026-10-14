"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl = value => { try { const u = new URL(value); return ["https:", "http:"].includes(u.protocol) ? u.href : ""; } catch { return ""; } };
const domain = value => { try { return new URL(value).hostname.replace(/^www\./, ""); } catch { return "Web sitesi eklenmedi"; } };
const domainKey = value => { try { const u = new URL(value); const host = u.hostname.replace(/^www\./, ""); return ["instagram.com", "facebook.com", "etsy.com"].includes(host) ? host + "/" + (u.pathname.split("/").filter(Boolean)[0] || "").toLowerCase() : host; } catch { return ""; } };
const fold = value => String(value).toLocaleLowerCase("tr-TR").replaceAll("ı", "i").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const statuses = {research:"Araştırılacak", qualified:"Uygun", contacted:"İletişime geçildi", replied:"Yanıt geldi", not_suitable:"Uygun değil"};
const fits = {unknown:"Belirsiz", possible:"Olası eşleşme", confirmed:"Doğrulandı", no:"Uygun değil"};
const countries = {FR:"Fransa", TR:"Türkiye", DE:"Almanya", GB:"Birleşik Krallık", US:"ABD", IT:"İtalya", ES:"İspanya", NL:"Hollanda", BE:"Belçika", CH:"İsviçre"};
const opportunities = {unknown:"İncelenmedi",potential:"Butik adayı",multibrand:"Çok markalı seçki",supplier_invitation:"Tedarikçi başvuru ifadesi"};
const buyerTypes = {unknown:"Belirsiz",boutique:"Butik",multibrand:"Çok markalı butik",concept:"Konsept mağaza",retailer:"Perakende mağaza"};
const assessmentFields = ["buyer_type","opportunity","priority","reasons","assessment","assessed_at","supplier_evidence","supplier_source","discovery_mode"];
const labels = {prospects:"Potansiyel alıcılar",discover:"Ürünle butik bul", saved:"Firma listem", history:"Arama geçmişi", settings:"Ayarlar ve yedekleme"};
const state = {view:"discover", mode:"product", leads:[], results:[], history:[], selected:new Set(), settings:null, request:null, hasMore:false, busy:false, editing:null, drawerSnapshot:"", editToken:0};
let toastTimer;
let adminCsrf = "";

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 115000);
  try {
    const response = await fetch(path.startsWith("/api/") ? "/admin/butik-api/" + path.slice(5) : path, {...options, signal:controller.signal, headers:{"Content-Type":"application/json", "X-App-Request":"FirmaAtlas", "X-CSRF-Token":adminCsrf, ...options.headers}});
    if (response.status === 401 && path !== "/api/login") { showLogin(); throw new Error("Oturumunuz sona erdi. Yeniden giriş yapın."); }
    if (!response.ok) {
      let message = "İşlem tamamlanamadı. Lütfen tekrar deneyin.";
      try { const data = await response.json(); if (typeof data.detail === "string") message = data.detail; } catch {}
      throw new Error(message);
    }
    return options.raw ? response : await response.json();
  } catch (e) {
    if (e.name === "AbortError") throw new Error("İşlem zaman aşımına uğradı. Kaydetme yaptıysanız tekrar denemeden önce listeyi yenileyin.");
    if (e instanceof TypeError) throw new Error("Uygulamayla bağlantı kurulamadı. Bağlantınızı kontrol edin.");
    throw e;
  } finally { clearTimeout(timer); }
}

function toast(message, error = false) {
  clearTimeout(toastTimer); $("#toast").textContent = message;
  $("#toast").classList.remove("hidden"); $("#toast").classList.toggle("error", error);
  toastTimer = setTimeout(() => $("#toast").classList.add("hidden"), error ? 9000 : 4500);
}
function errorAt(id, message = "") { $(id).textContent = message; $(id).classList.toggle("hidden", !message); }
async function buttonTask(button, task) {
  if (button.disabled) return;
  button.disabled = true;
  try { await task(); } catch (error) { toast(error.message, true); } finally { button.disabled = false; }
}
function confirmAction(title, text, yes = "Onayla") {
  return new Promise(resolve => {
    const dialog = $("#confirm-dialog");
    $("#confirm-title").textContent = title; $("#confirm-text").textContent = text; $("#confirm-yes").textContent = yes;
    const finish = value => { dialog.close(); resolve(value); };
    $("#confirm-yes").onclick = () => finish(true); $("#confirm-no").onclick = () => finish(false);
    dialog.oncancel = event => { event.preventDefault(); finish(false); };
    dialog.showModal();
  });
}
async function switchView(view) {
  if (state.busy) { toast("Araştırma sürüyor; tamamlandığında ekran değiştirebilirsiniz."); return; }
  const wasDiscovery = ["discover","prospects"].includes(state.view);
  const changedDiscovery = ["discover","prospects"].includes(view) && state.view !== view;
  state.view = view;
  $$(".view").forEach(el => el.classList.toggle("hidden", el.id !== `view-${view === "prospects" ? "discover" : view}`));
  $$(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === view));
  $("#breadcrumb-title").textContent = labels[view];
  if (view === "discover" || view === "prospects") {
    const potential = view === "prospects";
    setMode(potential ? "prospects" : "product");
    $("#discovery-title").innerHTML = potential ? "Yeni alıcı potansiyelleri<span>.</span>" : "Ürününüze uygun butikler<span>.</span>";
    $("#discovery-description").textContent = potential ? "Anahtar kelime yazmadan bölgenizdeki butik ve çok markalı mağazaları keşfedin." : "Satmak istediğiniz ürünü yazın; perakende alıcı adaylarını kanıtlarıyla keşfedin.";
    $("#search-panel-title").textContent = potential ? "Bölgeyi seçin, potansiyelleri keşfedin" : "Hedef alıcınızı bulun";
    if (changedDiscovery) { state.results=[];state.request=null;state.selected.clear();$("#results-count").textContent="0";$("#search-results").innerHTML=empty("Hedef bölgenizdeki butiklere ulaşın",potential ? "Ürün bilgisi gerekmez. Kategori seçimi isteğe bağlıdır." : "Ürün anahtar kelimenizi girip aramayı başlatın.");$("#results-subtitle").textContent="";$("#result-page").textContent="";["#pagination","#search-summary","#excluded-panel"].forEach(x=>$(x).classList.add("hidden"));errorAt("#search-error");updateSelected(); }
  }
  if (view === "saved") { try { await loadLeads(); } catch (e) { toast(e.message, true); } renderSaved(); }
  if (view === "history") await loadHistory();
  window.scrollTo({top:0});
}
function setMode(mode) {
  if (state.busy) return;
  state.mode = mode;
  const potential = mode === "prospects";
  $(".search-tabs").classList.toggle("hidden",potential);
  $(".main-query").classList.toggle("hidden",potential);
  $("#sector-field").classList.toggle("hidden",!potential && mode !== "city");
  $("#search-button").textContent = potential ? "Potansiyelleri bul" : "Butikleri bul";
  updateSearchCost();
  $$(".search-tab").forEach(el => { const selected = el.dataset.mode === mode; el.classList.toggle("active", selected); el.setAttribute("aria-selected", selected); el.tabIndex = selected ? 0 : -1; });
  $("#query-label").textContent = mode === "general" ? "Arama ifadesi" : mode === "city" ? "Ürün / sektör (isteğe bağlı)" : "Ürün / ürün grubu";
  $("#search-query").placeholder = mode === "general" ? "Örn. boutique linge de maison Lyon" : "Örn. müslin nevresim";
  $("#search-query").required = mode !== "city" && mode !== "prospects";
  $("#search-query").minLength = ["city","prospects"].includes(mode) ? 0 : 2;
  $("#search-query").maxLength = mode === "general" ? 250 : 160;
  $("#search-city").required = mode === "city";
  $("#search-city").minLength = mode === "city" ? 2 : 0;
  $("#city-hint").textContent = mode === "city" ? "Bu arama için zorunlu" : "İsteğe bağlı";
  $("#query-hint").textContent = mode === "general" ? "Ürün odaklı ifade kullanın; yalnızca perakende alıcı adayları listelenir." : "Yaygın tekstil terimleri çevrilir; diğer ürünleri arama dilinde de yazabilirsiniz.";
}
function updateSearchCost() { const multi = (state.mode === "prospects" || (state.mode === "city" && !$("#search-query").value.trim())) && $("#search-sector").value === "all"; $("#search-cost").textContent=`Arama başına ${multi ? 3 : 1} servis isteği · En fazla 6 site incelenir · Aynı arama 15 dakika önbellekten gelir.`; }
function requestFromForm() {
  const value = state.mode === "prospects" ? "" : $("#search-query").value.trim();
  return {mode:state.mode, product:state.mode === "general" ? "" : value, query:state.mode === "general" ? value : "", city:$("#search-city").value.trim(), country:$("#search-country").value, language:$("#search-language").value, sector:$("#search-sector").value, page:1};
}
async function runSearch(request) {
  if (state.busy) return;
  state.busy = true; state.selected.clear(); updateSelected();
  $("#search-button").disabled = true; $("#prev-page").disabled = true; $("#next-page").disabled = true;
  errorAt("#search-error"); ["#pagination","#search-summary","#excluded-panel"].forEach(x=>$(x).classList.add("hidden"));
  $("#search-results").innerHTML = `<div class="loading-state"><div class="spinner"></div>Firmalar araştırılıyor…<p>Web sonuçları eleniyor ve butiklerin siteleri inceleniyor. Bu işlem yaklaşık 10–45 saniye sürebilir.</p></div>`;
  try {
    const data = await api("/api/search", {method:"POST", body:JSON.stringify(request)});
    state.results = data.results; state.request = request; state.hasMore = data.has_more;
    $("#results-count").textContent = state.results.length;
    $("#results-subtitle").textContent = `${data.query} · ${data.provider === "serpapi" ? "Google / SerpApi" : "Brave Search"}`;
    renderSearchSummary(data);
    renderResults();
    $("#result-page").textContent = `Sayfa ${request.page}`;
    $("#pagination-label").textContent = `Sayfa ${request.page}`;
    $("#pagination").classList.toggle("hidden", !state.hasMore && request.page === 1);
  } catch (e) {
    state.results = []; state.request = null; state.hasMore = false; $("#results-count").textContent = "0"; $("#result-page").textContent = "";
    $("#results-subtitle").textContent = "Arama tamamlanamadı.";
    errorAt("#search-error", e.message);
    $("#search-results").innerHTML = empty("Arama tamamlanamadı", "Yukarıdaki uyarıyı kontrol edip yeniden deneyin.");
  } finally {
    state.busy = false; $("#search-button").disabled = false;
    $("#prev-page").disabled = !state.request || state.request.page === 1; $("#next-page").disabled = !state.hasMore;
  }
}
function empty(title, description) { return `<div class="empty-state"><div class="empty-illustration"><span>⌕</span></div><h3>${esc(title)}</h3><p>${esc(description)}</p></div>`; }
function savedLead(row) { return state.leads.find(x => (row.website ? domainKey(x.website) === domainKey(row.website) : fold(x.name) === fold(row.name) && fold(x.city) === fold(row.city) && fold(x.country) === fold(row.country))); }
function companyCell(row, action, key) {
  const initials = row.name.split(/\s+/).slice(0,2).map(x => x[0]).join("");
  return `<div class="company-cell"><div class="company-logo">${esc(initials)}</div><div><button class="company-name" data-action="${action}" data-key="${esc(key)}" title="${esc(row.name)}">${esc(row.name)}</button><span class="company-domain">${esc(domain(row.website))}</span></div></div>`;
}
function renderResults() {
  if (!state.results.length) { $("#search-results").innerHTML = empty("Bu aramada sonuç bulunamadı", "Bu sayfada kendi sitesiyle doğrulanabilen butik / ürün kanıtı bulunamadı. Sonraki sayfayı, daha genel bir ürün veya farklı bölgeyi deneyin."); return; }
  $("#search-results").innerHTML = `<table class="data-table"><thead><tr><th class="check-cell"><input type="checkbox" id="select-all" aria-label="Tüm sonuçları seç"></th><th>Firma / web sitesi</th><th>Konum</th><th>Alıcı değerlendirmesi</th><th>İşlem</th></tr></thead><tbody>${state.results.map((r,i) => `<tr><td class="check-cell"><input type="checkbox" data-select="${i}" ${state.selected.has(i) ? "checked" : ""} ${savedLead(r) ? "disabled" : ""} aria-label="${esc(r.name)} seç"></td><td>${companyCell(r,"result",i)}</td><td><div class="cell-stack"><span>${esc(r.city || r.target_city || "—")}</span><small>${esc(countries[r.country] || r.country || "")} ${r.city ? "" : r.target_city ? "· arama hedefi" : ""}</small></div></td><td>${buyerSummary(r)}</td><td><div class="row-actions"><button class="small-button" data-action="result" data-key="${i}">İncele ↗</button><button class="small-button ${savedLead(r) ? "saved" : ""}" data-action="save-result" data-key="${i}" ${savedLead(r) ? "disabled" : ""}>${savedLead(r) ? "✓ Kayıtlı" : "+ Kaydet"}</button></div></td></tr>`).join("")}</tbody></table>`;
  updateSelected();
}
function updateSelected() {
  $("#save-selected").classList.toggle("hidden", !state.selected.size); $("#save-selected").textContent = `${state.selected.size} firmayı kaydet`;
  const all = $("#select-all");
  if (all) { const available = state.results.filter(r => !savedLead(r)).length; all.checked = available > 0 && state.selected.size === available; all.indeterminate = state.selected.size > 0 && state.selected.size < available; all.disabled = !available; }
}
async function loadLeads() {
  const data = await api("/api/leads"); state.leads = data.leads; state.hiddenCount = data.hidden_count || 0;
  $("#nav-count").textContent = state.leads.length;
  $("#stat-total").textContent = state.leads.length;
  $("#stat-qualified").textContent = state.leads.filter(x => x.status === "qualified").length;
  $("#stat-contacted").textContent = state.leads.filter(x => ["contacted", "replied"].includes(x.status)).length;
  $("#stat-replied").textContent = state.leads.filter(x => x.status === "replied").length;
  if (state.results.length) renderResults();
}
function renderSaved() {
  const query = fold($("#filter-query").value); const status = $("#filter-status").value; const fit = $("#filter-fit").value; const opportunity = $("#filter-opportunity").value;
  const filtered = state.leads.filter(r => (!query || fold([r.name,r.product,r.city,r.target_city,r.email,r.website,r.country].join(" ")).includes(query)) && (!status || r.status === status) && (!fit || r.fit === fit) && (!opportunity || opportunity === r.opportunity));
  state.pdfIds = filtered.map(r=>r.id); $("#export-pdf").disabled = !filtered.length;
  $("#saved-count").textContent = `${state.leads.length} kayıt içinden ${filtered.length} firma gösteriliyor${state.hiddenCount ? ` · ${state.hiddenCount} eski/uygunsuz kayıt gizlendi; tam yedekte korunuyor` : ""}`;
  if (!filtered.length) { $("#saved-results").innerHTML = empty(state.leads.length ? "Filtrelere uygun firma yok" : "Firma listeniz henüz boş", state.leads.length ? "Filtreleri değiştirip tekrar deneyin." : "Keşif sonuçlarından firma kaydedin veya elle yeni bir firma ekleyin."); return; }
  $("#saved-results").innerHTML = `<table class="data-table"><thead><tr><th>Firma / web sitesi</th><th>İletişim</th><th>Konum</th><th>Alıcı önceliği</th><th>Durum</th><th></th></tr></thead><tbody>${filtered.map(r => `<tr><td>${companyCell(r,"edit",r.id)}</td><td><div class="cell-stack"><span>${esc(r.email || "E-posta eklenmedi")}</span><small>${esc(r.phone || r.whatsapp || "Telefon eklenmedi")}</small></div></td><td><div class="cell-stack"><span>${esc(r.city || "Doğrulanmadı")}</span><small>${esc(countries[r.country] || r.country)}</small></div></td><td>${buyerSummary(r)}</td><td><span class="badge ${esc(r.status)}">${statuses[r.status]}</span></td><td><button class="small-button" data-action="edit" data-key="${esc(r.id)}">Düzenle ↗</button></td></tr>`).join("")}</tbody></table>`;
}
async function saveResult(index) {
  const row = state.results[index]; if (!row || savedLead(row)) return;
  await api("/api/leads", {method:"POST", body:JSON.stringify(row)}); state.selected.delete(index); await loadLeads(); toast(`${row.name} listenize eklendi.`);
}
const leadFields = ["name","website","product","fit","email","phone","whatsapp","instagram","contact_person","city","target_city","country","status","notes","evidence","source_url","name_tr","product_tr","evidence_tr","supplier_evidence_tr","notes_tr"];
function formLead() {
  const lead = {}; for (const name of leadFields) lead[name] = $("#lead-form").elements[name].value.trim();
  lead.is_demo = false; lead.sources = state.editing?.sources || [];
  const context = state.assessmentContext;
  if (!context || (context.website === lead.website && context.product === lead.product)) for (const name of assessmentFields) if (state.editing?.[name] !== undefined) lead[name]=state.editing[name];
  return lead;
}
function openLead(lead = null) {
  state.editToken++; state.editing = lead ? structuredClone(lead) : {is_demo:false,sources:[]};
  const form = $("#lead-form"); form.reset();
  for (const name of leadFields) if (lead && name in lead) form.elements[name].value = lead[name];
  $("#drawer-title").textContent = lead?.id ? "Firma bilgilerini düzenle" : lead ? "Firmayı inceleyin" : "Yeni firma ekleyin";
  $("#save-lead").textContent = lead?.id ? "Değişiklikleri kaydet" : "Firmayı kaydet";
  $("#delete-lead").classList.toggle("hidden", !lead?.id);
  $("#enrich-button").disabled = false;
  state.assessmentContext = {website:form.elements.website.value.trim(),product:form.elements.product.value.trim()};
  renderAssessment();
  $("#enrich-button").textContent = "⌕ Siteden bilgileri bul";
  errorAt("#drawer-error"); renderSources(); renderContactLinks();
  state.drawerSnapshot = JSON.stringify(formLead()); $("#lead-dialog").showModal(); $(".drawer-content").scrollTop = 0;
}
async function closeLead() {
  if (JSON.stringify(formLead()) !== state.drawerSnapshot && !await confirmAction("Kaydedilmemiş değişiklikler", "Yaptığınız değişiklikler kaydedilmedi. Kartı kapatmak istiyor musunuz?", "Değişiklikleri bırak")) return;
  state.editToken++; $("#lead-dialog").close();
}
function renderSources() {
  const sources = state.editing?.sources || [];
  $("#sources-list").innerHTML = sources.length ? `<div class="sources"><h3>Bilgi kaynakları</h3>${sources.map(s => `<a href="${esc(safeUrl(s.url))}" target="_blank" rel="noopener noreferrer">${esc({email:"E-posta",phone:"Telefon",whatsapp:"WhatsApp",instagram:"Instagram",evidence:"Ürün kanıtı"}[s.field] || s.field)} · ${esc(domain(s.url))} ↗ <span>${s.checked_at ? esc(new Date(s.checked_at).toLocaleDateString("tr-TR")) : ""}</span></a>`).join("")}<p>Kaynaklar sitenin incelendiği andaki yayımlanmış bilgiyi gösterir.</p></div>` : "";
}
function renderContactLinks() {
  const row = formLead(); const links = [];
  if (safeUrl(row.website)) links.push(`<a href="${esc(safeUrl(row.website))}" target="_blank" rel="noopener noreferrer">Web sitesini aç ↗</a>`);
  if (row.email && /^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(row.email)) links.push(`<a href="mailto:${esc(encodeURIComponent(row.email))}">E-posta yaz ↗</a>`);
  const whatsapp = row.whatsapp.replace(/\D/g, ""); if (whatsapp.length >= 7 && whatsapp.length <= 15) links.push(`<a href="https://wa.me/${whatsapp}" target="_blank" rel="noopener noreferrer">WhatsApp aç ↗</a>`);
  if (safeUrl(row.instagram)) links.push(`<a href="${esc(safeUrl(row.instagram))}" target="_blank" rel="noopener noreferrer">Instagram ↗</a>`);
  $("#contact-links").innerHTML = links.join("");
}
async function enrichLead() {
  const btn = $("#enrich-button"); const form = $("#lead-form"); const url = form.elements.website.value.trim(); const product = form.elements.product.value.trim();
  if (!safeUrl(url)) { errorAt("#drawer-error", "Önce geçerli bir web sitesi adresi girin."); return; }
  btn.disabled = true; btn.textContent = "Site inceleniyor…"; errorAt("#drawer-error");
  const token = state.editToken; const before = formLead();
  try {
    const result = await api("/api/enrich", {method:"POST", body:JSON.stringify({url, product})});
    if (state.editToken !== token || !$("#lead-dialog").open) return;
    if (form.elements.website.value.trim() !== url || form.elements.product.value.trim() !== product) { errorAt("#drawer-error", "Adres veya ürün değişti. Yeni bilgilerle tekrar inceleyin."); return; }
    let count = 0;
    for (const name of ["email","phone","whatsapp","instagram","evidence"]) if (result.data[name] && !form.elements[name].value.trim() && form.elements[name].value.trim() === before[name]) { form.elements[name].value = result.data[name]; count++; }
    if (result.data.fit === "possible" && form.elements.fit.value === "unknown") form.elements.fit.value = "possible";
    state.editing.sources = [...(state.editing.sources || []), ...result.data.sources].filter((s,i,a) => a.findIndex(x => x.url === s.url && x.field === s.field && x.value === s.value) === i).slice(-20);
    if (result.assessment?.accepted) {
      for (const field of assessmentFields) if (result.assessment[field] !== undefined) state.editing[field]=result.assessment[field];
    } else if (result.assessment) { Object.assign(state.editing,{priority:0,opportunity:"unknown",buyer_type:"unknown",assessment:result.checked.length ? "website" : "unreviewed",reasons:[result.assessment.reason || "Alıcı niteliği doğrulanamadı"],supplier_source:"",supplier_evidence:""}); }
    state.assessmentContext={website:url,product};
    if ((before.supplier_evidence || "") !== (state.editing.supplier_evidence || "")) form.elements.supplier_evidence_tr.value="";
    renderAssessment(); renderSources(); renderContactLinks();
    if (result.warnings.length) errorAt("#drawer-error", result.warnings.join(" "));
    toast(count ? `${count} alan dolduruldu. İnceleyip kaydedin.` : "Yeni bilgi bulunamadı. Mevcut alanlar korundu; gerekirse elle ekleyin.");
  } catch (e) { if (state.editToken === token) errorAt("#drawer-error", e.message); }
  finally { if (state.editToken === token) { btn.disabled = false; btn.textContent = "⌕ Siteden bilgileri bul"; } }
}
async function loadHistory() {
  $("#history-results").innerHTML = '<div class="loading-state">Arama geçmişi yükleniyor…</div>';
  try {
    const data = await api("/api/history"); state.history = data.history;
    $("#history-results").innerHTML = state.history.length ? state.history.map(h => `<div class="history-item"><span class="history-icon">◷</span><div><strong>${esc(h.query)}</strong><p>${esc(new Date(h.created_at).toLocaleString("tr-TR"))} · ${h.count} sonuç · ${h.provider === "serpapi" ? "Google / SerpApi" : "Brave"} · Sayfa ${h.request.page}</p></div><button class="button secondary" data-action="repeat" data-key="${esc(h.id)}">Yeniden ara ↗</button></div>`).join("") : empty("Henüz arama yapılmadı", "Aramalarınız burada otomatik olarak saklanır.");
  } catch (e) { $("#history-results").innerHTML = empty("Geçmiş yüklenemedi", e.message); }
}
function applyRequest(req) {
  setMode(req.mode); $("#search-query").value = req.mode === "general" ? req.query : req.product; $("#search-city").value = req.city; $("#search-country").value = req.country; $("#search-language").value = req.language; $("#search-sector").value = req.sector || "all"; updateSearchCost();
}
function renderSettings() {
  const s = state.settings; $("#provider").value = s.provider; $("#connection-pill").textContent = s.configured ? "● Canlı arama bağlı" : "○ Arama bağlantısı gerekli";
  $("#storage-label").textContent = s.cloud ? "Web çalışma alanı" : "Yerel çalışma alanı"; $("#settings-storage").textContent = s.storage;
  $("#provider-state").textContent = s.configured ? `${s.provider === "serpapi" ? "Google / SerpApi" : "Brave Search"} anahtarı tanımlı. Bağlantı, ilk canlı aramada doğrulanır.` : "Henüz canlı arama anahtarı tanımlanmadı. Butik keşfi için bir servis bağlayın.";
  $("#settings-form").classList.toggle("hidden", s.cloud);
  $("#setup-notice").classList.toggle("hidden",s.configured);
  $("#search-button").disabled = !s.configured;
  if (s.cloud) $("#provider-state").textContent += " Anahtarlar Vercel ortam değişkenlerinden yönetilir.";
}
async function download(path, filename, options = {}) {
  const response = await api(path, {...options,raw:true}); const blob = await response.blob(); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 60000);
}
function showLogin() { window.location.replace("/admin/"); }
async function initialize() {
  const response = await fetch("/api/admin?action=status", {cache:"no-store"});
  if (!response.ok) throw new Error("Yönetici oturumu kontrol edilemedi. Sayfayı yenileyin.");
  const admin = await response.json();
  if (!admin.authenticated) { showLogin(); return; }
  adminCsrf = admin.csrf;
  const session = await api("/api/session");
  if (!session.authenticated) { showLogin(); return; }
  $("#login-screen").classList.add("hidden"); $("#app").inert = false; $("#logout").classList.toggle("hidden", !session.cloud);
  state.settings = await api("/api/settings"); renderSettings(); await loadLeads(); renderSaved(); await loadTranslationSettings();
}

document.addEventListener("click", async event => {
  const view = event.target.closest("[data-view]"); if (view) await switchView(view.dataset.view);
  const mode = event.target.closest("[data-mode]"); if (mode) setMode(mode.dataset.mode);
  const action = event.target.closest("[data-action]"); if (!action) return;
  const key = action.dataset.key;
  if (action.dataset.action === "result") { const row = state.results[Number(key)]; openLead(savedLead(row) || row); }
  if (action.dataset.action === "edit") openLead(state.leads.find(x => x.id === key));
  if (action.dataset.action === "save-result") await buttonTask(action, () => saveResult(Number(key)));
  if (action.dataset.action === "repeat") { const h = state.history.find(x => x.id === key); if (h) { const req = {...h.request}; delete req.demo; await switchView(req.mode === "prospects" ? "prospects" : "discover"); applyRequest(req); await runSearch(req); } }
});
$(".search-tabs").addEventListener("keydown", event => {
  if (!["ArrowLeft","ArrowRight","Home","End"].includes(event.key)) return;
  event.preventDefault(); const modes = ["product","city","general"]; const i = modes.indexOf(state.mode); const next = event.key === "Home" ? 0 : event.key === "End" ? 2 : (i + (event.key === "ArrowRight" ? 1 : 2)) % 3;
  setMode(modes[next]); $(`[data-mode="${modes[next]}"]`).focus();
});
$("#search-form").addEventListener("submit", event => { event.preventDefault(); runSearch(requestFromForm()); });
$("#search-sector").addEventListener("change",updateSearchCost);
$("#search-query").addEventListener("input",updateSearchCost);
$("#prev-page").onclick = () => state.request && runSearch({...state.request,page:state.request.page - 1});
$("#next-page").onclick = () => state.request && runSearch({...state.request,page:state.request.page + 1});
$("#search-results").addEventListener("change", event => {
  if (event.target.id === "select-all") { state.selected.clear(); if (event.target.checked) state.results.forEach((r,i) => { if (!savedLead(r)) state.selected.add(i); }); renderResults(); }
  else if (event.target.dataset.select !== undefined) { const i = Number(event.target.dataset.select); if (event.target.checked) state.selected.add(i); else state.selected.delete(i); updateSelected(); }
});
$("#save-selected").onclick = () => buttonTask($("#save-selected"), async () => {
  const indexes = [...state.selected]; let added = 0; const errors = [];
  for (const i of indexes) { try { await api("/api/leads", {method:"POST", body:JSON.stringify(state.results[i])}); state.selected.delete(i); added++; } catch (e) { errors.push(e.message); } }
  await loadLeads(); updateSelected(); toast(`${added} firma kaydedildi.${errors.length ? ` ${errors.length} kayıt eklenemedi: ${errors[0]}` : ""}`, errors.length > 0);
});
for (const id of ["#filter-query","#filter-status","#filter-fit","#filter-opportunity"]) $(id).addEventListener(id === "#filter-query" ? "input" : "change", renderSaved);
$("#new-lead").onclick = $("#add-saved").onclick = () => openLead();
$("#close-drawer").onclick = $("#cancel-drawer").onclick = closeLead;
$("#lead-dialog").addEventListener("cancel", e => { e.preventDefault(); closeLead(); });
$("#lead-form").addEventListener("input", renderContactLinks);
$("#lead-form").addEventListener("submit", async event => {
  event.preventDefault(); const btn = $("#save-lead"); if (btn.disabled) return; btn.disabled = true; errorAt("#drawer-error");
  try {
    const lead = formLead(); const existing = state.editing?.id;
    await api(existing ? `/api/leads/${existing}` : "/api/leads", {method:existing ? "PUT" : "POST", body:JSON.stringify(existing ? {lead, version:state.editing.version} : lead)});
    state.editToken++; $("#lead-dialog").close(); await loadLeads(); renderSaved(); toast(existing ? "Firma bilgileri güncellendi." : "Firma listenize eklendi.");
  } catch (e) { errorAt("#drawer-error", e.message); } finally { btn.disabled = false; }
});
$("#enrich-button").onclick = enrichLead;
$("#delete-lead").onclick = () => buttonTask($("#delete-lead"), async () => {
  if (!await confirmAction("Firma kaydı silinsin mi?", `“${state.editing.name}” firma kaydı ve notları silinecek. Bu işlem geri alınamaz.`, "Kaydı sil")) return;
  await api(`/api/leads/${state.editing.id}?version=${state.editing.version}`, {method:"DELETE"}); state.editToken++; $("#lead-dialog").close(); await loadLeads(); renderSaved(); toast("Firma kaydı silindi.");
});
$("#settings-form").addEventListener("submit", event => { event.preventDefault(); buttonTask($("#settings-form button[type=submit]"), async () => { state.settings = await api("/api/settings", {method:"PUT", body:JSON.stringify({provider:$("#provider").value,key:$("#api-key").value.trim()})}); $("#api-key").value = ""; renderSettings(); toast("Arama anahtarı kaydedildi. Canlı arama yapabilirsiniz."); }); });
$("#export-csv").onclick = () => buttonTask($("#export-csv"), () => download("/api/export", "firma-atlas-firmalar.csv"));
$("#backup-button").onclick = () => buttonTask($("#backup-button"), () => download("/api/backup", "firma-atlas-yedek.json"));
$("#restore-button").onclick = () => $("#restore-file").click();
$("#restore-file").onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 20_000_000) throw new Error("Yedek en fazla 20 MB olabilir.");
    let data; try { data = JSON.parse(await file.text()); } catch { throw new Error("Geçerli bir JSON yedeği seçin."); }
    if (data.format !== "firma-atlas-v1" || !Array.isArray(data.leads)) throw new Error("Bu dosya bir Firma Atlas yedeği değil.");
    if (!await confirmAction("Yedeği içe aktar", `${data.leads.length} firma kontrol edilip listeye eklenecek. Mevcut firmalar değiştirilmez; tekrarlar atlanır.`, "İçe aktar")) return;
    const result = await api("/api/restore", {method:"POST", body:JSON.stringify(data)}); await loadLeads(); renderSaved(); toast(`${result.added} firma eklendi, ${result.skipped} tekrar veya eski örnek kayıt atlandı.`);
  } catch (e) { toast(e.message, true); } finally { event.target.value = ""; }
};

$("#logout").onclick = () => buttonTask($("#logout"), async () => { const response = await fetch("/api/admin?action=logout", {method:"POST", headers:{"Content-Type":"application/json","X-CSRF-Token":adminCsrf},body:"{}"}); if (!response.ok) throw new Error("Çıkış yapılamadı. Tekrar deneyin."); state.leads = []; state.results = []; state.history = []; state.request = null; state.selected.clear(); $("#saved-results").innerHTML = ""; $("#history-results").innerHTML = ""; $("#search-results").innerHTML = ""; showLogin(); });
setMode("product");
initialize().catch(e => { errorAt("#search-error", e.message); toast(e.message, true); });

function buyerSummary(row) {
  return `<div class="buyer-summary"><span class="priority-score">${esc(row.priority || 0)}<small>/100</small></span><div><strong>${esc(opportunities[row.opportunity] || "İncelenmedi")}</strong><small>${row.assessment === "website" ? "Site incelendi" : row.assessment === "search" ? "Arama özeti · inceleme gerekli" : "Değerlendirme gerekli"}</small></div></div>`;
}
function renderSearchSummary(data) {
  const box=$("#search-summary"); box.classList.remove("hidden");
  box.innerHTML=`<span><strong>${esc(data.scanned)}</strong> web sonucu</span><span><strong>${esc(data.results.length)}</strong> alıcı adayı</span><span><strong>${esc(data.excluded.length)}</strong> elenen</span><span><strong>${esc(data.site_checks)}</strong> site kontrolü</span><span>${data.cached ? "Önbellek · yeni istek yok" : `${esc(data.requests_used)} servis isteği`}</span>`;
  $("#excluded-panel").classList.toggle("hidden",!data.excluded.length);
  $("#excluded-title").textContent=`${data.excluded.length} sonuç neden elendi?`;
  $("#excluded-results").innerHTML=data.excluded.map(x=>`<div class="excluded-row"><span>${esc(x.name || domain(x.url))}</span><small>${esc(x.reason)}</small></div>`).join("");
  if(data.warnings?.length) errorAt("#search-error",`Araştırma kısmen tamamlandı: ${data.warnings.join(" ")}`);
}
function renderAssessment() {
  const row=state.editing || {};const box=$("#buyer-assessment");box.classList.toggle("hidden",!row.reasons?.length);
  box.innerHTML=`${buyerSummary(row)}<p>${esc(buyerTypes[row.buyer_type] || "Belirsiz")}</p><ul>${(row.reasons || []).map(x=>`<li>${esc(x)}</li>`).join("")}</ul>${row.supplier_evidence ? `<blockquote>${esc(row.supplier_evidence)}</blockquote><a href="${esc(safeUrl(row.supplier_source))}" target="_blank" rel="noopener noreferrer">Başvuru ifadesinin kaynağı ↗</a>` : ""}<small>Öncelik puanı bir sipariş olasılığı değildir. Ürün ve alım ihtiyacını işletmeyle doğrulayın.</small>`;
}

async function loadTranslationSettings() {
 const config=await api('/api/translation/settings');
 $('#translation-provider').value=config.provider; $('#translation-region').value=config.region;
 $('#translation-state').textContent=config.configured ? 'Çeviri bağlantısı kayıtlı. Çevirileri kullanmadan önce kontrol edin.' : 'Bağlantı tanımlı değil. Türkçe alanları elle doldurabilirsiniz.';
 $('#translation-settings-form').classList.toggle('hidden',config.cloud);
 if(config.cloud) $('#translation-state').textContent+=' Bağlantı Vercel ortam değişkenlerinden yönetilir.';
}
$('#translation-settings-form').addEventListener('submit',event=>{event.preventDefault();buttonTask($('#translation-settings-form button'),async()=>{
 await api('/api/translation/settings',{method:'PUT',body:JSON.stringify({provider:$('#translation-provider').value,key:$('#translation-key').value.trim(),region:$('#translation-region').value.trim()})});
 $('#translation-key').value='';await loadTranslationSettings();toast('Çeviri bağlantısı kaydedildi.');
});});
$('#translate-lead').onclick=()=>buttonTask($('#translate-lead'),async()=>{
 const token=state.editToken;const row=formLead();const originals=['name','product','evidence','supplier_evidence','notes'];
 const snapshot=JSON.stringify(originals.map(k=>row[k]||''));
 const result=await api('/api/translate',{method:'POST',body:JSON.stringify(row)});
 if(token!==state.editToken || !$('#lead-dialog').open) return;
 if(snapshot!==JSON.stringify(originals.map(k=>formLead()[k]||''))) {toast('Metin değişti. Çeviriyi tekrar başlatın.',true);return;}
 for(const [key,value] of Object.entries(result.translations)) if(!$('#lead-form').elements[key].value.trim()) $('#lead-form').elements[key].value=value;
 toast('Boş Türkçe alanlar dolduruldu. Kontrol edip firmayı kaydedin.');
});
for(const key of ['name','product','evidence','notes']) $('#lead-form').elements[key].addEventListener('input',()=>{
 const translated=$('#lead-form').elements[key+'_tr'];if(translated.value) {translated.value='';toast('Orijinal metin değiştiği için ilgili çeviri temizlendi.');}
});
$('#export-pdf').onclick=()=>buttonTask($('#export-pdf'),async()=>{
 const ids=state.pdfIds||[];if(!ids.length) return;
 await download('/api/export/pdf','firma-atlas-butikler.pdf',{method:'POST',body:JSON.stringify({ids})});
 toast('Listede görünen kayıtlı firmaların PDF dosyası hazır.');
});
