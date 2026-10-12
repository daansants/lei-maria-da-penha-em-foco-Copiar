#!/usr/bin/env python3
"""Importa manchetes de RSS públicos e mantém links para a fonte original."""
import datetime as dt
import email.utils
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html import unescape

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / 'news.json'
QUERIES = [
    '"Lei Maria da Penha" justiça',
    '"medida protetiva" STJ',
    '"presunção de inocência" violência doméstica',
]
MAX_ITEMS = 80

def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', unescape(s or ''))).strip()[:400]

def date_of(raw):
    try:
        return email.utils.parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError, IndexError):
        return dt.date.today().isoformat()

def feed(query):
    params = urllib.parse.urlencode({'q': query, 'hl': 'pt-BR', 'gl': 'BR', 'ceid': 'BR:pt-419'})
    req = urllib.request.Request('https://news.google.com/rss/search?' + params, headers={'User-Agent':'LMPEmFoco/1.0 (RSS reader)'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return ET.fromstring(response.read(2_000_000))

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
                url = (item.findtext('link') or '').strip()
                if not title or not url.startswith('https://'):
                    continue
                source = item.find('source')
                publisher = clean(source.text) if source is not None else 'Fonte externa'
                category = 'Justiça' if 'STJ' in query else ('Direitos e garantias' if 'inocência' in query else 'Notícias')
                results[url] = {'title':title, 'summary':'Manchete de fonte externa. Consulte a publicação original para ler o conteúdo completo.', 'source':publisher, 'date':date_of(item.findtext('pubDate')), 'category':category, 'url':url}
        except Exception as exc:
            print(f'Falha no feed {query!r}: {exc}')
    if successes == 0:
        raise RuntimeError('Nenhuma fonte respondeu. Mantendo o arquivo anterior.')
    articles = sorted(results.values(), key=lambda a:a.get('date',''), reverse=True)[:MAX_ITEMS]
    OUTPUT.write_text(json.dumps({'articles':articles}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(articles)} manchetes armazenadas; {successes}/{len(QUERIES)} feeds consultados.')

if __name__ == '__main__':
    main()
