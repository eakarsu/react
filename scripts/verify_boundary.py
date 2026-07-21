#!/usr/bin/env python3
"""Verify the immutable, non-executable course archive without extracting it."""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


class BoundaryError(RuntimeError):
    pass


REQUIRED_UNRESOLVED = {
    "accountable-owner",
    "primary-source-provenance",
    "license-permission",
    "supported-version",
    "security-patching-owner",
}
ALLOWED_NEW_FILES = {
    ".github/workflows/boundary.yml",
    "BOUNDARY.json",
    "PROVENANCE.md",
    "SECURITY.md",
    "_COMPLETENESS_REVIEW.md",
    "scripts/verify-boundary.sh",
    "scripts/verify_boundary.py",
    "tests/test_boundary.py",
}
ROOT_RUNTIME_FILES = {
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Dockerfile",
    "compose.yaml",
    "docker-compose.yml",
    "start.sh",
}
NESTED_ARCHIVE_SUFFIXES = (".zip", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".7z", ".rar")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BoundaryError(message)


def git(root: Path, *args: str, null: bool = False) -> str | bytes:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return result.stdout if null else result.stdout.decode("utf-8", "strict").strip()


def validate_boundary(data: dict) -> None:
    require(data.get("schemaVersion") == 1, "unsupported boundary schema")
    require(data.get("artifactType") == "course-material-archive", "wrong artifact type")
    require(data.get("disposition") == "retain-internal-quarantine", "archive must remain quarantined")
    require(data.get("deployableApplication") is False, "archive cannot become deployable")
    require(data.get("runtimeAcceptance") == "not_applicable", "runtime acceptance must remain N/A")
    require(data.get("loginAcceptance") == "not_applicable", "login acceptance must remain N/A")
    require(set(data.get("allowedOperations", [])) == {"inventory", "integrity-check", "owner-approved-extraction"}, "allowed operations changed")
    require({"deploy", "publish", "redistribute", "execute-in-place"}.issubset(data.get("prohibitedOperations", [])), "prohibited operations weakened")
    require(REQUIRED_UNRESOLVED.issubset(data.get("unresolved", [])), "unresolved governance gate removed")
    require(data.get("updateStrategy") == "immutable-until-owner-approved-replacement", "unsafe update strategy")


def safe_archive_member(name: str, external_attr: int, flag_bits: int) -> None:
    normalized = name.replace("\\", "/")
    parts = PurePosixPath(normalized)
    require(not parts.is_absolute(), f"absolute archive member: {name}")
    require(".." not in parts.parts, f"traversal archive member: {name}")
    require(not (len(normalized) >= 2 and normalized[1] == ":"), f"drive-qualified archive member: {name}")
    require(not flag_bits & 1, f"encrypted archive member: {name}")
    mode = (external_attr >> 16) & 0o170000
    require(mode != stat.S_IFLNK, f"symlink archive member: {name}")
    require(not normalized.lower().endswith(NESTED_ARCHIVE_SUFFIXES), f"nested archive member: {name}")


def baseline_entries(root: Path, commit: str) -> list[tuple[str, str, str, int]]:
    raw = git(root, "ls-tree", "-r", "-z", "-l", commit, null=True)
    entries = []
    for row in raw.split(b"\0"):
        if not row:
            continue
        metadata, encoded_path = row.split(b"\t", 1)
        mode, object_type, object_id, size = metadata.decode("ascii").split()
        path = encoded_path.decode("utf-8", "surrogateescape")
        entries.append((mode, object_type, object_id, int(size)))
        entries[-1] = (path, mode, object_id, int(size))
    return entries


