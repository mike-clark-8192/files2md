import argparse
from pathlib import Path
from . import transform
from .filespecs import ignore_files, ignore_dirs
import sys


class Args(argparse.Namespace):
    indir: Path
    outfile: Path


def parse_arguments(argv: list[str]) -> Args:
    def existing_directory(path_str):
        path = Path(path_str)
        if not path.is_dir():
            raise argparse.ArgumentTypeError(f"{path} is not a valid directory.")
        return path

    def overwritable_file(path_str):
        path = Path(path_str)
        if path.exists() and not path.is_file():
            raise argparse.ArgumentTypeError(f"{path} exists and is not a file.")
        return path

    parser = argparse.ArgumentParser(description="Convert files ")
    parser.add_argument(
        "indir",
        type=existing_directory,
        default=Path("."),
        nargs="?",
        help="Input directory.",
    )
    parser.add_argument(
        "outfile",
        type=overwritable_file,
        nargs="?",
        help="Output markdown file.",
        default=Path("[indir.name].md"),
    )
    args = parser.parse_args(argv, namespace=Args())
    if args.outfile is parser.get_default("outfile"):
        indir_name = args.indir.resolve().name
        args.outfile = Path(f"{indir_name}.md")
    return args


def try_remove_path_from_list(path: Path, list_: list[Path]) -> None:
    try:
        list_.remove(path)
    except ValueError:
        pass


def describe_path(path: Path, base: Path) -> str:
    relpath = path.resolve().relative_to(base.parent)
    return str(relpath.as_posix())


def filter_files(files: list[Path]):
    for file in files.copy():
        if file.name in ignore_files:
            try_remove_path_from_list(file, files)
        if any(parent.name in ignore_dirs for parent in file.parents):
            try_remove_path_from_list(file, files)


def main(argv=sys.argv[1:]):
    args = parse_arguments(argv)
    files: list[Path] = [x for x in args.indir.rglob("*") if not x.is_dir()]
    filter_files(files)
    base_path = args.indir.resolve()
    project_name = base_path.name
    path_descs = [describe_path(file, base_path) for file in files]

    with open(args.outfile, "w", encoding="utf8") as ofh:
        header = transform.make_header_md(project_name, path_descs)
        for file in files:
            pathdesc = describe_path(file, args.indir.resolve())
            mdstr = transform.file2md(file, pathdesc)
            ofh.write(mdstr)


if __name__ == "__main__":
    main()
