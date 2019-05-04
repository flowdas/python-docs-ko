python-docs-ko
==============

A toolkit for Korean translation of the Python documentation.

Prerequisites
-------------

- Git
- Docker

Install
-------

::

    python3.7 -m venv <work-dir>
    cd <work-dir>
    source bin/activate
    pip install python-docs-ko
    pdk init <your-python-docs-ko-fork>

    # translate *.po files in python-docs-ko/

Build
-----

::

    pdk build
    open html/index.html
