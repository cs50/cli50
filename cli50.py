#!/usr/bin/env python3

import argparse
import distutils.spawn
import gettext
import inflect
import os
import pkg_resources
import re
import shutil
import signal
import subprocess
import sys

# Internationalization
gettext.bindtextdomain("messages", "locale")
gettext.textdomain("messages")
_ = gettext.gettext

# Require Python 3.6
if sys.version_info < (3, 6):
    sys.exit(_("CS50 CLI requires Python 3.6 or higher"))

# Get version
try:
    d = pkg_resources.get_distribution("cli50")
except pkg_resources.DistributionNotFound:
    __version__ = "UNKNOWN"
else:
    __version__ = d.version

def main():

    # Listen for ctrl-c
    signal.signal(signal.SIGINT, handler)

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fast", action="store_true", help=_("skip autoupdate"))
    parser.add_argument("-g", "--git", action="store_true", help=_("mount .gitconfig"))
    parser.add_argument("-l", "--login", const=True, default=False, help=_("log into container"),
                        metavar="CONTAINER", nargs="?")
    parser.add_argument("-p", "--publish", action="append",
                        help=_("publish port(s) to ports on host"), metavar="LIST", nargs="?")
    parser.add_argument("-P", "--publish-all", action="store_true",
                        help=_("publish exposed ports to random ports on host"))
    parser.add_argument("-s", "--ssh", action="store_true", help=_("mount .ssh"))
    parser.add_argument("-S", "--stop", action="store_true", help=_("stop any containers"))
    parser.add_argument("-t", "--tag", default=None,
                        help=_("start cs50/cli:TAG, else cs50/cli:latest"), metavar="TAG")
    parser.add_argument("-V", "--version", action="version",
                        version="%(prog)s {}".format(__version__))
    parser.add_argument("directory", default=os.getcwd(), metavar="DIRECTORY",
                        nargs="?", help=_("directory to mount, else $PWD"))
    args = vars(parser.parse_args())

    # Check for Docker
    if not distutils.spawn.find_executable("docker"):
        parser.error(_("Docker not installed."))

    # Image to use
    image = f"cs50/cli:{args['tag']}" if args["tag"] else "cs50/cli"

    # Stop containers
    if args["stop"]:
        try:
            stdout = subprocess.check_output([
                "docker", "ps",
                "--all",
                "--format", "{{.ID}}\t{{.Image}}"
            ]).decode("utf-8")
            for line in stdout.rstrip().splitlines():
                ID, Image = line.split("\t")
                if Image == image:
                    subprocess.check_call(["docker", "stop", "--time", "0", ID])
            sys.exit(0)
        except subprocess.CalledProcessError:
            sys.exit(1)

    # Ensure directory exists
    directory = os.path.realpath(args["directory"])
    if not os.path.isdir(directory):
        parser.error(_("{}: no such directory").format(args['directory']))

    # Log into container
    if args["login"]:

        # If container specified
        if isinstance(args["login"], str):
            try:
                login(args["login"])
            except:
                sys.exit(1)
            else:
                sys.exit(0)

        # Check for running containers
        try:
            stdout = subprocess.check_output([
                "docker", "ps",
                "--all",
                "--filter", "status=running",
                "--format", "{{.ID}}\t{{.Image}}\t{{.RunningFor}}\t{{.Mounts}}",
                "--no-trunc"
            ]).decode("utf-8")
        except subprocess.CalledProcessError:
            sys.exit(1)
        else:
            containers = []
            for line in stdout.rstrip().splitlines():
                ID, Image, RunningFor, *Mounts = line.split("\t")
                Mounts = Mounts[0].split(",") if Mounts else []
                Mounts = [Mount for Mount in Mounts if not re.match(r"^[0-9a-fA-F]{64}$", Mount)]  # Ignore hashes
                containers.append((ID, Image, RunningFor.lower(), Mounts))

        # Ask whether to use a running container
        for ID, Image, RunningFor, Mounts in containers:
            while True:
                prompt = _("Log into {}, started {}").format(Image, RunningFor)
                if Mounts:
                    prompt += _(" with {} mounted").format(inflect.engine().join(Mounts))
                prompt += "? [Y] "
                stdin = input(prompt)
                if re.match("^\s*(?:y|yes)?\s*$", stdin, re.I):
                    try:
                        login(ID)
                    except:
                        sys.exit(1)
                    else:
                        sys.exit(0)
                else:
                    break

    # Update image
    if not args["fast"]:
        try:
            subprocess.check_call(["docker", "pull", image])
        except subprocess.CalledProcessError:
            sys.exit(1)

    # Options
    options = ["--interactive",
               "--rm",
               "--security-opt", "seccomp=unconfined",  # https://stackoverflow.com/q/35860527#comment62818827_35860527
               "--tty",
               "--volume", directory + ":/home/ubuntu/workspace",
               "--workdir", "/home/ubuntu/workspace"]

    # Ports to publish
    if isinstance(args["publish"], list):
        if len(args["publish"]) == 1 and args["publish"][0] == None:  # If --publish without LIST
            options += ["--publish", "8080:8080", "--publish", "8081:8081", "--publish", "8082:8082"]
        else:  # If --publish with LIST
            for port in args["publish"]:
                if port:
                    options += ["--publish", port]
    if args["publish_all"]:
        options += ["--publish-all"]

    # Mount ~/.gitconfig read-only, if exists
    if args["git"]:
        gitconfig = os.path.join(os.path.expanduser("~"), ".gitconfig")
        if not os.path.isfile(gitconfig):
            sys.exit(_("{}: no such directory").format(gitconfig))
        options += ["--volume", f"{gitconfig}:/home/ubuntu/.gitconfig:ro"]

    # Mount ~/.ssh read-only, if exists
    if args["ssh"]:
        ssh = os.path.join(os.path.expanduser("~"), ".ssh")
        if not os.path.isdir(ssh):
            sys.exit(_("{}: no such directory").format(ssh))
        options += ["--volume", f"{ssh}:/home/ubuntu/.ssh:ro"]

    # Mount directory in new container
    try:
        columns, lines = shutil.get_terminal_size()  # Temporary
        subprocess.check_call(["docker", "run"] + options + [image, "bash", "--login"],
                              env=dict(os.environ, COLUMNS=str(columns), LINES=str(lines)))  # Temporary
    except subprocess.CalledProcessError:
        sys.exit(1)
    else:
        sys.exit(0)


def handler(number, frame):
    """Handle SIGINT."""
    print("")
    sys.exit(0)


def login(container):
    columns, lines = shutil.get_terminal_size()  # Temporary
    try:
        subprocess.check_call([
            "docker", "exec",
            "--env", f"COLUMNS={str(columns)},LINES={str(lines)}",  # Temporary
            "--env", f"LINES={str(lines)}",  # Temporary
            "--interactive",
            "--tty",
            container,
            "bash",
            "--login"
        ])
    except subprocess.CalledProcessError:
        raise RuntimeError() from None


if __name__ == "__main__":
    main()
