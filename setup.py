from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().strip().splitlines()

setup(
    name='dagaar_fuel_station',
    version='0.0.1',
    description='Advanced fuel station operations and billing for ERPNext',
    author='OpenAI',
    author_email='support@example.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)
