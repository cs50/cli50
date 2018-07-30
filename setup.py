from setuptools import setup

setup(
    author="CS50",
    author_email="sysadmins@cs50.harvard.edu",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development"
    ],
    description="This is CS50 CLI, with which you can mount a directory inside of an Ubuntu container.",
    license="GPLv3",
    install_requires=["inflect", "pexpect"],
    keywords="cli50",
    name="cli50",
    python_requires=">=3.6",
    scripts=["cli50"],
    url="https://github.com/cs50/cli50",
    version="2.4.0"
)
