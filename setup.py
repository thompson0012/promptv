from setuptools import setup, find_packages

setup(
    name='promptv',
    version='0.1.7',
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'promptv': ['resources/*.yaml'],
    },
    install_requires=[
        'click>=8.0.0',
        'pydantic>=2.12.5',
        'jinja2>=3.1.4',
        'pyyaml>=6.0.2',
        'rich>=13.9.4',
        'tiktoken>=0.8.0',
        'textual>=0.84.0',
        'openai>=1.0.0',
        'anthropic>=0.18.0',
        'httpx>=0.25.0',
    ],
    entry_points={
        'console_scripts': [
            'promptv=promptv.cli:cli',
        ],
    },
    author='Thompson Wong',
    author_email='thompsonwong@labs21.dev',
    description='A CLI tool for managing prompts locally with versioning',
    python_requires='>=3.11',
)