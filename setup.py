# python setup.py sdist bdist_wheel; twine upload dist/*

from setuptools import setup, find_packages
import os
from io import open

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

requirements = ['prometheus-client', 'flask']  # Required for end user.

version = os.environ.get('GITHUB_REF', 'local')
version = version.split("/")[-1]
if version.startswith("v"):
    version = version[1:]
print(f"VERSION={version}")
 
setup(
    name='prometheus-flask-instrumentator',
    version=version,
    description='Istruments Flask API transparently',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords='prometheus instrumentation flask monitoring metrics',
    url='https://github.com/trallnag/prometheus-flask-instrumentator',
    author='Tim Schwenke',
    author_email='tim.schwenke@outlook.com',

    classifiers=[
        'Development Status :: 4 - Beta',  # 5 - Production/Stable
        'Intended Audience :: Developers',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Logging',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],

    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.6',
    install_requires=requirements,
)
