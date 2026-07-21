# Security handling

Keep this archive internal and non-executable. Do not execute source, open nested archives interactively, install dependencies, serve files, or render active content on a shared host. The read-only validator inspects ZIP central-directory metadata only and rejects traversal, absolute/drive-qualified, encrypted, symlink, and nested-archive entries; it does not certify payload safety.

Owner-approved extraction must use a fresh disposable directory outside this repository, a size/file-count quota, path-traversal-safe tooling, malware and secret scans, dependency/license review, and a new separately owned product boundary. Never overwrite existing paths or follow links. Delete the disposable copy after evidence capture.

There is no security support or patching commitment while the archive remains quarantined. Route suspected exposure or corruption to the future accountable owner, preserve hashes and access evidence, stop sharing, and assess credential rotation if any secret is discovered. Execution, redistribution, or publication requires prior documented ownership, permission, supported-version, patching, privacy, security, and release approval.
