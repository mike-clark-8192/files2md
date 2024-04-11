import subprocess
from pathlib import Path
from typing import Iterable

from pathspec.util import StrPath

StrPathIter = Iterable[StrPath]


def rglob_abs(root: StrPath, pattern: str) -> list[Path]:
    root = validate_dir_path(root)
    return [root.joinpath(p) for p in root.rglob(pattern)]


def dir_find_dotgit_dirs(search_dir: StrPath) -> list[Path]:
    search_dir = validate_dir_path(search_dir)
    dotgit_dirs: list[Path] = []
    for dotgit_paths in rglob_abs(search_dir, ".git"):
        dotgit_dirs.append(dotgit_paths.parent)
    return dotgit_dirs


def dirs_find_dotgit_dirs(search_dirs: StrPathIter) -> list[Path]:
    search_dirs = validate_paths(search_dirs)
    dotgit_dirs: list[Path] = []
    for search_dir in search_dirs:
        dotgit_dirs.extend(dir_find_dotgit_dirs(search_dir))
    return dotgit_dirs


def git_lsfiles_dirs(dirs: StrPathIter) -> list[Path]:
    dirs = validate_paths(dirs)
    dotgit_dirs = dirs_find_dotgit_dirs(dirs)
    all_results: list[Path] = []
    for dotgit_dir in dotgit_dirs:
        results = git_lsfiles_dir(dotgit_dir)
        all_results.extend(results)
    return all_results


def git_lsfiles_dir(root: StrPath) -> list[Path]:
    validate_dir_path(root)

    cached_paths = paths_from_git_cmd(
        [
            "git",
            "ls-files",
            "--exclude-standard",
            "--no-recurse-submodules",
            "--cached",
        ],
        root,
    )

    unversioned_paths = paths_from_git_cmd(
        [
            "git",
            "ls-files",
            "--exclude-standard",
            "--others",
        ],
        root,
    )

    deleted_paths = paths_from_git_cmd(
        [
            "git",
            "ls-files",
            "--exclude-standard",
            "--deleted",
        ],
        root,
    )

    existing_paths = (cached_paths | unversioned_paths) - deleted_paths

    return list(sorted(existing_paths))


def paths_from_git_cmd(cmd: list[str], root: StrPath) -> set[Path]:
    root = validate_dir_path(root)
    file_paths: set[Path] = set()
    output = subprocess.run(cmd, text=True, check=True, capture_output=True, cwd=root)
    for line in output.stdout.splitlines():
        qualified_path = root.joinpath(line)
        file_paths.add(qualified_path)
    return file_paths


def validate_paths(paths: StrPathIter) -> list[Path]:
    return [validate_dir_path(path) for path in paths]


def validate_dir_path(path: StrPath) -> Path:
    path = Path(path)
    if not path.is_absolute():
        msg = f"Path '{path}' must be an absolute path."
        raise ValueError(msg)
    if not path.is_dir():
        msg = f"Path '{path}' must be an existing directory."
        raise ValueError(msg)
    return path
