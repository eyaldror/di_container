from setuptools import setup, find_packages
from pathlib import Path

UTF8 = 'utf-8'


def get_version():
    version_var = '__version__'
    package_file = 'di_container/__init__.py'
    for line in Path(package_file).read_text(encoding=UTF8).splitlines():
        if line.startswith(version_var):
            return line.partition('=')[-1].strip()[1:-1]  # remove whitespaces and the quotation marks
    else:
        raise RuntimeError(f'Failed to find {version_var} in {package_file}.')


setup(
    name='di_container',
    version=get_version(),
    install_requires=Path('requirements.txt').read_text(encoding=UTF8).splitlines(),
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
