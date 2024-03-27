import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

import pathspec

from .. import fileinfo, md_transform
from . import arg, msg


def collect_paths(
    use_default_patterns: bool,
    include_patterns: list[str] = [],
    exclude_patterns: list[str] = [],
) -> tuple[list[Path], list[str]]:
    patterns = [f"**"]
    if use_default_patterns:
        patterns.extend(fileinfo.DEFAULT_PATTERNS)
    exclude_patterns = [f"!{pattern}" for pattern in exclude_patterns]
    patterns.extend(exclude_patterns)
    patterns.extend(include_patterns)
    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    return [Path(x) for x in spec.match_tree(".")], patterns


def file_sizes_and_names(lst: Iterable[Path]):
    for item in sorted(lst, key=lambda x: x.stat().st_size):
        yield f"{item.stat().st_size:10,} {item}"


def main(argv: list[str] = sys.argv[1:]):
    args = arg.parse(argv)
    os.chdir(args.in_dir)
    files, applied_patterns = collect_paths(
        args.use_default_patterns, args.glob_patterns, args.exclude_patterns
    )
    project_name = args.in_dir.name

    with open(args.out_file, "w", encoding=args.output_encoding) as ofh:
        mdtr = md_transform.MdTransform(
            max_lines_per_file=args.max_lines_per_file,
            include_empty=args.include_empty,
            mlpf_approx_pct=args.mlpf_approx_pct,
        )
        mdtr.make_md(project_name, args.in_dir, files, ofh)

    output_file_size = args.out_file.stat().st_size
    with msg.VPrinter(args.verbosity) as vprint:
        summary = mdtr.summary
        vprint.section(2, "arguments", vars(args))
        vprint.section(3, "applied-patterns", applied_patterns)
        vprint.section(3, "file-count-by-suffix", summary.suffix_to_file_count)
        vprint.section(4, "files", file_sizes_and_names(summary.included_files), "\n")
        vprint.section(
            1,
            "summary",
            {
                "Number of files included": len(files),
                "Output file size": output_file_size,
                "Output file": args.out_file,
            },
        )


if __name__ == "__main__":
    main()
