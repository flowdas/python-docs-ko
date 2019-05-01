# Copyright 2018 Nitmus Co., Ltd., 오동권(Dong-gweon Oh) <paul.oh@nitmus.com>, All rights reserved.
from setuptools import setup

setup_requires = [
]

install_requires = [
    'flowdas',
]

tests_require = [
]

docker_require = sum([
    install_requires,
], [
    'blurb',
    'python-docs-theme',
    'requests',
    'sentry-sdk',
    'sphinx',
])

dev_require = sum([
    install_requires,
    tests_require,
], [
    'twine',
])

setup(
    name='python-docs-ko',
    version=open('VERSION').read().strip(),
    url='https://www.flowdas.com/pages/python-docs-ko.html',
    project_urls={
        "Code": "https://github.com/flowdas/python-docs-ko",
        "Issue tracker": "https://github.com/flowdas/python-docs-ko/issues",
    },
    description='The toolkit for Korean translation of the Python documentation.',
    long_description=open('README.rst').read(),
    author='Flowdas Inc.',
    author_email='prospero@flowdas.com',
    packages=[
        'flowdas.pdk',
    ],
    package_data={
    },
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    extras_require={
        'dev': dev_require,
        'docker': docker_require,
    },
    scripts=[],
    entry_points={
        'console_scripts': [
            'pdk=flowdas.pdk.app:App.main',
        ],
    },
    zip_safe=False,
    python_requires=">=3.7",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
)
