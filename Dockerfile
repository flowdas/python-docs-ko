FROM python:3.7.4 as build

# Home
WORKDIR /python-docs-ko

# create venv
RUN python -m venv .

# create project directory
RUN mkdir python-docs-ko

# git clone cpython
RUN git clone -b v3.7.4 --single-branch https://github.com/python/cpython python-docs-ko/src
RUN rm -rf python-docs-ko/src/.git
RUN mkdir -p python-docs-ko/src/locale/ko/LC_MESSAGES

# install python-doc-ko
COPY setup.py README.rst VERSION docker.config.json ./
COPY flowdas ./flowdas/
RUN ./bin/pip install .[all]
RUN rm -rf setup.py README.rst VERSION flowdas
RUN mv docker.config.json config.json

# test
RUN bin/pdk init https://github.com/python/python-docs-ko.git
RUN bin/pdk build
RUN cp python-docs-ko/bld/NEWS python-docs-ko/src/Misc/NEWS
RUN rm -rf python-docs-ko/msg python-docs-ko/bld python-docs-ko/tmp

# finalize
FROM python:3.7.4-slim
RUN set -ex \
    && apt-get update \
    && apt-get install make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
COPY --from=build /python-docs-ko /python-docs-ko/
ENTRYPOINT ["/python-docs-ko/bin/pdk"]
