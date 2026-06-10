import dataclasses
import json
import sys
from pathlib import Path
from typing import Iterable

import pathspec

import files2md
from files2md import fileinfo, md_transform
from files2md.cli import cli_args, msg
import files2md.cli.gitutil as gitutil


def build_pattern_chain(args: cli_args.Args) -> list[str]:
    """Assemble the ordered gitwildmatch pattern list (last match wins).

    Layers, top to bottom:
      0. baseline           -- ** / known-good includes / nothing
      1. everyday excludes  -- binary, vcs, generated, noisy (unless --no-default-patterns)
      2. user --glob        -- include/exclude, order preserved, user has precedence
      3. sensitive excludes -- the last word, unless --include-sensitive
    """
    patterns: list[str] = []

    # Layer 0: baseline
    if args.baseline == "all":
        patterns.append("**")
    elif args.baseline == "known":
        patterns.extend(fileinfo.KNOWN_GOOD_INCLUDES)
    # "none": start empty, rely entirely on --glob

    # Layer 1: everyday exclude sets
    if args.default_patterns:
        for set_name in fileinfo.EVERYDAY_EXCLUDE_SET_ORDER:
            patterns.extend(f"!{p}" for p in fileinfo.EVERYDAY_EXCLUDE_SETS[set_name])

    # Layer 2: user patterns (already gitignore-style; '!' = exclude)
    patterns.extend(args.glob_patterns)

    # Layer 3: sensitive files always have the last word, unless opted in
    if not args.include_sensitive:
        patterns.extend(f"!{p}" for p in fileinfo.SENSITIVE_EXCLUDES)

    return patterns


def collect_paths_git(
    args: cli_args.Args, patterns: list[str]
) -> tuple[list[Path], list[str]]:
    all_paths: list[Path] = gitutil.git_lsfiles_dirs(args.in_dirs)
    pathspec_obj = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    all_paths = [p for p in all_paths if pathspec_obj.match_file(p)]
    return all_paths, patterns


def collect_paths(args: cli_args.Args) -> tuple[list[Path], list[str]]:
    patterns = build_pattern_chain(args)

    if args.git_ls_files:
        return collect_paths_git(args, patterns)

    spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
    all_paths: list[Path] = []
    for in_dir in args.in_dirs:
        all_paths.extend(in_dir.joinpath(x) for x in spec.match_tree(in_dir))
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
    # Reconfigure stdout/stderr to use UTF-8 encoding to avoid encoding errors on Windows
    # when outputting Unicode characters (especially when output is redirected/piped)
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    args = cli_args.parse(argv)
    files, applied_patterns = collect_paths(args)
    project_name = (
        ", ".join(d.name for d in args.in_dirs) or "No directories specified."
    )

    if not args.split:
        transform = main_singlefile_output(args, files, project_name)
        output_file_paths = [args.out_file]
        output_file_size = args.out_file.stat().st_size
    else:
        transform = main_splitfile_output(args, files, project_name)
        output_file_paths = transform.output_handler.get_filepaths()
        output_file_size = sum(p.stat().st_size for p in output_file_paths)

    if args.first_pass:
        write_first_pass_manifest(
            args.first_pass, args, transform, applied_patterns, output_file_paths
        )

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
                "Output files": output_file_paths if args.split else args.out_file,
                **(
                    {"First-pass manifest": args.first_pass}
                    if args.first_pass
                    else {}
                ),
            },
        )


def write_first_pass_manifest(
    path: Path,
    args: cli_args.Args,
    transform: md_transform.MdWriter,
    applied_patterns: list[str],
    output_file_paths: list[Path],
) -> None:
    """Write the pass-1 metadata as a JSON manifest.

    A dry-run-style record of exactly what the current pattern set selected and
    how large each piece is -- handy for tuning --baseline/--glob without
    re-reading the generated document.
    """
    manifest = {
        "files2md_version": files2md.__version__,
        "project_name": transform.project_name,
        "in_dirs": [str(d) for d in args.in_dirs],
        "baseline": args.baseline,
        "include_sensitive": args.include_sensitive,
        "split_kb": args.split,
        "applied_patterns": applied_patterns,
        "output_files": [str(p) for p in output_file_paths],
        "file_count": len(transform.first_pass_entries),
        "total_chars": sum(e.chars for e in transform.first_pass_entries),
        "suffix_counts": transform.summary.suffix_to_file_count,
        "files": [dataclasses.asdict(e) for e in transform.first_pass_entries],
    }
    with open(path, "w", encoding=args.output_encoding) as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")


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
        binary_patterns=args.binary_patterns,
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
            binary_patterns=args.binary_patterns,
        )
        transform.make_md()
    return transform


if __name__ == "__main__":
    main()
