python-docs-ko
==============

A toolkit for Korean translation of the Python documentation.

Prerequisites
-------------

- Git - 직접 사용활 수 있어야 하고, PATH 에 경로가 설정되어 있어야 합니다.
- Docker - 직접 사용할 필요는 없지만, 설치되어 있어야 하고, PATH 에 경로가 설정되어 있어야 합니다. Docker for Desktop 이면 충분합니다.

Install
-------

::

    python3.7 -m venv <work-dir>
    cd <work-dir>
    source bin/activate
    pip install python-docs-ko
    pdk init <your-python-docs-ko-fork>

    # translate *.po files in python-docs-ko/msg/

Build
-----

::

    pdk build
    open python-docs-ko/bld/html/index.html
