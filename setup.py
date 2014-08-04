from distutils.core import setup


with open("README.md") as f:
    readme = f.read()

setup(
    name="pybelsberg",
    description="A proof-of-concept library of Babelsberg for Python",
    long_description=readme,
    version="0.0.1",
    author="Babelsberg contributors",
    author_email="timfelgentreff+pybelsberg@gmail.com",
    url="https://github.com/babelsberg/pybelsberg",
    packages=["pybelsberg"],
    data_files=["README.md"]
)
