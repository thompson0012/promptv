from setuptools import setup, find_packages

setup(
    name='promptv',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click>=8.0.0',
    ],
    entry_points={
        'console_scripts': [
            'promptv=promptv.cli:cli',
        ],
    },
    author='Your Name',
    description='A CLI tool for managing prompts locally with versioning',
    python_requires='>=3.7',
)
