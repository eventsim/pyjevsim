import pathlib
import setuptools

README = pathlib.Path("README.md").read_text(encoding="utf-8")

setuptools.setup(
    name="pyjevsim",
    version="1.1.6",
    license="MIT",
    author="Changbeom Choi",
    author_email="me@cbchoi.info",
    description="A library that provides a Modeling & Simulation Environment for Discrete Event System Formalism",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/eventsim/pyjevsim",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
