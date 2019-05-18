import io
import pathlib
import string

import flowdas.app
import flowdas.meta
import yaml
from babel.messages.pofile import read_po, write_po

from .project import Project, shell
from .spell import check_spell

flowdas.app.define('docker', flowdas.meta.Boolean(default=False))
flowdas.app.define('docker_cmd', flowdas.meta.String(default='docker'))
flowdas.app.define('git_cmd', flowdas.meta.String(default='git'))
# flowdas.app.define('spell_uri', flowdas.meta.String(default='http://speller.cs.pusan.ac.kr/PnuWebSpeller/lib/check.asp'))
flowdas.app.define('spell_uri', flowdas.meta.String(default='http://164.125.7.61/speller/lib/check.asp'))

DEFAULT_PROJECT_DATA = """kind: python-docs-ko
name: python-docs-ko
msg_repo: {}
ignores:
- whatsnew/changelog.po
"""


def _remove_nonprintables(text):
    nps = ''.join(sorted(set(chr(i) for i in range(128)) - set(string.printable)))
    table = str.maketrans(nps, nps[0] * len(nps))
    return text.translate(table).replace(nps[0], '')


class App(flowdas.app.App):
    @property
    def distribution(self):
        return 'python-docs-ko'

    @property
    def image(self):
        return f'flowdas/python-docs-ko:{self.version}'

    def open_project(self, name):
        if name is None:
            p = pathlib.Path().absolute()
            try:
                relpath = p.relative_to(self.home)
                name = relpath.parts[0]
            except (ValueError, IndexError):
                name = 'python-docs-ko'
        with open(self.home / name / 'project.yaml') as f:
            data = yaml.load(f, Loader=yaml.SafeLoader)
        return Project().load(data)

    class Command(flowdas.app.App.Command):
        def init(self, repo, *, project=None):
            """initialize project"""
            app = App()
            if project is None:
                project = 'python-docs-ko'
                project_dir = app.home / project
                project_dir.mkdir(exist_ok=True)
                with open(project_dir / 'project.yaml', 'wt') as f:
                    f.write(DEFAULT_PROJECT_DATA.format(repo))
            app.open_project(project).setup()

        def build(self, *, rebuild=False, project=None):
            """build html"""
            App().open_project(project).build(rebuild=rebuild)

        def dockerbuild(self):
            """build docker image (dev only)"""
            app = App()
            return shell(f'{app.config.docker_cmd} build . -t {app.image}', chdir=app.home)

        def dockerpush(self):
            """push docker image (dev only)"""
            app = App()
            return shell(f'{app.config.docker_cmd} push {app.image}', chdir=app.home)

        def format(self, pofile):
            """format po file"""
            with open(pofile) as f:
                idata = f.read()
            f = io.StringIO(idata)
            catalog = read_po(f, abort_invalid=True)

            catalog.language_team = 'Korean (https://python.flowdas.com)'

            for msg in catalog:
                if not msg.id or not msg.string or msg.fuzzy:
                    continue
                msg.string = _remove_nonprintables(msg.string)

            f = io.BytesIO()
            write_po(f, catalog)
            odata = f.getvalue()
            if idata.encode() != odata:
                with open(pofile, 'wb') as f:
                    f.write(odata)
            else:
                print('already formatted')
            fuzzy_count = empty_count = 0
            for msg in catalog:
                if not msg.id:
                    continue
                if msg.fuzzy:
                    fuzzy_count += 1
                elif not msg.string:
                    empty_count += 1
            if fuzzy_count:
                print(f'{fuzzy_count} fuzzy messages found')
            if empty_count:
                print(f'{empty_count} untranslated messages found')

        def spell(self, pofile):
            """spell check"""
            check_spell(pofile)
