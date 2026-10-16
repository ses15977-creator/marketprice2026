#!/usr/bin/env python3
"""Bounded public JSON-LD collector. No browser impersonation or block bypass."""
import datetime as dt
import html.parser
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from decimal import Decimal, InvalidOperation
from gmarket_mobile_probe import URLS, MAX_SIZE
import import_csv as db

AGENT = 'MarketPrice2026/1.0'
HOSTS = {'m.gmarket.co.kr', 'item.gmarket.co.kr', 'www.gmarket.co.kr'}

class Scripts(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.parts = []; self.documents = []
    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.active = dict(attrs).get('type', '').lower() == 'application/ld+json'
            self.parts = []
    def handle_data(self, data):
        if self.active: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            try: self.documents.append(json.loads(''.join(self.parts)))
            except ValueError: pass
            self.active = False

def nodes(value):
    if isinstance(value, list):
        for item in value: yield from nodes(item)
    elif isinstance(value, dict):
        yield value
        for item in value.values(): yield from nodes(item)

def extract(body, source, stamp):
    parser = Scripts(); parser.feed(body); records = {}
    for p in nodes(parser.documents):
        if p.get('@type') != 'Product' or not isinstance(p.get('name'), str): continue
        offers = p.get('offers', [])
        if isinstance(offers, dict): offers = [offers]
        for o in offers:
            if not isinstance(o, dict) or o.get('@type') != 'Offer' or o.get('priceCurrency') != 'KRW': continue
            url = urllib.parse.urljoin(source, o.get('url') or p.get('url') or '')
            parsed = urllib.parse.urlsplit(url)
            code = urllib.parse.parse_qs(parsed.query).get('goodscode', [])
            if parsed.scheme != 'https' or parsed.hostname not in HOSTS or parsed.username or parsed.password or not code or not code[0].isdigit(): continue
            # Unknown delivery charges must never be reported as free delivery.
            shipping = o.get('shippingDetails', {})
            if isinstance(shipping, list):
                if len(shipping) != 1: continue
                shipping = shipping[0]
            rate = shipping.get('shippingRate', {}) if isinstance(shipping, dict) else {}
            if rate.get('currency') != 'KRW' or 'value' not in rate: continue
            try:
                price = Decimal(str(o['price'])); delivery = Decimal(str(rate['value']))
                if not price.is_finite() or not delivery.is_finite() or price <= 0 or delivery < 0: continue
            except (KeyError, InvalidOperation): continue
            canonical = 'https://item.gmarket.co.kr/Item?goodscode=' + code[0]
            rec = db.validate(dict(platform='G마켓', product_name=p['name'], listing_url=canonical,
                seller_price=str(price), shipping_fee=str(delivery), observed_at=stamp,
                source_url=source, is_deal='true'), 1)
            if canonical in records and records[canonical] != rec:
                raise ValueError('Conflicting product offers; no observations saved')
            records[canonical] = rec
    return list(records.values())

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).hostname != urllib.parse.urlsplit(req.full_url).hostname or not newurl.startswith('https://'):
            raise ValueError('Unexpected redirect; stopped')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

OPENER = urllib.request.build_opener(SafeRedirect())
def read(url):
    with OPENER.open(urllib.request.Request(url, headers={'User-Agent': AGENT}), timeout=20) as response:
        raw = response.read(MAX_SIZE + 1)
        if len(raw) > MAX_SIZE: raise ValueError('Response too large')
        return raw.decode(response.headers.get_content_charset() or 'utf-8')

def robots_allowed(rules, url):
    # Duplicate wildcard groups exist on this host. urllib.robotparser only
    # considers the first, which can mask a later Disallow: /. Check every
    # applicable group conservatively instead of treating that as permission.
    groups = []; agents = []; directives = []
    def flush():
        if agents: groups.append((list(agents), list(directives)))
    for raw in rules.splitlines():
        line = raw.split('#', 1)[0].strip()
        if ':' not in line: continue
        key, value = (part.strip() for part in line.split(':', 1))
        if key.lower() == 'user-agent':
            if directives:
                flush(); agents = []; directives = []
            agents.append(value)
        elif agents:
            directives.append((key, value))
    flush()
    for group_agents, group_rules in groups:
        if not any(a == '*' or a.lower() in AGENT.lower() for a in group_agents): continue
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(['User-agent: *'] + [k + ': ' + v for k, v in group_rules])
        if not parser.can_fetch(AGENT, url): return False
    return True

def collect(url, stamp):
    robots_url = urllib.parse.urljoin(url, '/robots.txt')
    try: rules = read(robots_url)
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
        rules = ''
    if not robots_allowed(rules, url): raise ValueError('robots.txt disallows collection')
    return extract(read(url), url, stamp)

def main():
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.replace(minute=0, second=0, microsecond=0).isoformat()
    report = {'started_at': now.isoformat(), 'status': 'failed', 'saved': 0, 'results': []}
    records = {}
    try:
        for url in URLS:
            try:
                rows = collect(url, stamp)
                for row in rows:
                    if row['url'] in records and records[row['url']]['price'] != row['price']:
                        raise ValueError('Conflicting prices across source pages')
                    records[row['url']] = row
                report['results'].append({'url': url, 'extracted': len(rows)})
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                report['results'].append({'url': url, 'error': type(e).__name__, 'reason': str(e) if isinstance(e, ValueError) else 'Access unavailable', 'http_status': getattr(e, 'code', None)})
        if not records: raise ValueError('No verified products extracted; nothing saved')
        if not db.BASE or not db.KEY: raise ValueError('Missing server-side Supabase credentials')
        # Atomic RPC requires the supplied migration; fail closed if it is absent.
        for row in records.values():
            db.request('rpc/save_verified_observation', 'POST', {'rec': row})
            report['saved'] += 1
        report['status'] = 'success' if all('error' not in x for x in report['results']) else 'partial'
    except (ValueError, urllib.error.URLError) as e:
        report['error'] = str(e) if isinstance(e, ValueError) else type(e).__name__
    finally:
        report['finished_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        if db.BASE and db.KEY:
            try:
                db.request('collection_runs', 'POST', {'platform_id': 1,
                    'status': report['status'], 'started_at': report['started_at'],
                    'finished_at': report['finished_at'],
                    'error_message': report.get('error')})
                report['run_log_saved'] = True
            except (ValueError, urllib.error.URLError):
                report['run_log_saved'] = False
                report['database_status'] = 'run_log_write_failed'
                report['status'] = 'failed'
        else:
            report['run_log_saved'] = False
            report['database_status'] = 'missing_server_credentials'
        pathlib.Path('gmarket-collection-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'success' else 2

if __name__ == '__main__': sys.exit(main())
