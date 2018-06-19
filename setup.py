from setuptools import setup
import glob
import os
import subprocess
from pathlib import Path

def create_mo_files():
    """Compiles .po files in local/LANG to .mo files and returns them as array of data_files"""

    mo_files=[]
    for prefix in glob.glob("locale/*/LC_MESSAGES"):
        prefix = Path(prefix)
        for _,_,files in os.walk(prefix):
            for file in map(Path, files):
                if file.suffix == ".po":
                    po_file = prefix / file
                    mo_file = prefix / (file.stem + ".mo")
                    subprocess.call(["msgfmt", "-o", mo_file, po_file])
                    mo_files.append((str("submit50" / prefix / "LC_MESSAGES"), [str(mo_file)]))

    return mo_files

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
    install_requires=["inflect"],
    keywords="cli50",
    name="cli50",
    python_requires=">=3.6",
    py_modules=["cli50"],
    entry_points={
        "console_scripts": ["cli50=cli50:main"]
    },
    url="https://github.com/cs50/cli50",
    version="2.3.1",
    data_files=create_mo_files()
)
