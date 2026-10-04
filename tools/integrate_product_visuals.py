from pathlib import Path
import json
from PIL import Image

root = Path(__file__).resolve().parents[1]
source = Path(r'C:\Users\Atakan\.codex\generated_images\01a10166-d565-7f52-860c-f8b2c1398248')
target = root / 'img/products'
target.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / 'tools/product-image-prompts.json').read_text(encoding='utf-8'))
for item in manifest['images']:
    with Image.open(source / item['source']) as original:
        for width, suffix in [(1536, ''), (768, '-768')]:
            photo = original.convert('RGB')
            photo.thumbnail((width, round(width * 2 / 3)), Image.Resampling.LANCZOS)
            photo.save(target / (item['slug'] + suffix + '.webp'), 'WEBP', quality=85, method=6)
print('12 product concepts exported in 2 responsive WebP sizes.')
