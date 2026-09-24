import io
import json
import os
import argparse
import subprocess
import unittest
from unittest import mock

from cli50 import __main__


class PypiReleasesTestCase(unittest.TestCase):
    def test_pypi_releases_uses_standard_library_response(self):
        payload = io.BytesIO(b'{"releases": {"8.0.1": [], "8.0.0": []}}')

        with mock.patch("urllib.request.urlopen", return_value=payload) as urlopen:
            self.assertEqual(__main__.pypi_releases(), {"8.0.1": [], "8.0.0": []})

        urlopen.assert_called_once_with("https://pypi.org/pypi/cli50/json", timeout=10)

    def test_main_ignores_invalid_pypi_json(self):
        self._assert_update_check_failure_is_ignored(
            json.JSONDecodeError("Expecting value", "", 0)
        )

    def test_main_ignores_missing_pypi_releases(self):
        self._assert_update_check_failure_is_ignored(KeyError("releases"))

    def test_main_compares_versions_semantically(self):
        args = argparse.Namespace(
            directory=os.getcwd(),
            dotfile=[],
            fast=False,
            jekyll=False,
            login=False,
            port=[],
            stop=False,
            tag=__main__.TAG,
        )

        with mock.patch.object(__main__, "__version__", "10.0.0"), \
             mock.patch("argparse.ArgumentParser.parse_args", return_value=args), \
             mock.patch.object(__main__, "pypi_releases", return_value={"9.9.9": []}), \
             mock.patch("shutil.which", return_value=None), \
             mock.patch("builtins.input") as prompt, \
             self.assertRaises(SystemExit) as raised:
            __main__.main()

        self.assertEqual(raised.exception.code, 2)
        prompt.assert_not_called()

    def test_pull_falls_back_when_manifest_lookup_fails(self):
        error = subprocess.CalledProcessError(1, ["docker", "manifest", "inspect"])

        with mock.patch("subprocess.check_output", side_effect=error), \
             mock.patch("subprocess.call") as docker_pull:
            __main__.pull("cs50/cli", "latest")

        docker_pull.assert_called_once_with(
            ["docker", "pull", "cs50/cli:latest"], stderr=__main__.subprocess.DEVNULL
        )

    def _assert_update_check_failure_is_ignored(self, error):
        args = argparse.Namespace(
            directory=os.getcwd(),
            dotfile=[],
            fast=False,
            jekyll=False,
            login=False,
            port=[],
            stop=False,
            tag=__main__.TAG,
        )

        with mock.patch.object(__main__, "__version__", "8.0.1"), \
             mock.patch("argparse.ArgumentParser.parse_args", return_value=args), \
             mock.patch.object(__main__, "pypi_releases", side_effect=error), \
             mock.patch("shutil.which", return_value=None), \
             self.assertRaises(SystemExit) as raised:
            __main__.main()

        self.assertEqual(raised.exception.code, 2)
