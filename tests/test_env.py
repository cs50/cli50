import os
import tempfile
import unittest

from cli50.__main__ import env_options


def env_dict(options):
    return dict(option.split("=", 1) for option in options[1::2])


class EnvOptionsTestCase(unittest.TestCase):

    def test_env_options_sources_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            with open(os.path.join(directory, ".env"), "w") as file:
                file.write("FOO=bar\nexport BAZ='qux quux'\n")
            self.assertEqual(env_dict(env_options(directory)), {"FOO": "bar", "BAZ": "qux quux"})

    def test_env_options_ignores_missing_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(env_options(directory), [])
