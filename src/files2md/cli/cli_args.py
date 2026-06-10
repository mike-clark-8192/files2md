import argparse
import os
import pathlib
from pathlib import Path
import typing
import types
import re


class Args:
    autoname_output: bool
    baseline: str
    binary_patterns: list[str]
    first_pass: pathlib.Path
    force: bool
    git_ls_files: bool
    glob_patterns: list[str]
    in_dirs: list[pathlib.Path]
    include_empty: bool
    include_sensitive: bool
    max_lines_per_file: int
    mlpf_approx_pct: int
    out_dir: pathlib.Path
    out_file: pathlib.Path
    output_encoding: str
    output_extension: str
    default_patterns: bool
    split: int
    sub_rules_file: str
    verbosity: int

def parse(argv: list[str]) -> Args:
    parser = build_argparser()

    args: Args = parser.parse_args(argv, namespace=Args())
    if not args.in_dirs:
        args.in_dirs = [Path.cwd()]
    args.in_dirs = [d.absolute() for d in args.in_dirs]
    if not args.in_dirs:
        args.in_dirs = [Path(os.getcwd())]
    if args.out_file is None:
        args = typing.cast(Args, args)
        if not args.autoname_output:
            parser.error("required: -O or [out_file]")
        ext = args.output_extension
        in_dir_names = "_".join(d.name for d in args.in_dirs)
        args.out_file = Path(f"{in_dir_names}_md.{ext}")
    if args.out_dir is not None:
        # --out-dir overrides the directory; the filename comes from -o / -O.
        args.out_file = args.out_dir / args.out_file.name
    args.out_file = args.out_file.absolute()
    if not args.force:
        existing = first_output_path(args.out_file, args.split)
        if existing.exists():
            parser.error(f"{existing} exists. Use -f to overwrite.")

    return args


def first_output_path(out_file: Path, split_kb: int) -> Path:
    """The first file actually written, for the overwrite guard.

    Single-file mode writes ``out_file`` itself. Split mode never writes that
    base name -- it writes ``<stem>-1<suffix>``, ``<stem>-2<suffix>``, ... -- so
    the first part is what we check.
    """
    if split_kb:
        return out_file.parent / f"{out_file.stem}-1{out_file.suffix}"
    return out_file


def build_argparser():
    parser = argparse.ArgumentParser(
        description="Convert file structure to markdown.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "in_dirs",
        nargs="*",
        type=ArgType.existing_dir,
        metavar="DIR",
        help="Specify one or more input directories.",
    )

    def add_output_options():
        parser.add_argument(
            "-d",
            "--out-dir",
            type=ArgType.existing_dir,
            metavar="DIR",
            help="Directory to write output into; the filename comes from "
            "-o / -O. Overrides the directory part of -o. Useful with --split.",
        )
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "-o",
            "--out-file",
            type=Path,
            help="Output file.",
        )
        group.add_argument(
            "-O",
            "--autoname-output",
            action="store_true",
            default=False,
            help="Automatically name the output file.",
        )

    add_output_options()

    parser.add_argument(
        "--baseline",
        choices=["all", "known", "none"],
        default="all",
        help="Starting set before patterns are applied: 'all' = include "
        "everything (**); 'known' = include only recognised source/text file "
        "types; 'none' = start empty and rely on --glob.",
    )
    parser.add_argument(
        "-g",
        "--glob",
        dest="glob_patterns",
        action="extend",
        nargs="+",
        default=[],
        metavar="GLOB",
        help="Your include/exclude patterns, applied after the built-in sets so "
        "they take precedence. Gitignore-style but inverted (same as ripgrep -g): "
        "'PAT' includes, '!PAT' excludes. Repeatable; order is preserved.",
    )
    parser.add_argument(
        "--include-sensitive",
        action="store_true",
        default=False,
        help="Include sensitive files (.env, *.pem, id_rsa, ...) that are "
        "otherwise always excluded last -- even by --glob '**'.",
    )
    parser.add_argument(
        "-B",
        "--binary-patterns",
        type=str,
        nargs="+",
        default=[],
        metavar="GLOB",
        help="Wildmatch patterns to match binary files. These files will be included in the output but without their content.",
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
        "--default-patterns",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply the built-in everyday exclude sets (binary, vcs, generated, "
        "noisy). Disable with --no-default-patterns. Sensitive-file exclusion is "
        "separate and stays on regardless (see --include-sensitive).",
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
        type=int,
        default=5,
        dest="verbosity",
        metavar="N",
        help="Verbosity level; higher shows more (1 = summary only, 0 = silent).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Force overwrite output file(s).",
    )
    parser.add_argument(
        "--output-extension",
        type=str,
        default="txt",
        metavar="EXT",
        help="Output file extension.",
    )
    parser.add_argument(
        "-1",
        "--first-pass",
        type=Path,
        metavar="FILE",
        help="Also write a JSON manifest of the selected files (paths, line "
        "ranges, sizes) to FILE -- a dry-run view for tuning --baseline/--glob.",
    )
    parser.add_argument(
        "-t",
        "--git-ls-files",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Use 'git ls-files' to list files in input directories.",
    )
    parser.add_argument(
        "-p",
        "--split",
        type=int,
        metavar="KB",
        default=0,
        help="Split output into multiple files of [approximate] size `KB` kilobytes each.",
    )
    parser.add_argument(
        "-s",
        "--sub-rules-file",
        type=str,
        metavar="FILE",
        help="Specify a file containing text substitution rules.",
    )
    return parser


class ArgType:
    @staticmethod
    def existing_dir(path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_dir():
            raise argparse.ArgumentTypeError(f"expected a directory: {path}")
        return path.absolute()

    @staticmethod
    def existing_file(path_str: str) -> Path:
        path = Path(path_str)
        if not path.is_file():
            raise argparse.ArgumentTypeError(f"expected a file: {path}")
        return path.absolute()

    @staticmethod
    def file_or_nonexistant(path_str: str) -> Path:
        path = Path(path_str)
        if path.exists() and not path.is_file():
            raise argparse.ArgumentTypeError(f"exists and is not a file: {path}")
        return path.absolute()

    @staticmethod
    def dir_or_nonexistant(path_str: str) -> Path:
        path = Path(path_str)
        if path.exists() and not path.is_dir():
            raise argparse.ArgumentTypeError(f"exists and is not a directory: {path}")
        return path.absolute()
