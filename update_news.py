#!/usr/bin/env python3
"""Atualiza manchetes de feeds RSS e imagens quando fornecidas pelas fontes."""
import datetime as dt
import email.utils
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / 'news.json'
QUERIES = [
    '"Lei Maria da Penha" "falsa denúncia"',
    '"Lei Maria da Penha" "absolvido"',
    '"violência doméstica" "direito de defesa"',
    '"medida protetiva" STJ',
    '"Lei Maria da Penha" "guarda"',
    '"presunção de inocência" "violência doméstica"',
]
MAX_ITEMS = 80
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; LMPEmFocoNews/2.0; RSS metadata reader)', 'Accept': 'text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.5'}


def clean(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', unescape(value or ''))).strip()[:400]


def date_of(raw):
    try:
        return email.utils.parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return dt.date.today().isoformat()


def http_get(url, limit=1_000_000):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read(limit), response.geturl(), response.headers.get('Content-Type', '')


def safe_https(url):
    if not isinstance(url, str):
        return ''
    url = url.strip()
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        return ''
    return url


class ImageMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images = []
        self.canonical = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            key = (attrs.get('property') or attrs.get('name') or '').lower()
            if key in ('og:image:secure_url', 'og:image', 'twitter:image'):
                self.images.append(attrs.get('content', ''))
        if tag == 'link' and 'canonical' in (attrs.get('rel') or '').lower():
            self.canonical = attrs.get('href', '')


def rss_image(item):
    for child in item.iter():
        name = child.tag.split('}')[-1].lower()
        if name in ('thumbnail', 'content') and child.attrib.get('url'):
            image = safe_https(child.attrib['url'])
            if image:
                return image
        if name == 'enclosure' and child.attrib.get('type', '').startswith('image/'):
            image = safe_https(child.attrib.get('url', ''))
            if image:
                return image
    description = item.findtext('description') or ''
    match = re.search(r'<img\b[^>]*\bsrc=["\']([^"\']+)', description, re.I)
    return safe_https(unescape(match.group(1))) if match else ''


def metadata_image(url):
    """Consulta metadados somente de URLs de editoras, não de redirecionamentos Google News."""
    parsed = urllib.parse.urlsplit(url)
    if not safe_https(url) or parsed.hostname in ('news.google.com', 'www.google.com', 'google.com'):
        return ''
    try:
        data, final_url, content_type = http_get(url, 400_000)
        if 'html' not in content_type.lower():
            return ''
        parser = ImageMetadata()
        parser.feed(data.decode('utf-8', 'replace'))
        for candidate in parser.images:
            image = safe_https(urllib.parse.urljoin(final_url, unescape(candidate)))
            if image:
                return image
    except Exception as exc:
        print(f'Imagem indisponível em {parsed.hostname}: {exc}')
    return ''


def feed(query):
    params = urllib.parse.urlencode({'q': query, 'hl': 'pt-BR', 'gl': 'BR', 'ceid': 'BR:pt-419'})
    data, _, _ = http_get('https://news.google.com/rss/search?' + params, 2_000_000)
    return ET.fromstring(data)


def main():
    try:
        old = json.loads(OUTPUT.read_text(encoding='utf-8')).get('articles', [])
    except (FileNotFoundError, json.JSONDecodeError):
        old = []
    results = {a['url']: a for a in old if isinstance(a, dict) and a.get('url')}
    successes = 0
    for query in QUERIES:
        try:
            root = feed(query)
            successes += 1
            for item in root.findall('.//channel/item'):
                title = clean(item.findtext('title'))
                url = safe_https((item.findtext('link') or '').strip())
                if not title or not url:
                    continue
                source = item.find('source')
                publisher = clean(source.text) if source is not None else 'Fonte externa'
                old_article = results.get(url, {})
                image = rss_image(item) or old_article.get('image', '')
                if not image:
                    image = metadata_image(url)
                article = {
                    'title': title,
                    'summary': 'Leia a publicação original para conhecer os detalhes.',
                    'source': publisher,
                    'date': date_of(item.findtext('pubDate')),
                    'category': 'Notícias',
                    'url': url,
                }
                if image:
                    article['image'] = image
                results[url] = article
        except Exception as exc:
            print(f'Falha no feed {query!r}: {exc}')
    if not successes:
        raise RuntimeError('Nenhuma fonte respondeu. Mantendo o arquivo anterior.')
    articles = sorted(results.values(), key=lambda a: a.get('date', ''), reverse=True)[:MAX_ITEMS]
    OUTPUT.write_text(json.dumps({'articles': articles}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(articles)} notícias; {sum(bool(a.get("image")) for a in articles)} com imagem; {successes}/{len(QUERIES)} feeds consultados.')


if __name__ == '__main__':
    main()

