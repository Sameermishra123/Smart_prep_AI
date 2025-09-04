from setuptools import setup,find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="SmartPrepAI",
    version="0.1",
    author="Shivam Kumar Srivastava",
    packages=find_packages(),
    install_requires = requirements,
    python_requires=">=3.11",
)