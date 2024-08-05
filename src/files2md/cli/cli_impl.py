import argparse
import os
import sys
from pathlib import Path
from typing import Iterable

import pathspec

from files2md import fileinfo, md_transform
from files2md.cli import cli_args, msg
import files2md.cli.gitutil as gitutil


def collect_paths_git(
    args: cli_args.Args, patterns: list[str]
) -> tuple[list[Path], list[str]]:
    all_paths: list[Path] = gitutil.git_lsfiles_dirs(args.in_dirs)
    pathspec_obj = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    all_paths = [p for p in all_paths if pathspec_obj.match_file(p)]
    return all_paths, patterns


def collect_paths(args: cli_args.Args) -> tuple[list[Path], list[str]]:

    use_default_patterns: bool = args.use_default_patterns
    include_patterns: list[str] = args.glob_patterns
    exclude_patterns: list[str] = args.exclude_patterns

    patterns = [f"**"]
    if use_default_patterns:
        patterns.extend(fileinfo.DEFAULT_PATTERNS)
    exclude_patterns = [f"!{pattern}" for pattern in exclude_patterns]
    patterns.extend(exclude_patterns)
    patterns.extend(include_patterns)

    if args.git_ls_files:
        return collect_paths_git(args, patterns)

    all_paths: list[Path] = []
    for in_dir in args.in_dirs:
        spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        specced = [in_dir.joinpath(x) for x in spec.match_tree(in_dir)]
        all_paths.extend(specced)
    return all_paths, patterns


def file_sizes_and_names(summary: md_transform.TransformSummary) -> Iterable[str]:
    lst = summary.included_files
    sizes = summary.files_to_char_count
    for item in sorted(lst, key=lambda x: sizes[x]):
        flags = "x" if item in summary.content_excluded_files else " "
        flags += "t" if item in summary.truncated_files else " "
        size = sizes.get(item, -1)
        yield f"{flags} {size:12,} chars: {item}"


def main(argv: list[str] = sys.argv[1:]):
    args = cli_args.parse(argv)
    files, applied_patterns = collect_paths(args)
    project_name = (
        ", ".join(d.name for d in args.in_dirs) or "No directories specified."
    )

    if not args.split:
        transform = main_singlefile_output(args, files, project_name)
    else:
        transform = main_splitfile_output(args, files, project_name)

    output_file_size = args.out_file.stat().st_size
    with msg.VPrinter(args.verbosity) as vprint:
        summary = transform.summary
        vprint.section(2, "arguments", vars(args))
        vprint.section(3, "applied-patterns", applied_patterns)
        vprint.section(3, "file-count-by-suffix", summary.suffix_to_file_count)
        vprint.section(4, "files", file_sizes_and_names(summary), "\n")
        vprint.section(
            1,
            "summary",
            {
                "Number of files included": len(files),
                "Output file size": output_file_size,
                "Output file": args.out_file,
            },
        )


def main_splitfile_output(args: cli_args.Args, files: list[Path], project_name: str):
    initial_path = Path(args.out_file)
    output_handler = md_transform.SplitFileOutputHandler(
        initial_path=initial_path,
        kb_per_file=args.split,
        output_encoding=args.output_encoding,
    )
    transform = md_transform.MdWriter(
        project_name=project_name,
        in_dirs=args.in_dirs,
        files=files,
        output=output_handler,
        max_lines_per_file=args.max_lines_per_file,
        include_empty=args.include_empty,
        mlpf_approx_pct=args.mlpf_approx_pct,
        sub_rules_file=args.sub_rules_file,
    )
    transform.make_md()
    return transform


def main_singlefile_output(args: cli_args.Args, files: list[Path], project_name: str):
    with open(args.out_file, "w", encoding=args.output_encoding) as ofh:
        output_handler = md_transform.SingleFileOutputHandler(ofh)
        transform = md_transform.MdWriter(
            project_name=project_name,
            in_dirs=args.in_dirs,
            files=files,
            output=output_handler,
            max_lines_per_file=args.max_lines_per_file,
            include_empty=args.include_empty,
            mlpf_approx_pct=args.mlpf_approx_pct,
            sub_rules_file=args.sub_rules_file,
        )
        transform.make_md()
    return transform


if __name__ == "__main__":
    main()
