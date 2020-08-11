from setuptools import setup, find_packages
from pathlib import Path

setup(
    name='di_container',
    version='2.1.1',
    install_requires=Path('requirements.txt').read_text(encoding='utf-8').splitlines(),
    author='Eyal Dror',
    description='A dependency injection container for Python, using semantics similar to Castle Windsor.',
    long_description=Path('README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown',
    url='https://github.com/eyaldror/di_container',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.5.0',
)
