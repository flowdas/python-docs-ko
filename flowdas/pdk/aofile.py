import pathlib

REPEAT = 7
PROLOG = '<' * REPEAT
SEPARATOR = '=' * REPEAT
EPILOG = '>' * REPEAT
DIVIDER = '<<<*>>>\n'


class Template:
    def __init__(self, template):
        self._template = template
        self._patches = []
        refs = []
        i3 = 0
        excess = 0
        while True:
            i0 = template.find(PROLOG, i3)
            if i0 < 0:
                break
            i1 = template.index(SEPARATOR, i0 + REPEAT)
            i2 = template.index(EPILOG, i1 + REPEAT)
            if template[i0 + REPEAT] == template[i1 - 1] == template[i1 + REPEAT] == template[i2 - 1] == '\n':
                # block mode
                block = 1
            else:
                # string mode
                block = 0
            assert block
            refs.extend([template[i3:i0], template[i0 + REPEAT + block:i1]])
            i3 = i2 + REPEAT + block
            offset = i0
            width = i1 - i0 - REPEAT - block
            replacement = template[i1 + REPEAT + block:i2]
            self._patches.append((offset - excess, width, replacement))
            excess += (REPEAT + block) * 3 + len(replacement)
        refs.append(template[i3:])
        self._reference = ''.join(refs)
        assert self._reference
        assert self._patches

    def __str__(self):
        return self._template

    def generate_patches(self, text, *, hint=''):
        p = text.find(self._reference)
        if p < 0:
            print(self._reference)
            raise RuntimeError(f'{hint}:cannot locate annotation')
        if text.find(self._reference, p + len(self._reference)) >= 0:
            print(p, self._reference)
            raise RuntimeError(f'{hint}:multiple match')
        for offset, width, replacement in self._patches:
            yield p + offset, width, replacement


class AOFile:
    def __init__(self, path):
        self._path = pathlib.Path(path)
        self._templates = []
        self._dirty = False
        if self._path.exists():
            self._load()

    def _load(self):
        text = self._path.read_text()
        templates = text.split(DIVIDER)
        self._templates = [Template(t) for t in templates if t.strip()]
        self._dirty = False

    def render(self, text):
        patches = []
        for t in self._templates:
            patches.extend(p for p in t.generate_patches(text, hint=self._path))
        for (offset, width, replacement) in sorted(patches, reverse=True):
            text = ''.join([text[:offset], replacement, text[offset + width:]])
        return text

    def save(self):
        if not self._dirty:
            return
        text = DIVIDER.join(str(t) for t in self._templates)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(text)

    def append(self, template):
        if not isinstance(template, Template):
            template = Template(template)
        self._templates.append(template)
        self._dirty = True
