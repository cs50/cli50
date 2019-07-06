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
    message_extractors = {
        'cli50': [('**.py', 'python', None),],
    },
    description="This is CS50 CLI, with which you can mount a directory inside of an Ubuntu container.",
    license="GPLv3",
    install_requires=["inflect", "requests"],
    keywords="cli50",
    name="cli50",
    python_requires=">=3.6",
    packages=["cli50"],
    entry_points={
        "console_scripts": ["cli50=cli50.__main__:main"]
    },
    url="https://github.com/cs50/cli50",
    version="3.1.0",
    include_package_data=True
)
