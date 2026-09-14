# GS1 correctness audit — 2026-09-13

Reviewed all six implementation modules and the original tests at
`5d92c335fc027d9c55f3a1281b223bfa67a1792c`: discovery/entity parsing, reduced
TSV identity, whole-FOV extraction, summary, plotting and CLI publication.
The scope is GS1 plus exact echo selection/row ambiguity; no study thresholds
or scientific defaults changed.

## Evidence and correction

The recovered audit's synthetic reproduction ran against this checkout before
editing. All its assertions passed, as did the original **11 tests**. A NaN
produced blank metric cells, 3D input became a one-volume scan, and 5D input
reported eight volumes while drawing two four-point traces. All-corrupt input
returned success with a header-only TSV and an unchanged old PDF; a missing
root returned success without a PDF. The echo-2 glob also selected echo 20,
creating identical subject/session/task/run rows. The added regression suite
initially had **39 failing cases**, confirming these gaps locally.

- `metrics.py` now requires nonempty 4D images, and nonempty finite 1D traces
  with finite summaries. A nonfinite voxel or an overflowing sum makes its
  volume's spatial mean nonfinite, so that one trace check rejects both.
- `scan.py` validates the root, matches the exact `_echo-2_` entity by default,
  and rejects every candidate in an ambiguous reduced-identity group. Warnings
  name the conflicting files, even if one copy is corrupt. A narrower `--glob`
  can select the intended acquisition/space/echo explicitly.
- Collection retains other usable files and logs `attempted`, `succeeded`,
  and `failed` counts. Attempted means distinct glob matches, including rejected
  ambiguous candidates; failed means candidates omitted from the output.
  No usable scan raises an error. This separates partial coverage from no QA.
- `cli.py` and `io.py` stage the requested products beside their destinations
  before replacement. A rendering/write error leaves prior products intact;
  a replacement error rolls back already replaced files. The CLI exits nonzero
  and identifies failure without claiming a new output set. `plot.py` propagates
  plot errors and closes figures, preventing a TSV from being paired with a
  supposedly successful PDF that silently omitted traces.
- Publication reproduces each prior product's owner, group, mode bits and POSIX
  access ACL on both its staged replacement and its rollback backup before any
  replacement, and publishes nothing when that fails. A rerun therefore cannot
  widen access to an existing restricted output: a staged file created under a
  permissive umask, or one whose copied mode bits would grant the group the read
  that an ACL mask denies, is corrected before it becomes the published file.

## Validation and limits

The suite collects **73 tests** and passes using `pytest -q -W error`, including
the original suite. Its runnable subset is platform-dependent: the 5 POSIX-ACL
cases skip on hosts whose `os` exposes no extended-attribute calls (Darwin) or
whose filesystem rejects `system.posix_acl_access`, and the 6 group-ownership
cases skip when the environment cannot assign a different group, leaving 62
cases everywhere. On the audited macOS host 68 pass and 5 skip.
Tests use generated NIfTIs and injected local plot/write/rename failures, with
fresh and pre-existing outputs. They cover NaN/±Inf, 3D/5D/zero dimensions,
summary/spatial overflow, missing/non-directory/empty roots, corrupt inputs,
partial/all-failed scans, exact echo matching, duplicate identities (including
one corrupt duplicate), glob deduplication, and TSV-only operation. Access
preservation is exercised with synthetic owner-only and group-restricted outputs
under a permissive umask, and with a synthetic ACL (`u::rw-,u:reader:r--,g::---,
m::r--,o::---`, mode 0640) asserting the published and rolled-back products keep
that ACL and grant the group class nothing; injected `chmod`, `chown` and
`setxattr` failures assert that neither product is replaced.
The installed CLI also passed clean and all-corrupt smoke checks: the latter
exited 1 with coverage/failure diagnostics and byte-identical prior TSV/PDF.
`uv build` produced both the source distribution and wheel successfully.

The known control includes zero background and yields exactly `[0,…,9]`;
plot x coordinates remain `0,…,9`, and the pre-trim marker remains at index 7.
Finite clean scans retain the original schema, summaries and numerical axes.

Local environment: Darwin ARM64, Python 3.11.15, NumPy 2.4.6, nibabel 5.4.2,
pandas 3.0.5, Matplotlib 3.11.2, pytest 9.1.1, resolved from this package's
manifest. This is not validation of the consuming pipeline's Linux lock or a
Sherlock run. No participant data, historical outputs, remote compute or live
SDK state was read or changed. These are conditional defects; their incidence
in research data remains unknown. Private audit bundles are not committed.

Access preservation covers owner, group, mode bits and the POSIX access ACL
(`system.posix_acl_access`) of the files being replaced. Other ACL flavors are
not reproduced: platforms whose `os` module exposes no extended-attribute calls
(such as Darwin) are treated as having mode bits only, so a macOS/NFSv4 ACL on a
prior output would be dropped. Directory default ACLs and SELinux labels are not
copied, and preservation is not attempted for destinations that do not yet exist
— a new output takes the umask and inherited ACL of its directory. A rerun whose
prior outputs the invoking user cannot `chown` or whose ACL it cannot set (a
product owned by another lab member, or a group the user has since left) now
fails with `Operation not permitted` and publishes nothing, where the earlier
in-place truncating write succeeded; recover by having the owner rerun or by
removing the stale products.

Replacement is atomic per file, not across the pair: serialize writers to the
same destinations. Process termination, power loss or concurrent readers during
publication can expose an intermediate pair. Normal caught publication failures
roll back; if the filesystem also prevents rollback, the error names retained
staging directories containing backups for recovery. No transaction framework
or crash-recovery daemon was added. Direct low-level writer calls do not gain
CLI staging; `write_metrics_tsv([])` remains a header-only serializer. A TSV-only
invocation publishes only its requested TSV and does not refresh any old PDF.
