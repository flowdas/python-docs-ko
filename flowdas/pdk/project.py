import os.path
import os.path
import pathlib
import shutil
import subprocess

from flowdas.app import App

from flowdas import meta
from .aofile import AOFile


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
    cname = meta.String()

    @property
    def home(self):
        return App().home / self.name

    def get_doc_dir(self):
        return '.'

    def get_src_links(self):
        return None

    def get_msg_dir(self):
        return None

    def get_bld_dir(self):
        return None

    def get_htm_dir(self):
        return None

    def get_build_cmd(self, *, rebuild=False):
        raise NotImplementedError

    def get_build_dir(self):
        return '.'

    def _create_symlink(self, symlink, to):
        np = len(pathlib.Path(os.path.commonpath([symlink, to])).parts)
        parts = ('..',) * (len(symlink.parts) - np - 1) + to.parts[np:]
        relpath = os.path.sep.join(parts)
        symlink.parent.mkdir(parents=True, exist_ok=True)
        symlink.symlink_to(relpath, target_is_directory=to.is_dir())

    def setup(self):
        pass

    def docker_build(self, *, rebuild=False):
        app = App()
        home = str(app.home)
        volumes = f'-v {home}/{self.name}:/python-docs-ko/{self.name}'
        options = f'--project={self.name}'
        if rebuild:
            options += ' --rebuild'
        return shell(f'{app.config.docker_cmd} run --rm -i {volumes} {app.image} build {options}',
                     chdir=home)

    def _prune_dir(self, root):
        if root.exists():
            with os.scandir(root) as it:
                for entry in it:
                    if not entry.name.startswith('.'):
                        path = os.path.join(root, entry.name)
                        if entry.is_file():
                            os.remove(path)
                        else:
                            shutil.rmtree(path)

    def build(self, *, rebuild=False):
        app = App()
        if app.config.docker:
            tmp_dir = self.home / 'tmp'
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            pub_dir = self.home / 'pub'
            publish = pub_dir.exists() and rebuild
            if publish:
                self._prune_dir(self.home / 'bld')
            self.copy_doc()
            self.link_msg()
            self.link_bld()
            shell(self.get_build_cmd(rebuild=rebuild), chdir=tmp_dir / self.get_build_dir())
            if publish:
                self._prune_dir(pub_dir)
                self.copy_pub()
        else:
            self.docker_build(rebuild=rebuild)

    def _annotate(self, src, dst, ann):
        dst.mkdir(parents=True, exist_ok=True)
        for src_child in src.iterdir():
            dst_child = dst / src_child.name
            ann_child = ann / src_child.name
            if src_child.is_dir():
                if src_child.name not in {'__pycache__'}:
                    self._annotate(src_child, dst_child, ann_child)
            elif ann_child.exists():
                original = src_child.read_text()
                aofile = AOFile(ann_child)
                annotated = aofile.render(original)
                dst_child.write_text(annotated)
                mtime0 = src_child.stat().st_mtime
                mtime1 = ann_child.stat().st_mtime
                if mtime1 > mtime0:
                    times = (ann_child.stat().st_atime, mtime1)
                else:
                    times = (src_child.stat().st_atime, mtime0)
                os.utime(dst_child, times)
            else:
                shutil.copy2(src_child, dst_child)

    def copy_doc(self):
        src_dir = self.home / 'src' / self.get_doc_dir()
        dst_dir = self.home / 'tmp' / self.get_doc_dir()
        mod_dir = self.home / 'mod'
        if mod_dir.exists():
            self._annotate(src_dir, dst_dir, mod_dir)
        else:
            if not dst_dir.exists() or not src_dir.samefile(dst_dir):
                shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns('.git'))
        for link in (self.get_src_links() or []):
            self._create_symlink(self.home / 'tmp' / link, self.home / 'src' / link)

    def _link_dir(self, target_dir, source_dir):
        if source_dir:
            (self.home / target_dir).mkdir(exist_ok=True)
            self._create_symlink(self.home / 'tmp' / source_dir, self.home / target_dir)

    def link_msg(self):
        self._link_dir('msg', self.get_msg_dir())

    def link_bld(self):
        self._link_dir('bld', self.get_bld_dir())

    def copy_pub(self):
        htm_dir = self.get_htm_dir()
        if htm_dir:
            src = self.home / 'bld' / htm_dir
            if src.exists():
                ignore = shutil.ignore_patterns('.*')
                dst = self.home / 'pub'
                for child in src.iterdir():
                    if child.name.startswith('.'):
                        continue
                    if child.is_dir():
                        shutil.copytree(child, dst / child.name, ignore=ignore)
                    else:
                        shutil.copy2(child, dst / child.name)

                # create empty files
                for name in ['.nojekyll']:
                    path = dst / name
                    if not path.exists():
                        path.write_text('')

                # create CNAME
                if self.cname:
                    (dst / 'CNAME').write_text(self.cname)


class DefaultProject(Project):
    kind = 'python-docs-ko'
    msg_repo = meta.String()
    ignores = meta.String[:](required=True)
    deprecated = meta.String[:](required=True)

    def get_doc_dir(self):
        return 'Doc'

    def get_src_links(self):
        return [
            'Misc',
            'README.rst',
            'LICENSE',
            'Include/Python.h',
            'Python/ceval.c',
            'Include/patchlevel.h',
            'Parser/Python.asdl',
            'Tools/scripts/diff.py',
            'Lib/test/exception_hierarchy.txt',
            'Tools/scripts/serve.py',
            'Grammar/Grammar',
        ]

    def get_msg_dir(self):
        return 'locale/ko/LC_MESSAGES'

    def get_bld_dir(self):
        return 'Doc/build'

    def get_htm_dir(self):
        return 'html'

    def get_build_cmd(self, *, rebuild=False):
        if rebuild:
            return "make VENVDIR=../../.. SPHINXOPTS='-D locale_dirs=../locale -D language=ko -D gettext_compact=0' autobuild-dev-html"
        else:
            return "make VENVDIR=../../.. SPHINXOPTS='-D locale_dirs=../locale -D language=ko -D gettext_compact=0 -A daily=1 -A switchers=1' html"

    def get_build_dir(self):
        return 'Doc'

    def setup(self):
        app = App()
        if self.msg_repo:
            msg_dir = app.home / self.name / 'msg'
            if not (msg_dir / '.git').exists():
                git_clone(self.msg_repo, msg_dir, '3.8')
        if not app.config.docker:
            try:
                shell(f'{app.config.docker_cmd} image inspect {app.image}', capture=True)
            except:
                shell(f'{app.config.docker_cmd} pull {app.image}')

    def docker_build(self, *, rebuild=False):
        if self.name == 'python-docs-ko':
            app = App()
            home = str(app.home / 'python-docs-ko')
            volumes = ' '.join(f'-v {home}/{x}:/python-docs-ko/python-docs-ko/{x}' for x in (
                'project.yaml',
                'msg',
                'bld',
            ))
            options = ' --rebuild' if rebuild else ''
            return shell(f'{app.config.docker_cmd} run --rm -i {volumes} {app.image} build{options}', chdir=home)
        else:
            super().docker_build(rebuild=rebuild)
