FROM python:3.7.3 as build

# Home
WORKDIR /python-docs-ko

# create venv
RUN python -m venv .

# create project directory
RUN mkdir python-docs-ko

# git clone cpython
RUN git clone -b 3.7 --single-branch https://github.com/flowdas/cpython python-docs-ko/src
RUN rm -rf python-docs-ko/src/.git
RUN mkdir -p python-docs-ko/src/locale/ko/LC_MESSAGES

# install python-doc-ko
COPY setup.py README.rst VERSION docker.config.json ./
COPY flowdas ./flowdas/
RUN ./bin/pip install .[docker]
RUN rm -rf setup.py README.rst VERSION flowdas
RUN mv docker.config.json config.json

# finalize
FROM python:3.7.3-slim
COPY --from=build /python-docs-ko /python-docs-ko/
RUN set -ex \
    && apt-get update \
    && apt-get install make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
ENTRYPOINT ["/python-docs-ko/bin/pdk"]
