# setup.py
from setuptools import setup, find_packages

setup(
    name="server-monitoring-system",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask>=2.3.0",
        "twilio>=8.0.0",
        "python-dotenv>=1.0.0",
        "pytz>=2023.3",
        "PyYAML>=6.0.0",
        "requests>=2.31.0",
    ],
)