from setuptools import find_packages, setup
from io import open

readme = open('README.rst', encoding='utf-8').read()

setup(
    name='opositest',
    version='0.6.0',
    packages=find_packages(),
    include_package_data=True,
    license='MIT License',
    description='A configurable quiz app for Django.',
    long_description=readme,
    url='https://github.com/purusello/opositest',
    author='Tom Walker',
    author_email='purusello@gmail.com',
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires=[
        'django-model-utils>=3.1.1',
        'Django>=1.8.19',
        'Pillow>=4.0.0',
        'django>=1.8.19',
        'mysqlclient>=1.4',
        'six>=0.0',
        'reportlab>=3.5',
        'setuptools>=41.2',
        'sqlparse>=0.3',
        'pytz>=2019.2',
        'wheel>=0.33.6',
        'django-widget-tweaks >=1.0'
    ],
    test_suite='runtests.runtests'
)
