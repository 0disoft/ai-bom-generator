from hashlib import sha256
from io import BytesIO
import unittest
from unittest.mock import patch

from scripts import spdx_validation_resources as resources


class ResourceTests(unittest.TestCase):
    def setUp(self):
        resources.resource.cache_clear()

    def tearDown(self):
        resources.resource.cache_clear()

    def test_verified_resource_is_downloaded_once(self):
        body = b"public test resource"
        entry = ("https://example.invalid/resource", sha256(body).hexdigest())
        with patch.dict(resources.RESOURCES, {"test": entry}), patch.object(resources, "urlopen", return_value=BytesIO(body)) as fetch:
            self.assertEqual(resources.resource("test"), body.decode())
            self.assertEqual(resources.resource("test"), body.decode())
            fetch.assert_called_once_with(entry[0], timeout=30)

    def test_drift_and_oversized_resource_fail_closed(self):
        for body, limit, diagnostic in [(b"changed", 100, "integrity"), (b"large", 2, "size")]:
            with patch.object(resources, "MAX_RESOURCE_BYTES", limit), patch.object(resources, "urlopen", return_value=BytesIO(body)):
                with self.assertRaisesRegex(resources.ResourceError, diagnostic):
                    resources.resource("context")

    def test_network_error_is_distinct_and_not_cached(self):
        with patch.object(resources, "urlopen", side_effect=TimeoutError) as fetch:
            for _ in range(2):
                with self.assertRaisesRegex(resources.ResourceError, "network-error"):
                    resources.resource("context")
            self.assertEqual(fetch.call_count, 2)
