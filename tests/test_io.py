import os
from pathlib import Path
import stat

import pytest

from global_signal_plots.io import staged_outputs


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX file permissions")


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
