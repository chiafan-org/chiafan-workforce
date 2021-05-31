from setuptools import setup, find_packages

setup(
    name='chiafan-workforce',
    version='0.2.0',
    description='The Chia Plotter ToolKit',
    author='Break Yang',
    author_email='breakds@gmail.com',
    # find_package() without any arguments will serach the same
    # directory as the setup.py for modules and packages.
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'chiafan=chiafan.app:main',
        ],
    },
    python_requires='>=3.6',
)
