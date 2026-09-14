from contextlib import nullcontext
import os
from pathlib import Path
import stat

import pytest

from global_signal_plots.io import staged_outputs


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")


def _access(path):
    metadata = path.stat()
    return metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)


@pytest.fixture
def group_restricted_outputs(tmp_path):
    default_groups = {os.getegid(), tmp_path.stat().st_gid}
    groups = [gid for gid in os.getgroups() if gid not in default_groups]
    if not groups and os.geteuid() == 0:
        groups = [max(default_groups) + 1]
    if not groups:
        pytest.skip("requires permission to assign a different group")
    paths = [tmp_path / "out.tsv", tmp_path / "out.pdf"]
    owner = 1 if os.geteuid() == 0 else os.geteuid()
    for path in paths:
        path.write_bytes(b"prior product")
        os.chown(path, owner, groups[0])
        path.chmod(0o640)
    return paths


@pytest.mark.parametrize("modes", [(0o600, 0o600), (0o640, 0o600)])
def test_publication_preserves_permissions_before_either_replace(tmp_path, monkeypatch, modes):
    paths = [tmp_path / "out.tsv", tmp_path / "out.pdf"]
    for path, mode in zip(paths, modes):
        path.write_bytes(b"prior product")
        path.chmod(mode)
    replace = os.replace
    published = []

    def record_replace(source, target):
        if not published:
            assert [stat.S_IMODE(path.stat().st_mode) for path in staged] == list(modes)
        replace(source, target)
        published.append(target)

    monkeypatch.setattr(os, "replace", record_replace)
    previous_umask = os.umask(0o022)
    try:
        with staged_outputs(paths) as staged:
            for path in staged:
                path.write_bytes(b"new product")
                assert stat.S_IMODE(path.stat().st_mode) == 0o644
    finally:
        os.umask(previous_umask)

    assert published == paths
    assert [path.read_bytes() for path in paths] == [b"new product"] * 2
    assert [stat.S_IMODE(path.stat().st_mode) for path in paths] == list(modes)
    assert not list(tmp_path.glob(".gs-*"))


@pytest.mark.parametrize("failed_suffix", [".tsv", ".pdf"])
def test_permission_preservation_failure_prevents_all_publication(tmp_path, monkeypatch, failed_suffix):
    paths = [tmp_path / "out.tsv", tmp_path / "out.pdf"]
    for path in paths:
        path.write_bytes(b"prior product")
        path.chmod(0o600)
    chmod, replace = os.chmod, os.replace
    published = []

    def fail_chmod(path, mode, *args, **kwargs):
        if Path(path).name == f"new{failed_suffix}":
            raise PermissionError("injected permission preservation failure")
        return chmod(path, mode, *args, **kwargs)

    def record_replace(source, target):
        published.append(target)
        return replace(source, target)

    monkeypatch.setattr(os, "chmod", fail_chmod)
    monkeypatch.setattr(os, "replace", record_replace)
    with pytest.raises(PermissionError, match="injected permission preservation failure"):
        with staged_outputs(paths) as staged:
            for path in staged:
                path.write_bytes(b"new product")

    assert published == []
    assert [path.read_bytes() for path in paths] == [b"prior product"] * 2
    assert [stat.S_IMODE(path.stat().st_mode) for path in paths] == [0o600] * 2
    assert not list(tmp_path.glob(".gs-*"))


@pytest.mark.parametrize("rollback", [False, True])
def test_publication_and_rollback_preserve_ownership(
    tmp_path, monkeypatch, group_restricted_outputs, rollback
):
    paths = group_restricted_outputs
    before = {path: _access(path) for path in paths}
    replace = os.replace

    def replace_or_fail(source, target):
        assert _access(source) == before[target]
        if rollback and target == paths[1]:
            raise OSError("injected publication failure")
        return replace(source, target)

    monkeypatch.setattr(os, "replace", replace_or_fail)
    outcome = (
        pytest.raises(OSError, match="injected publication failure")
        if rollback else nullcontext()
    )
    with outcome:
        with staged_outputs(paths) as staged:
            for path, target in zip(staged, paths):
                path.write_bytes(b"new product")
                assert path.stat().st_gid != before[target][1]

    expected_content = b"prior product" if rollback else b"new product"
    assert [path.read_bytes() for path in paths] == [expected_content] * 2
    assert {path: _access(path) for path in paths} == before
    assert not list(tmp_path.glob(".gs-*"))


@pytest.mark.parametrize(
    "failed_chown", [1, 2, 3, 4],
    ids=["backup-tsv", "backup-pdf", "staged-tsv", "staged-pdf"],
)
def test_ownership_preservation_failure_prevents_all_publication(
    tmp_path, monkeypatch, group_restricted_outputs, failed_chown
):
    paths = group_restricted_outputs
    before = {path: _access(path) for path in paths}
    chown, replace = os.chown, os.replace
    ownership_changes = 0
    published = []

    def fail_chown(path, uid, gid, *args, **kwargs):
        nonlocal ownership_changes
        ownership_changes += 1
        if ownership_changes == failed_chown:
            raise PermissionError("injected ownership preservation failure")
        return chown(path, uid, gid, *args, **kwargs)

    def record_replace(source, target):
        published.append(target)
        return replace(source, target)

    monkeypatch.setattr(os, "chown", fail_chown)
    monkeypatch.setattr(os, "replace", record_replace)
    with pytest.raises(PermissionError, match="injected ownership preservation failure"):
        with staged_outputs(paths) as staged:
            for path in staged:
                path.write_bytes(b"new product")

    assert published == []
    assert [path.read_bytes() for path in paths] == [b"prior product"] * 2
    assert {path: _access(path) for path in paths} == before
    assert not list(tmp_path.glob(".gs-*"))
