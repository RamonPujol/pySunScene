from setuptools import setup, find_packages

setup(
    name='WebAppSunScene',
    version='0.2',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=['Flask','pysunscene','numpy'],
    license = 'MIT',
    author = 'Gabriel Cardona',
    author_email = 'gabriel.cardona@uib.es',
)

