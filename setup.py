import setuptools

setuptools.setup(
    name="pyevsim",
    version="1.1.6",
    license="MIT",
    author="Changbeom Choi",
    author_email="me@cbchoi.info",
    description="A library that provides a Modeling & Simulation Environment for Discrete Event System Formalism",
    long_description=open("README.md").read(),
    url="https://github.com/eventsim/pyevsim",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
