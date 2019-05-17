import difflib
import pathlib
import re
import sqlite3
import time
import urllib.parse
import urllib.request
import warnings

from babel.messages.pofile import read_po
from flowdas.app import App
from lxml import etree

REQUEST_INTERVAL = 5  # seconds between http request


class Cache:
    def __init__(self, database):
        self._conn = c = sqlite3.connect(database)
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS spell(input TEXT PRIMARY KEY NOT NULL, output TEXT NOT NULL)")

    def get(self, input, getter):
        c = self._conn.execute("SELECT output FROM spell WHERE input=?", (input,))
        row = c.fetchone()
        if row:
            return row[0]
        output = getter(input)
        if output:
            with self._conn:
                self._conn.execute("INSERT INTO spell VALUES (?,?)", (input, output))
        return output


def sanitize(text):
    text = text.replace('`\\', '`').replace('*\\', '*')
    text = re.sub(r':(\w+):(\w+):`([^`]+)`', lambda m: m.group(3), text)  # :...:...:`...`
    text = re.sub(r':(\w+):`([^`]+)`', lambda m: m.group(2), text)  # :...:`...`
    text = re.sub(r'``([^`]+)``', lambda m: m.group(1), text)  # ``...``
    text = re.sub(r'`([^`]+)`([_]*)', lambda m: m.group(1), text)  # `...`_, `...`__
    text = re.sub(r'[*][*]([^*]+)[*][*]', lambda m: m.group(1), text)  # **...**
    text = re.sub(r'[*]([^*]+)[*]', lambda m: m.group(1), text)  # *...*
    return text


def extract(html):
    html = etree.HTML(html)
    tables = html.xpath('//table[@class="tableErrCorrect"]')
    for table in tables:
        entry = {}
        for tr in table.xpath("tr"):
            tds = tr.xpath("td")
            key = tds[0].text.strip()
            key = {
                '입력 내용': 'input',
                '대치어': 'output',
                '도움말': 'help',
            }.get(key, key)
            if key in {'input', 'output'}:
                value = (tds[1].text or '').strip()
                if value and (key != 'output' or value != '대치어 없음'):
                    entry[key] = value
            else:
                value = " ".join([x.strip() for x in tds[1].itertext()])
                if value and value != '없음':
                    entry[key] = value
        input, output, help = entry['input'], entry.get('output'), entry.get('help')
        if filter_suggestion(input, output, help):
            yield (input, output, help)


SIMPLE_EXCLUDES = {
    ('파이썬', '파이선'),
    ('컨텍스트', '문맥'),
    ('메서드를', '멘 거들을'),
    ('메서드가', '메서 들어가'),
    ('딕셔너리', '사전'),
    ('딕셔너리를', '사전을'),
}

DIFF_EXCLUDES = {
    ('.', '·'),
    ('딕셔너리', '사전'),
}


def filter_suggestion(input, output, help):
    if (input, output) in SIMPLE_EXCLUDES:
        return False
    if output:
        if input.isascii() and input.isprintable() and output.isascii() and output.isprintable():
            return False
        diffs = []
        s = difflib.SequenceMatcher(a=input, b=output)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag != 'equal':
                diff = (input[i1:i2], output[j1:j2])
                if diff in DIFF_EXCLUDES:
                    continue
                if diff == ('', ' ') and i1 > 0 and input[i1 - 1:i1 + 1].isalpha():
                    continue
                diffs.append(diff)
        if not diffs:
            return False
    else:
        if input.isascii() and input.isprintable():
            return False
    return True


def check_spell(pofile):
    app = App()
    cache = Cache(str(app.home / 'spell.cache'))
    ofile = app.home / 'spell.txt'
    uri = app.config.spell_uri

    wait_until = time.time()

    def fetch(text):
        nonlocal wait_until
        now = time.time()
        if now < wait_until:
            time.sleep(wait_until - now)
        wait_until += REQUEST_INTERVAL

        data = urllib.parse.urlencode({'text1': text})
        data = data.encode('ascii')
        with urllib.request.urlopen(uri, data, timeout=5) as f:
            return f.read().decode('utf-8')

    with open(pofile) as f:
        catalog = read_po(f, abort_invalid=True)
    poname = pathlib.Path(pofile).name

    with ofile.open('w') as f:
        for msg in catalog:
            if not msg.id or not msg.string or msg.fuzzy:
                continue

            text = sanitize(msg.string)
            try:
                html = cache.get(text, fetch)
                suggestions = list(extract(html))
                if suggestions:
                    f.write(f'# {poname}:{msg.lineno}\n')
                    for input, output, help in suggestions:
                        f.write(f'{input} -> {output}: {help or ""}\n')
                    f.write('\n')
                    f.flush()
            except urllib.request.URLError:
                warnings.warn('fail: ' + text)
