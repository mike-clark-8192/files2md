from pathlib import Path
import files2md.cli.gitutil as gitutil
from files2md.cli.gitutil import StrPath, StrPathIter
import os


def abs_paths(paths: list[str]) -> set[Path]:
    return {Path(p).absolute() for p in paths}


def assert_same_paths(a: StrPathIter, b: StrPathIter):
    sa = {os.path.abspath(p) for p in a}
    sb = {os.path.abspath(p) for p in b}
    assert sa == sb


def test_dir_find_dotgit_dirs(tmp_path):
    # Two repos at different depths, each marked by a .git directory.
    (tmp_path / "repoA" / ".git").mkdir(parents=True)
    (tmp_path / "repoB" / "sub" / ".git").mkdir(parents=True)

    # dir_find_dotgit_dirs returns the parent of each .git it finds.
    assert_same_paths(
        gitutil.dir_find_dotgit_dirs(tmp_path),
        [
            tmp_path / "repoA",
            tmp_path / "repoB" / "sub",
        ],
    )