def verify(root: Path) -> dict[str, int]:
    root = root.resolve()
    boundary_path = root / "BOUNDARY.json"
    require(boundary_path.is_file(), "BOUNDARY.json missing")
    data = json.loads(boundary_path.read_text(encoding="utf-8"))
    validate_boundary(data)
    baseline = data["baseline"]

    require(Path(git(root, "rev-parse", "--show-toplevel")).resolve() == root, "validator must run in the archive repository")
    commit = baseline["sourceCommit"]
    require(git(root, "rev-parse", f"{commit}^{{tree}}") == baseline["sourceTree"], "pinned source tree mismatch")
    entries = baseline_entries(root, commit)
    require(len(entries) == baseline["trackedFiles"], "baseline file count mismatch")
    require(sum(item[3] for item in entries) == baseline["trackedBytes"], "baseline byte count mismatch")

    protected = [item for item in entries if item[0] != "README.md"]
    require(len(protected) == baseline["protectedPayloadFiles"], "protected file count mismatch")
    require(sum(item[3] for item in protected) == baseline["protectedPayloadBytes"], "protected byte count mismatch")
    for relative, mode, expected_blob, _size in protected:
        require(mode == "100644", f"unsupported baseline mode for {relative}: {mode}")
        path = root / relative
        require(path.is_file() and not path.is_symlink(), f"protected payload missing or non-regular: {relative}")
        require(git(root, "hash-object", "--", relative) == expected_blob, f"protected payload changed: {relative}")

    modified = set(filter(None, git(root, "diff", "--name-only", commit, "--").splitlines()))
    require(modified <= {"README.md"}, f"tracked payload drift: {sorted(modified - {'README.md'})}")
    untracked_raw = git(root, "ls-files", "--others", "--exclude-standard", "-z", null=True)
    untracked = {row.decode("utf-8", "surrogateescape") for row in untracked_raw.split(b"\0") if row}
    require(untracked <= ALLOWED_NEW_FILES, f"unexpected untracked material: {sorted(untracked - ALLOWED_NEW_FILES)}")

    for path in root.rglob("*"):
        if ".git" in path.relative_to(root).parts:
            continue
        require(not path.is_symlink(), f"symlink prohibited in archive boundary: {path.relative_to(root)}")
    for filename in ROOT_RUNTIME_FILES:
        require(not (root / filename).exists(), f"root runtime/deployment file prohibited: {filename}")

    archives = sorted(root / item[0] for item in protected if item[0].lower().endswith(".zip"))
    stats = {"zipArchives": len(archives), "zipEntries": 0, "zipCompressedBytes": 0, "zipDeclaredUncompressedBytes": 0}
    for archive in archives:
        try:
            with zipfile.ZipFile(archive) as opened:
                for member in opened.infolist():
                    safe_archive_member(member.filename, member.external_attr, member.flag_bits)
                    stats["zipEntries"] += 1
                    stats["zipCompressedBytes"] += member.compress_size
                    stats["zipDeclaredUncompressedBytes"] += member.file_size
        except zipfile.BadZipFile as error:
            raise BoundaryError(f"invalid ZIP central directory: {archive.relative_to(root)}") from error
    for key, actual in stats.items():
        require(actual == baseline[key], f"archive inventory mismatch for {key}: {actual}")

    required_docs = {
        "README.md": ("NOT_APPLICABLE", "retain-internal-quarantine"),
        "PROVENANCE.md": (commit, "Unknown"),
        "SECURITY.md": ("disposable", "Do not execute"),
    }
    for filename, phrases in required_docs.items():
        content = (root / filename).read_text(encoding="utf-8")
        for phrase in phrases:
            require(phrase in content, f"{filename} is missing required boundary phrase: {phrase}")
    review = (root / "_COMPLETENESS_REVIEW.md").read_text(encoding="utf-8")
    require(review.count("## Implementation progress (2026-07-20)") == 1, "implementation heading must occur exactly once")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        stats = verify(args.root)
    except (BoundaryError, KeyError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        print(f"archive boundary verification failed: {error}", file=sys.stderr)
        return 1
    print(
        "react archive boundary verified: "
        f"{stats['zipArchives']} ZIPs/{stats['zipEntries']} central-directory entries; "
        "deployment, execution, and login remain not applicable"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
