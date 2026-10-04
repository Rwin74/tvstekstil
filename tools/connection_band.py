from html import escape

COPY = {
 'en': ('OUR ORIGIN. YOUR NEXT CHAPTER.', 'A thread begins in Denizli.', 'Where could yours go?', 'Markets we are building for', ['France', 'Germany', 'Netherlands', 'Spain', 'United States'], 'Our own factory · Since 2021'),
 'fr': ('NOTRE ORIGINE. VOTRE PROCHAIN CHAPITRE.', 'Un fil prend naissance à Denizli.', 'Où ira le vôtre ?', 'Les marchés que nous visons', ['France', 'Allemagne', 'Pays-Bas', 'Espagne', 'États-Unis'], 'Notre propre usine · Depuis 2021'),
 'de': ('UNSER URSPRUNG. IHR NÄCHSTES KAPITEL.', 'Ein Faden beginnt in Denizli.', 'Wohin führt Ihrer?', 'Märkte, auf die wir uns ausrichten', ['Frankreich', 'Deutschland', 'Niederlande', 'Spanien', 'USA'], 'Unsere eigene Fabrik · Seit 2021'),
 'es': ('NUESTRO ORIGEN. SU PRÓXIMO CAPÍTULO.', 'Un hilo nace en Denizli.', '¿Hasta dónde llegará el suyo?', 'Mercados a los que nos dirigimos', ['Francia', 'Alemania', 'Países Bajos', 'España', 'Estados Unidos'], 'Nuestra propia fábrica · Desde 2021'),
}

def connection_band(lang):
 eyebrow, title, question, market_label, countries, factory = COPY[lang]
 return f'''<section class="connection-band" aria-labelledby="connection-title">
 <svg class="connection-thread" viewBox="0 0 1440 240" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path class="thread-base" d="M-40 180 C200 180 150 40 350 55 S650 255 860 160 S1140 25 1480 95"/><path class="thread-motion" d="M-40 180 C200 180 150 40 350 55 S650 255 860 160 S1140 25 1480 95"/></svg>
 <div class="connection-origin"><span class="origin-coordinate">TVS TEXTILE / EST. 2021</span><div class="origin-city"><span class="origin-dot" aria-hidden="true"></span>Denizli<span class="origin-country">TÜRKİYE</span></div><span class="origin-factory">{escape(factory)}</span></div>
 <div class="connection-message"><span class="eyebrow">{escape(eyebrow)}</span><h2 id="connection-title">{escape(title)}<br><em>{escape(question)}</em></h2></div>
 <div class="connection-markets"><span class="market-label">{escape(market_label)}</span><ul>{''.join(f'<li><span aria-hidden="true">{code}</span>{escape(country)}</li>' for code,country in zip(['FR','DE','NL','ES','US'],countries))}</ul></div>
 </section>'''
