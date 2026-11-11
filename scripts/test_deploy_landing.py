"""Exercise deploy_landing.py against a temporary release tree and a local HTTP server."""
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import tarfile
import tempfile
import threading
import unittest

import deploy_landing


def page(revision=None):
    meta = f'<meta name="barbersoftly-release" content="{revision}">' if revision else ""
    return f"<html><head>{meta}</head><body>landing</body></html>".encode()


def build_archive(path, revision, tamper=False):
    files = {"index.html": page(revision), "_astro/app.css": b"body{}"}
    entries = [{"path": name, "sha256": hashlib.sha256(data).hexdigest()} for name, data in files.items()]
    if tamper:
        files["_astro/app.css"] = b"changed"
    files["deployment.json"] = json.dumps(
        {"schemaVersion": 1, "application": "landing", "revision": revision, "files": entries}
    ).encode()
    with tarfile.open(path, "w:gz") as bundle:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class DeployLandingTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "landing"
        (self.root / "uploads").mkdir(parents=True)
        bootstrap = self.root / "releases" / "bootstrap"
        bootstrap.mkdir(parents=True)
        (bootstrap / "index.html").write_bytes(page())
        (self.root / "current").symlink_to(bootstrap)
        (self.root / "previous").symlink_to(bootstrap)
        (self.root / ".deployment-target.json").write_text(json.dumps({"application": "landing"}))
        handler = partial(Quiet, directory=str(self.root / "current"))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temporary.cleanup()

    def upload(self, sha, run, tamper=False):
        release_id = f"{sha}-{run}-1"
        checksum = build_archive(self.root / "uploads" / f"{release_id}.tar.gz", sha, tamper)
        return release_id, checksum

    def current(self):
        return (self.root / "current").resolve().name

    def test_deploy_then_rollback(self):
        first, second = "a" * 40, "b" * 40
        deploy_landing.deploy(*self.upload(first, 1), base=self.root, health_url=self.url)
        deploy_landing.deploy(*self.upload(second, 2), base=self.root, health_url=self.url)
        self.assertEqual(self.current(), f"{second}-2-1")
        self.assertEqual((self.root / "previous").resolve().name, f"{first}-1-1")
        self.assertFalse(any((self.root / "uploads").iterdir()))

        deploy_landing.rollback(base=self.root, health_url=self.url)
        self.assertEqual(self.current(), f"{first}-1-1")
        self.assertEqual((self.root / "previous").resolve().name, f"{second}-2-1")

    def test_rollback_to_bootstrap_without_manifest(self):
        deploy_landing.deploy(*self.upload("c" * 40, 3), base=self.root, health_url=self.url)
        deploy_landing.rollback(base=self.root, health_url=self.url)
        self.assertEqual(self.current(), "bootstrap")

    def test_failed_health_check_keeps_previous_release(self):
        release_id, checksum = self.upload("d" * 40, 4)
        with self.assertRaises(Exception):
            deploy_landing.deploy(release_id, checksum, base=self.root, health_url="http://127.0.0.1:9")
        self.assertEqual(self.current(), "bootstrap")

    def test_tampered_release_is_rejected(self):
        release_id, checksum = self.upload("e" * 40, 5, tamper=True)
        with self.assertRaises(ValueError):
            deploy_landing.deploy(release_id, checksum, base=self.root, health_url=self.url)
        self.assertEqual(self.current(), "bootstrap")

    def test_old_releases_are_pruned(self):
        for run in range(1, 9):
            deploy_landing.deploy(*self.upload(f"{run:x}" * 40, run), base=self.root, health_url=self.url)
        releases = sorted(path.name for path in (self.root / "releases").iterdir())
        self.assertEqual(len(releases), deploy_landing.KEEP_RELEASES)
        self.assertIn(self.current(), releases)


if __name__ == "__main__":
    unittest.main()
