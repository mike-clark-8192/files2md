import argparse
from pathlib import Path
import typing
import types


class Args:
    in_dir: Path
    out_file: Path
    glob_patterns: list[str]
    exclude_patterns: list[str]
    use_default_patterns: bool
    verbosity: int
    max_lines_per_file: int
    output_encoding: str
    include_empty: bool
    mlpf_approx_pct: int
    autoname_output: bool
    force: bool

    def __setattr__(self, name: str, value: typing.Any) -> None:
        import typing

        hints = typing.get_type_hints(self)
        if name not in hints:
            raise ValueError(f"{name} is not a declared attribute of {type(self)}")
        decltype = hints[name]
        if isinstance(decltype, types.GenericAlias):
            decltype = decltype.__origin__
        valtype = type(value)
        if value is not None and not issubclass(valtype, decltype):
            raise ValueError(
                f"Declared type '{decltype.__name__}' of attribute '{name}'"
                f" is incompatible with value type '{valtype.__name__}', value={value}"
            )
        super().__setattr__(name, value)


def parse(argv: list[str]) -> Args:
    parser = argparse.ArgumentParser(
        description="Convert file structure to markdown.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "in_dir",
        type=type_existing_directory,
        help="Input directory.",
    )
    parser.add_argument(
        "out_file",
        type=Path,
        nargs="?",
        help="Output markdown file.",
    )
    parser.add_argument(
        "-g",
        "--glob-patterns",
        type=str,
        nargs="+",
        default=[],
        metavar="GLOB",
        help="Wildmatch patterns to include files and directories.",
    )
    parser.add_argument(
        "-x",
        "--exclude-patterns",
        type=str,
        nargs="+",
        default=[],
        metavar="GLOB",
        help="Wildmatch patterns to exclude files and directories.",
    )
    parser.add_argument(
        "-l",
        "--max-lines-per-file",
        type=int,
        default=0,
        metavar="N",
        help="Maximum number of lines to read from each file. 0 = no limit.",
    )
    parser.add_argument(
        "--mlpf-approx-pct",
        type=int,
        default=25,
        metavar="N",
        help="Read N%% extra lines if doing so would avoid truncation of a file.",
    )
    parser.add_argument(
        "--include-empty",
        action="store_true",
        default=False,
        help="Include empty files in the output.",
    )
    parser.add_argument(
        "-D",
        "--no-default-patterns",
        action="store_false",
        default=True,
        dest="use_default_patterns",
        help="Turn off built-in include/exclude patterns.",
    )
    parser.add_argument(
        "--output-encoding",
        type=str,
        default="utf-8",
        metavar="ENCODING",
        help="Output file encoding.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbosity",
        help="Increase verbosity. Repeat for more output.",
    )
    parser.add_argument(
        "-O",
        "--autoname-output",
        action="store_true",
        default=False,
        help="Automatically name the output file.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=False,
        help="Force overwrite output file(s).",
    )

    args: Args = parser.parse_args(argv, namespace=Args())
    args.in_dir = args.in_dir.absolute()
    if args.out_file is None:
        if not args.autoname_output:
            parser.error("required: -O or [out_file]")
        args.out_file = Path(f"{args.in_dir.name}.md").absolute()
    if not args.force and args.out_file.exists():
        parser.error(f"{args.out_file} exists. Use -f to overwrite.")
    args.out_file = args.out_file.absolute()
    return args


def type_existing_directory(path_str):
    path = Path(path_str)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"{path} is not a valid directory.")
    return path.absolute()


def type_overwritable_file(path_str):
    path = Path(path_str)
    if path.exists() and not path.is_file():
        raise argparse.ArgumentTypeError(f"{path} exists and is not a file.")
    return path.absolute()
