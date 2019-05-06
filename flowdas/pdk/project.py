import os
import subprocess

from flowdas.app import App

from flowdas import meta


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


def git_clone(repo, dir, branch=None):
    app = App()
    if not os.path.exists(dir):
        shell(f'{app.config.git_cmd} clone --depth 1 --no-single-branch {repo} {dir}')
    if branch:
        shell(f'{app.config.git_cmd} -C {dir} checkout {branch}')
    shell(f'{app.config.git_cmd} -C {dir} pull')


class Project(meta.Entity):
    kind = meta.Kind()
    name = meta.String(required=True)
    build_cmd = meta.String()
    build_dir = meta.String()

    @property
    def home(self):
        return App().home / self.name

    def get_build_cmd(self):
        raise NotImplementedError

    def get_build_dir(self):
        return self.home

    def setup(self):
        pass

    def docker_build(self):
        app = App()
        home = str(app.home)
        volumes = f'-v {home}/{self.name}:/python-docs-ko/{self.name}'
        return shell(f'{app.config.docker_cmd} run --rm -i {volumes} {app.image} build --project={self.name}',
                     chdir=home)

    def build(self):
        app = App()
        if app.config.docker:
            shell(self.get_build_cmd(), chdir=self.home / 'src' / self.get_build_dir())
        else:
            self.docker_build()


class SphinxProject(Project):
    kind = 'sphinx'


class DefaultProject(SphinxProject):
    kind = 'python-docs-ko'
    msg_repo = meta.String(required=True)

    def get_build_cmd(self):
        return "make VENVDIR=../../.. SPHINXOPTS='-D locale_dirs=../locale -D language=ko -D gettext_compact=0' autobuild-dev-html"

    def get_build_dir(self):
        return 'Doc'

    def setup(self):
        app = App()
        msg_dir = app.home / self.name / 'msg'
        if not (msg_dir / '.git').exists():
            git_clone(self.msg_repo, msg_dir, '3.7')
        try:
            shell(f'{app.config.docker_cmd} image inspect {app.image}', capture=True)
        except:
            shell(f'{app.config.docker_cmd} pull {app.image}')

    def docker_build(self):
        app = App()
        home = str(app.home / 'python-docs-ko')
        volumes = ' '.join(f'-v {home}/{k}:/python-docs-ko/python-docs-ko/{v}' for k, v in (
            ('project.yaml', 'project.yaml'),
            ('msg', 'src/locale/ko/LC_MESSAGES'),
            ('pub', 'src/Doc/build/html'),
        ))
        return shell(f'{app.config.docker_cmd} run --rm -i {volumes} {app.image} build', chdir=home)
