import io

import flowdas.app
import flowdas.meta
import yaml
from babel.messages.pofile import read_po, write_po

from .project import Project, shell

flowdas.app.define('docker', flowdas.meta.Boolean(default=False))
flowdas.app.define('docker_cmd', flowdas.meta.String(default='docker'))
flowdas.app.define('git_cmd', flowdas.meta.String(default='git'))

DEFAULT_PROJECT_DATA = """kind: python-docs-ko
name: python-docs-ko
msg_repo: {}
"""


class App(flowdas.app.App):
    @property
    def distribution(self):
        return 'python-docs-ko'

    @property
    def image(self):
        return f'flowdas/python-docs-ko:{self.version}'

    def open_project(self, name):
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

        def build(self, *, project='python-docs-ko'):
            """build html"""
            App().open_project(project).build()

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
            f = io.BytesIO()
            write_po(f, catalog)
            odata = f.getvalue()
            if idata.encode() != odata:
                with open(pofile, 'wb') as f:
                    f.write(odata)
            else:
                print('already formatted')
