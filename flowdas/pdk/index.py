import csv
import hashlib
import io
import pathlib
from collections import namedtuple

from babel.messages.pofile import read_po

IndexRow = namedtuple('IndexRow', ['name', 'total', 'translated', 'hash'])


class Index:

    def __init__(self, index_file):
        self._file = index_file
        self._index = {}
        self._updated = False
        if index_file.exists():
            with index_file.open(newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    self._index[row[0]] = IndexRow(row[0], int(row[1]), int(row[2]), row[3])
        else:
            self._updated = True

    def save(self):
        if self._updated:
            with self._file.open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(sorted(self._index.values()))

    def scan(self, root, ignores=None):
        deleted = set(self._index.keys())
        excludes = set(pathlib.Path(ignore) for ignore in (ignores or []))
        queue = set(pofile.relative_to(root) for pofile in root.glob('**/*.po')) - excludes

        S, T = 0, 0
        for relpath in queue:
            name = str(relpath)
            pofile = root / relpath
            bcontent = pofile.read_bytes()
            hash = hashlib.sha256(bcontent).hexdigest()
            if name not in self._index or self._index[name].hash != hash:
                print(name)
                f = io.StringIO(bcontent.decode())
                catalog = read_po(f, abort_invalid=True)
                total, translated = 0, 0
                for msg in catalog:
                    # skip header
                    if not msg.id:
                        continue
                    size = len(msg.id)
                    total += size
                    if not msg.fuzzy and msg.string:
                        translated += size
                self._index[name] = IndexRow(name=name, total=total, translated=translated, hash=hash)
                self._updated = True
                S += total
                T += translated
            else:
                row = self._index[name]
                S += row.total
                T += row.translated
            try:
                deleted.remove(name)
            except:
                pass

        for name in deleted:
            del self._index[name]
            self._updated = True

        coverage = int(T * 10000 / S) / 10000
        print(f'{coverage:.2%} ({T}/{S})')
