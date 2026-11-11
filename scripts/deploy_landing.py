"""Deploy or roll back the Astro landing on the VPS.

Runs on the server as `python3 - <deploy|rollback> ...` (script read from stdin).
The release tree (/var/www/barbersoftly-releases/landing) is created once by an
administrator; this script never creates or changes production permissions.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import uuid

APPLICATION = "landing"
DOMAIN = "barbersoftly.com"
DEFAULT_ROOT = "/var/www/barbersoftly-releases/landing"
KEEP_RELEASES = 5
RELEASE_ID = re.compile(r"[a-f0-9]{40}-[0-9]+-[0-9]+")
RELEASE_META = re.compile(r'<meta name="barbersoftly-release" content="([a-f0-9]{40})"')


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def child(root, name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Release path escapes its directory")
    return root.joinpath(*path.parts)


def manifest(release, revision=None):
    data = json.loads((release / "deployment.json").read_text())
    if data.get("application") != APPLICATION or (revision and data.get("revision") != revision):
        raise ValueError("Release identity mismatch")
    declared = [item["path"] for item in data.get("files", [])]
    if "index.html" not in declared or len(set(declared)) != len(declared):
        raise ValueError("Release manifest is incomplete")
    for item in data["files"]:
        path = child(release, item["path"])
        if path.is_symlink() or not path.is_file() or digest(path) != item["sha256"]:
            raise ValueError("Release file integrity mismatch: " + item["path"])
    return data


def revision_of(release):
    """Revision of a release, or None for the pre-automation bootstrap copy."""
    if not (release / "deployment.json").is_file():
        return None
    return manifest(release)["revision"]


def replace_link(link, target):
    if link.exists() and not link.is_symlink():
        raise ValueError("Refusing to replace a real directory")
    temporary = link.with_name(link.name + ".next-" + uuid.uuid4().hex)
    temporary.symlink_to(target)
    os.replace(temporary, link)


def target_root(base):
    root = Path(base).resolve()
    configuration = json.loads((root / ".deployment-target.json").read_text())
    if configuration.get("application") != APPLICATION:
        raise ValueError("Deployment target is not initialized")
    return root


def release_target(root, link):
    if not link.is_symlink():
        raise ValueError("Missing deployment symlink: " + link.name)
    target = link.resolve(strict=True)
    if target.parent != (root / "releases").resolve() or not target.is_dir():
        raise ValueError("Deployment symlink escapes its release directory")
    return target


def check_served(revision, override=None):
    """Fetch "/" from this origin and confirm the expected release is served."""
    url = override or "https://" + DOMAIN
    command = ["curl", "--fail", "--silent", "--show-error", "--max-time", "10"]
    if not override:
        command += ["--resolve", DOMAIN + ":443:127.0.0.1"]
    command.append(url.rstrip("/") + "/?release-check")
    html = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    match = RELEASE_META.search(html)
    if revision and (not match or match.group(1) != revision):
        raise ValueError("Served landing does not match release " + revision)


def unpack(archive, destination):
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        for member in members:
            child(destination, member.name)
            if not (member.isfile() or member.isdir()):
                raise ValueError("Archive contains links or unsupported entries")
        for member in members:
            path = child(destination, member.name)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
                path.chmod(0o755)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, path.open("wb") as output:
                    shutil.copyfileobj(source, output)
                path.chmod(0o644)


def prune(root):
    """Keep the newest releases plus whatever current/previous point to."""
    keep = {release_target(root, root / "current"), release_target(root, root / "previous")}
    candidates = sorted(
        (path for path in (root / "releases").iterdir() if path.is_dir() and not path.is_symlink()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for path in candidates[KEEP_RELEASES:]:
        if path.resolve() not in keep:
            shutil.rmtree(path)


def deploy(release_id, expected_digest, base=DEFAULT_ROOT, health_url=None):
    if not RELEASE_ID.fullmatch(release_id or "") or not re.fullmatch(r"[a-f0-9]{64}", expected_digest or ""):
        raise ValueError("Invalid release identifier or checksum")
    root = target_root(base)
    with (root / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        previous = release_target(root, root / "current")
        archive = root / "uploads" / (release_id + ".tar.gz")
        if digest(archive) != expected_digest:
            raise ValueError("Archive checksum mismatch")
        release = root / "releases" / release_id
        release.mkdir()  # A previous or failed release is never overwritten.
        unpack(archive, release)
        revision = manifest(release, release_id[:40])["revision"]
        replace_link(root / "current", release)
        try:
            check_served(revision, health_url)
        except Exception:
            replace_link(root / "current", previous)
            raise
        replace_link(root / "previous", previous)
        archive.unlink()
        prune(root)
        print("Activated landing " + revision)


def rollback(base=DEFAULT_ROOT, health_url=None):
    root = target_root(base)
    with (root / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = release_target(root, root / "current")
        previous = release_target(root, root / "previous")
        if current == previous:
            raise ValueError("There is no previous release to restore")
        revision = revision_of(previous)
        replace_link(root / "current", previous)
        try:
            check_served(revision, health_url)
        except Exception:
            replace_link(root / "current", current)
            raise
        replace_link(root / "previous", current)
        print("Restored landing " + (revision or previous.name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["deploy", "rollback"])
    parser.add_argument("--release")
    parser.add_argument("--sha256")
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--health-url")
    args = parser.parse_args()
    if args.operation == "deploy":
        deploy(args.release, args.sha256, args.root, args.health_url)
    else:
        rollback(args.root, args.health_url)


if __name__ == "__main__":
    main()
