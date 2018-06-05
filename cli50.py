#!/usr/bin/env python3

import signal
import sys
signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(1))

import argparse
import distutils.spawn
import inflect
import os
import pexpect
import pkg_resources
import re
import shlex 
import shutil
import subprocess


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
        parser.error(_("%s: no such directory") % args['directory'])

    # Log into container
    if args["login"]:

        # If container specified
        if isinstance(args["login"], str):
            try:
                print(ports(args["login"]))
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
        if not containers:
            sys.exit("No containers are running.")

        # Ask whether to use a running container
        for ID, Image, RunningFor, Mounts in containers:
            while True:
                prompt = _(f"Log into {Image}, started {RunningFor}")
                if Mounts:
                    prompt += _(" with %s mounted") % inflect.engine().join(Mounts)
                prompt += "? [Y] "
                stdin = input(prompt)
                if re.match("^\s*(?:y|yes)?\s*$", stdin, re.I):
                    try:
                        print(ports(ID))
                        login(ID)
                    except:
                        sys.exit(1)
                    else:
                        sys.exit(0)
                else:
                    break
        else:
            sys.exit(0)

    # Pull image if not found locally, autoupdate unless skipped
    try:
        subprocess.check_call(["docker", "image", "inspect", image], stdout=subprocess.DEVNULL) 
        assert args["fast"]
    except (AssertionError, subprocess.CalledProcessError):
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
            sys.exit(_(f"{gitconfig}: no such directory"))
        options += ["--volume", f"{gitconfig}:/home/ubuntu/.gitconfig:ro"]

    # Mount ~/.ssh read-only, if exists
    if args["ssh"]:
        ssh = os.path.join(os.path.expanduser("~"), ".ssh")
        if not os.path.isdir(ssh):
            sys.exit(_(f"{ssh}: no such directory"))
        options += ["--volume", f"{ssh}:/home/ubuntu/.ssh:ro"]

    # Mount directory in new container
    try:

        # Create container
        columns, lines = shutil.get_terminal_size()  # Temporary
        options += [ # Temporary
            "--env", f"COLUMNS={str(columns)},LINES={str(lines)}",
            "--env", f"LINES={str(lines)}"]
        container = subprocess.check_output(["docker", "create"] + options + [image, "bash", "--login"]).decode("utf-8").rstrip()

        # Start container
        child = pexpect.spawn("docker", ["start", "--attach", "--interactive", container], dimensions=(lines, columns),
                              env=dict(os.environ, COLUMNS=str(columns), LINES=str(lines)))  # Temporary

        # Once running, list port mappings
        child.expect(".*\$")
        print(ports(container))

        # Let user interact with container
        print(child.after.decode("utf-8"), end="")
        child.interact()

    except (pexpect.exceptions.ExceptionPexpect, subprocess.CalledProcessError):
        sys.exit(1)
    else:
        sys.exit(0)


def handler(number, frame):
    """Handle SIGINT."""
    print()
    sys.exit(0)


def login(container):
    """Log into container."""
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


def ports(container):
    """Return port mappings for container."""
    return subprocess.check_output([
        "docker", "ps",
        "--filter", f"id={container}",
        "--format", "{{.Ports}}",
        "--no-trunc"
    ]).decode("utf-8").rstrip()


if __name__ == "__main__":
    main()