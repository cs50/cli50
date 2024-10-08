import signal
import sys

signal.signal(signal.SIGINT, lambda signum, frame: sys.exit(1))

import argparse
import gettext
import os
import re
import requests
import shutil
import subprocess
import tzlocal

from importlib.resources import files
from packaging import version

from . import __version__

# Image to use
IMAGE = "cs50/cli"

# Label to use
LABEL = "cli50"

# Default ports to publish
PORTS = [
    5000,  # Flask
    8080  # http-server
]

# Tag to use
TAG = "latest"

# Internationalization
t = gettext.translation("cli50", str(files("cli50").joinpath("locale")), fallback=True)
t.install()


def main():

    # Listen for ctrl-c
    signal.signal(signal.SIGINT, handler)

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dotfile", action="append", default=[],
                        help=_("dotfile in your $HOME to mount read-only in container's $HOME"), metavar="DOTFILE")
    parser.add_argument("-f", "--fast", action="store_true", default=False, help=_("don't check for updates"))
    parser.add_argument("-j", "--jekyll", action="store_true", help=_("serve Jekyll site"))
    parser.add_argument("-l", "--login", const=True, default=False, help=_("log into CONTAINER"), metavar="CONTAINER", nargs="?")
    parser.add_argument("-p", "--port", action="append", default=[], help=_("publish PORT"), metavar="PORT", type=int)
    parser.add_argument("-S", "--stop", action="store_true", help=_("stop any containers"))
    parser.add_argument("-t", "--tag", default=TAG, help=_("start {}:TAG, else {}:{}").format(IMAGE, IMAGE, TAG), metavar="TAG")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s {}".format(__version__) if __version__ else "Locally installed.")
    parser.add_argument("directory", default=os.getcwd(), metavar="DIRECTORY", nargs="?", help=_("directory to mount, else $PWD"))
    args = vars(parser.parse_args())

    # Check PyPI for newer version
    if __version__ and not args["fast"]:
        try:
            release = max(requests.get("https://pypi.org/pypi/cli50/json").json()["releases"], key=version.parse)
            assert release <= __version__
        except requests.RequestException:
            pass
        except AssertionError:
            try:
                response = input("A newer version of cli50 is available. Upgrade now? [Y/n] ")
            except EOFError:
                pass
            else:
                if response.strip().lower() not in ["n", "no"]:
                    print("Run `pip3 install --upgrade cli50` to upgrade. Then re-run cli50.")
                    sys.exit(0)

    # Check if Docker installed
    if not shutil.which("docker"):
        parser.error(_("Docker not installed."))

    # Check if Docker running
    try:
        stdout = subprocess.check_call(["docker", "info"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=10)
    except subprocess.CalledProcessError:
        sys.exit("Docker not running.")
    except subprocess.TimeoutExpired:
        sys.exit("Docker not responding.")

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
                "--format", "{{.ID}}\t{{.Image}}\t{{.RunningFor}}\t{{.Status}}\t{{.Mounts}}",
                "--no-trunc"
            ]).decode("utf-8")
        except subprocess.CalledProcessError:
            sys.exit(1)
        else:
            containers = []
            for line in stdout.rstrip().splitlines():
                ID, Image, RunningFor, Status, *Mounts = line.rstrip().split("\t")
                Mounts = Mounts[0].split(",") if Mounts else []
                Mounts = [re.sub(r"^/host_mnt", "", Mount) for Mount in Mounts if not re.match(r"^[0-9a-fA-F]{64}$", Mount)]  # Ignore hashes
                containers.append((ID, Image, RunningFor.lower(), Status.lower(), Mounts))
        if not containers:
            sys.exit("No containers are running.")

        # Ask whether to use a running container
        import inflect, textwrap
        for ID, Image, RunningFor, Status, Mounts in containers:
            while True:
                prompt = _("Log into {}, created {}, {}").format(Image, RunningFor, Status)
                if Mounts:
                    prompt += _(", with {} mounted").format(inflect.engine().join(Mounts))
                prompt += "? [Y/n]    "  # Leave room when wrapping for "yes"
                columns, lines = shutil.get_terminal_size()
                prompt = "\n".join(textwrap.wrap(prompt, columns, drop_whitespace=False)).strip() + " "
                try:
                    stdin = input(prompt)
                except EOFError:
                    break
                if re.match(r"^\s*(?:y|yes)?\s*$", stdin, re.I):
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

    # Stop containers
    if args["stop"]:
        try:
            stdout = subprocess.check_output([
                "docker", "ps",
                "--all",
                "--filter", f"label={LABEL}",
                "--format", "{{.ID}}"
            ]).decode("utf-8")
            for ID in stdout.rstrip().splitlines():
                subprocess.check_call(["docker", "stop", "--time", "0", ID])
            sys.exit(0)
        except subprocess.CalledProcessError:
            sys.exit(1)

    # Ensure directory exists
    directory = os.path.realpath(args["directory"])
    if not os.path.isdir(directory):
        parser.error(_("{}: no such directory").format(args['directory']))

    # Check Docker Hub for newer image
    if not args["fast"]:

        # Remote manifest
        import json
        try:
            RemoteManifest = json.loads(subprocess.check_output([
                "docker", "manifest", "inspect", f"{IMAGE}:{args['tag']}", "--verbose"
            ], stderr=subprocess.DEVNULL).decode("utf-8"))
        except subprocess.CalledProcessError:
            RemoteManifest = None

        # Local digest
        try:
            LocalDigest = json.loads(subprocess.check_output([
                "docker", "inspect", f"{IMAGE}:{args['tag']}"
            ], stderr=subprocess.DEVNULL).decode("utf-8"))[0]
        except (IndexError, KeyError, subprocess.CalledProcessError):
            LocalDigest = None

        # Pull image if no local digest
        if not LocalDigest:
            pull(IMAGE, args["tag"])

        # Ask to update image if local digest doesn't match any remote image digests
        elif (LocalDigest and RemoteManifest) and \
            LocalDigest['Id'] not in [manifest['SchemaV2Manifest']['config']['digest'] for manifest in RemoteManifest]:

            try:
                response = input(f"A newer version of {IMAGE}:{args['tag']} is available. Pull now? [Y/n] ")
            except EOFError:
                pass
            else:
                if response.strip().lower() not in ["n", "no"]:
                    pull(IMAGE, args["tag"])

    # Options
    workdir = "/mnt"
    options = ["--detach",
               "--env", f"LOCAL_WORKSPACE_FOLDER={directory}",
               "--env", f"TZ={tzlocal.get_localzone_name()}",
               "--env", f"WORKDIR={workdir}",
               "--interactive",
               "--label", LABEL,
               "--rm",
               "--security-opt", "seccomp=unconfined",  # https://stackoverflow.com/q/35860527#comment62818827_35860527, https://github.com/apple/swift-docker/issues/9#issuecomment-328218803
               "--tty",
               "--volume", directory + ":" + workdir,
               "--volume", "/var/run/docker.sock:/var/run/docker-host.sock",  # https://github.com/devcontainers/features/blob/main/src/docker-outside-of-docker/devcontainer-feature.json
               "--workdir", workdir]

    # Check for locale
    if lang := os.getenv("LANG"):
        options += ["--env", f"LANG={lang}"]

    # Validate ports
    if not args["port"]:
        args["port"] = PORTS
    for port in args["port"]:
        if port < 1024 or port > 65535:
            sys.exit(f"Invalid port: {port}")
        options += ["--expose", f"{port}"]

    # Home directory
    home = os.path.join(os.path.expanduser("~"), "")

    # Mount each dotfile in user's $HOME read-only in container's $HOME
    for dotfile in args["dotfile"]:
        if dotfile.startswith("/") and not dotfile.startswith(home):
            sys.exit(_("{}: not in your $HOME").format(dotfile))
        elif dotfile.startswith(os.path.join("~", "")):
            dotfile = os.path.expanduser(dotfile)
        else:
            dotfile = os.path.join(home, dotfile)
        if not os.path.exists(dotfile):
            sys.exit(_("{}: No such file or directory").format(dotfile))
        if not dotfile[len(home):].startswith("."):
            sys.exit(_("{}: Not a dotfile").format(dotfile))
        options += ["--volume", "{}:/home/ubuntu/{}:ro".format(dotfile, dotfile[len(home):])]

    # Default CMD
    cmd = ["bash", "--login"]

    # Serve Jekyll site
    if args["jekyll"]:
        cmd += ["-c", "bundle install && bundle exec jekyll serve --host 0.0.0.0 --port 8080"]

    # Mount directory in new container
    try:

        # Publish all exposed ports to random ports
        container = subprocess.check_output(["docker", "run"] + options +
                                            ["--publish-all"] +
                                            [f"{IMAGE}:{args['tag']}"] + cmd).decode("utf-8").rstrip()

        # Start Docker-outside-of-Docker (if supported by TAG)
        # a la https://github.com/devcontainers/features/blob/main/src/docker-outside-of-docker/install.sh
        try:
            subprocess.check_output(["docker", "exec", "--detach", container, "sudo", "/etc/init.d/docker", "start"])
        except subprocess.CalledProcessError:
            pass

        # List port mappings
        print(ports(container))

        # Let user interact with container
        print(subprocess.check_output(["docker", "logs", container]).decode("utf-8"), end="")
        subprocess.call(["docker", "attach", container])

    except subprocess.CalledProcessError:
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

    # Get mappings
    output = subprocess.check_output([
        "docker", "ps",
        "--filter", f"id={container}",
        "--format", "{{.Ports}}",
        "--no-trunc"
    ]).decode("utf-8").rstrip()

    # Filter out IPv6 mappings as unneeded
    mappings = list(filter(lambda mapping: not mapping.startswith(":::"), re.split(r", ", output)))
    return ", ".join(mappings)


def pull(image, tag):
    """Pull image as needed."""
    import json
    try:

        # Get the latest manifest from registry
        RemoteManifest = json.loads(subprocess.check_output([
            "docker", "manifest", "inspect", f"{image}:{tag}", "--verbose"
        ], stderr=subprocess.DEVNULL).decode("utf-8"))

        # Get local image id, if any
        localImageId = json.loads(subprocess.check_output([
            "docker", "inspect", f"{image}:{tag}"], stderr=subprocess.DEVNULL).decode("utf-8"))[0]['Id']

        # Pull latest if local image id does not match any digest in the manifest
        assert localImageId in [manifest['SchemaV2Manifest']['config']['digest'] for manifest in RemoteManifest] == True

    except (AssertionError, requests.exceptions.ConnectionError, subprocess.CalledProcessError):

        # Pull image
        subprocess.call(["docker", "pull", f"{image}:{tag}"], stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
