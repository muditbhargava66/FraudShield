# setup.py

from setuptools import setup, find_packages

setup(
    name='FraudShield',
    version='1.0.0',
    description='Anomaly Detection Pipeline for Fraud Detection',
    author='Mudit Bhargava',
    author_email='muditbhargava666@gmail.com',
    packages=find_packages(),
    install_requires=[
        'numpy',
        'pandas',
        'scikit-learn',
        'xgboost',
        'sqlalchemy',
        'psycopg2-binary',
        'pybind11',
        'apache-airflow',
        'pytest',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)