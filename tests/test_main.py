import io
import unittest
from unittest import mock

from cli50 import __main__


class PypiReleasesTestCase(unittest.TestCase):
    def test_pypi_releases_uses_standard_library_response(self):
        payload = io.BytesIO(b'{"releases": {"8.0.1": [], "8.0.0": []}}')

        with mock.patch("urllib.request.urlopen", return_value=payload) as urlopen:
            self.assertEqual(__main__.pypi_releases(), {"8.0.1": [], "8.0.0": []})

        urlopen.assert_called_once_with("https://pypi.org/pypi/cli50/json")
