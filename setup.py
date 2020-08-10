from setuptools import setup, find_packages
from pathlib import Path

setup(
    name='di_container',
    version='2.1.1',
    packages=find_packages(),
    install_requires=Path('requirements.txt').read_text(encoding='utf-8').splitlines(),
    python_requires='>=3.5.0',
    author='drorey',
    description='A dependency injection container for Python, using semantics similar to Castle Windsor.',
    long_description=Path('README.md').read_text(encoding='utf-8'),
    long_description_content_type='text/markdown'
)
