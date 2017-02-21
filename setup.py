from setuptools import setup, find_packages

setup(
    name='scscp',
    version='0.1.1',
    description='Implementation of the SCSCP protocol',
    url='https://github.com/OpenMath/py-scscp',
    author='Luca De Feo',
    license='MIT',
    classifiers=[
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    keywords='openmath scscp',
    packages=find_packages(),
    install_requires=['openmath>=0.1.1', 'pexpect'],
)
