# React course-material archive

This directory is a collection of course handouts, slides, exercises, sample source, and archived ZIP files. It is **not an independently supported application** and has no root dependency manifest, runtime, deployment target, authentication boundary, or login flow.

## Retention boundary

- Disposition: `retain-internal-quarantine` pending an accountable owner and provenance/license review.
- Allowed use: inventory, integrity checking, and owner-approved extraction into a separate project.
- Prohibited use: deployment, publication, redistribution, production dependency use, or presenting the materials as an original product.
- Runtime and login acceptance: `NOT_APPLICABLE`; individual exercises may be extracted only after their own manifest, license, acceptance criteria, tests, and security owner are established.

The archive contains nested ZIP files and macOS metadata. Treat every nested artifact as untrusted input: do not execute it in place, and scan/extract only into a disposable workspace.

See `BOUNDARY.json`, `PROVENANCE.md`, and `SECURITY.md` for the recorded decision and unresolved ownership requirements.

## Integrity evidence

The immutable source baseline is commit `33dfd033577b527056fe0a892fee57f6cf484ff5` / tree `a74e424ccf72d10d362e53bcd9de42cb03010d83`: 140 tracked files and 84,188,336 bytes. Except for this expanded README, all 139 original payload files are verified byte-for-byte against their Git blobs. The 74 ZIP central directories contain 1,593 entries; the validator rejects traversal, absolute/drive-qualified, encrypted, symlink, or nested-archive entries without extracting anything.

Run `sh scripts/verify-boundary.sh` and `python3 -B -m unittest discover -s tests -v` for the read-only policy checks. These checks prove integrity and quarantine only; they do not establish authorship, licensing, safety of execution, or product readiness.
