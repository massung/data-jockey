from setuptools import setup

setup(
    name='data-jockey',
    version='0.1',
    packages=[
        'jockey',
    ],
    py_modules=[
        'main',
    ],
    install_requires=[
        'click>=7.0',
        'matplotlib>=3.3',
        'orjson>=3.4',
        'pandas>=1.1',
        'ply>=3.11',
        'python-dotenv>=0.10',
        'requests>=2.21',
        'rich>=9.2',
        'smart-open>=3.0',
        'sqlalchemy>=1.3',
    ],
    entry_points={
        'console_scripts': ['jockey=jockey.main:cli'],
    },
    author='Jeffrey Massung',
    author_email='massung@gmail.com',
    description='jockey data query scripting language',
    keywords='data jockey pandas query sql dataframe script language',
    url='https://github.com/massung/data-jockey',
    project_urls={
        'Issues': 'https://github.com/massung/data-jockey/issues',
        'Source': 'https://github.com/massung/data-jockey',
    },
    license='BSD3',
)
