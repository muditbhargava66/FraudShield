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
        'matplotlib',
        'seaborn',
        'sqlalchemy',
        'psycopg2-binary',
        'apache-airflow',
        'pytest',
        'flake8',
        'black',
    ],
    entry_points={
        'console_scripts': [
            'fraudshield_ingest=src.data_ingestion.data_ingestion:main',
            'fraudshield_preprocess=src.data_preprocessing.data_preprocessing:main',
            'fraudshield_train=src.model_training.train_models:main',
            'fraudshield_evaluate=src.model_evaluation.evaluation:main',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
    ],
)