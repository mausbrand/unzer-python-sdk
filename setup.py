import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="unzer",
    version="0.0.1",
    author="Mausbrand Informationssysteme GmbH",
    author_email="team@viur.dev",
    description="An unofficial python SDK for unzer.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mausbrand/unzer-python-sdk",
    project_urls={
        "Bug Tracker": "https://github.com/mausbrand/unzer-python-sdk/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=2.6, <3",
)
