from setuptools import setup, find_packages

setup(
    name='HOTBot',
    version='1.0.0',
    description='Dynamic, random, and automated event scheduler using Google Calendar',
    author='Adam Haile',
    author_email='email@adamhaile.net',
    url='https://github.com/adammhaile/HotBot',
    license='MIT',
    packages=find_packages(),
    install_requires=['httplib2', 'python-dateutil', 'google-api-python-client', 'croniter'],
    entry_points={
        'console_scripts': [
            'hotbot = hotbot:run_script'
        ]
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)
