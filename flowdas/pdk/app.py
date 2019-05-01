import os
import subprocess

import flowdas.app
import flowdas.meta

flowdas.app.define('docker', flowdas.meta.Boolean(default=False))
flowdas.app.define('cpython_branch', flowdas.meta.String(default='3.7'))
flowdas.app.define('po_branch', flowdas.meta.String(default='3.7'))
flowdas.app.define('docker_cmd', flowdas.meta.String(default='docker'))
flowdas.app.define('git_cmd', flowdas.meta.String(default='git'))


def shell(cmd, capture=False, chdir=None):
    opts = {
        'shell': True,
        'stdin': subprocess.PIPE,
    }
    cwd = os.getcwd() if chdir else None
    if chdir:
        os.chdir(chdir)
    try:
        if capture:
            opts['stderr'] = subprocess.STDOUT
            opts['universal_newlines'] = True
            return subprocess.check_output(cmd, **opts)
        else:
            return subprocess.check_call(cmd, **opts)
    finally:
        if cwd:
            os.chdir(cwd)


def pdk(*args):
    app = App()
    home = str(app.home)
    volumes = f'-v {home}/python-docs-ko:/python-docs-ko/cpython/locale/ko/LC_MESSAGES -v {home}/html:/python-docs-ko/cpython/Doc/build/html'
    return shell(f'{app.config.docker_cmd} run --rm -i {volumes} {app.image} {" ".join(args)}', chdir=home)


def git_clone(repo, dir, branch=None):
    app = App()
    if not os.path.exists(dir):
        shell(f'{app.config.git_cmd} clone --depth 1 --no-single-branch {repo} {dir}')
    if branch:
        shell(f'{app.config.git_cmd} -C {dir} checkout {branch}')
    shell(f'{app.config.git_cmd} -C {dir} pull')


class App(flowdas.app.App):
    @property
    def distribution(self):
        return 'python-docs-ko'

    @property
    def image(self):
        return f'flowdas/python-docs-ko:{self.version}'

    class Command(flowdas.app.App.Command):
        def init(self, repo):
            """initialize project"""
            app = App()
            git_clone(repo, 'python-docs-ko', app.config.po_branch)
            try:
                shell(f'{app.config.docker_cmd} image inspect {app.image}', capture=True)
            except:
                shell(f'{app.config.docker_cmd} pull {app.image}')

        def build(self):
            """build html"""
            app = App()
            if app.config.docker:
                shell(
                    "make VENVDIR=../.. SPHINXOPTS='-D locale_dirs=../locale -D language=ko -D gettext_compact=0' autobuild-dev-html",
                    chdir=(app.home / 'cpython/Doc'))
            else:
                pdk('build')

        def dockerbuild(self):
            """build docker image (dev only)"""
            app = App()
            return shell(f'{app.config.docker_cmd} build . -t {app.image}', chdir=app.home)

        def dockerpush(self):
            """push docker image (dev only)"""
            app = App()
            return shell(f'{app.config.docker_cmd} push {app.image}', chdir=app.home)
