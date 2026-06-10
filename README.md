# files2md

`files2md` is a Python library and CLI tool that converts a directory of files into a
single Markdown document. This tool could be useful for sharing project structures
and contents with others.

You might find it particularly useful as a way to share a project with an AI
Chat Assistant like ChatGPT, Google Gemini, or GitHub Copilot.

## Installation and basic usage

Currently, `files2md` does not support direct installation from PyPI. To use
the tool, either clone it and run it directly, or use pip's ability to
install directly from a Git repository.

### via pip or [pipx](https://pipx.pypa.io/stable/)
```sh
pip install git+https://github.com/mike-clark-8192/files2md.git
files2md InputDir -o OutputFile.md
```

### via git clone
```sh
git clone https://github.com/mike-clark-8192/files2md && cd files2md
python3 -m files2md.cli InputDir -o OutputFile.md
```

The output target is required: pass `-o/--out-file FILE`, or `-O` to auto-name it.

## Features

- Recursive directory traversal of one or more input directories.
- Converts file contents to Markdown code blocks with a language hint based on
  file extension.
- A layered, gitignore-style include/exclude model built on
  [pathspec](https://github.com/cpburnz/python-pathspec) — see
  **[PATTERNS.md](PATTERNS.md)**.
- Detects file encodings and converts to UTF-8.
- Detects and excludes binary files (content excluded; file still listed).
- Built-in exclude sets for binaries, VCS internals, caches/build output, and
  noisy files (lockfiles, minified bundles, logs, …).
- **Always excludes sensitive files** (`.env`, `*.pem`, `id_rsa`, …) — even
  under a broad `--glob '**'` — unless you pass `--include-sensitive`.
- Optionally honor a repo's `.gitignore` by listing files via
  `git ls-files` (`-t/--git-ls-files`).
- Optional per-file line caps (`-l`) and output splitting (`-p`).

## Choosing what gets included

Selection is a single ordered list of patterns with **last-match-wins**
semantics. Polarity is inverted from a raw `.gitignore` (same as ripgrep's
`-g`): a bare pattern **includes**, `!PAT` **excludes**.

The list is assembled in four layers; lower layers override higher ones:

| Layer | Source | Role |
|------:|--------|------|
| 0 | `--baseline all\|known\|none` | the starting set |
| 1 | built-in everyday excludes | binary / vcs / generated / noisy |
| 2 | `-g` / `--glob` | **your** patterns — override layers 0 and 1 |
| 3 | sensitive excludes | secrets — override-proof (`--include-sensitive` to lift) |

```sh
# Everything except junk; secrets stay out. (the default)
files2md ./project -o out.md

# Only known source types, plus one extra extension.
files2md ./project --baseline known -g '*.weirdext' -o out.md

# Full manual control: nothing unless you name it.
files2md ./project --baseline none -g 'src/**' '!**/test_*.py' -o out.md
```

See **[PATTERNS.md](PATTERNS.md)** for the full model and more examples.

To inspect exactly what a pattern set selects (and how big each piece is)
without combing through the generated document, add `-1/--first-pass FILE` to
also emit a JSON manifest of the selected files with their line ranges and
sizes.

## Splitting large output

`-p/--split KB` writes the document across multiple parts of roughly `KB`
kilobytes each, named `<stem>-1<suffix>`, `<stem>-2<suffix>`, … next to your
`-o` path (each part is self-contained, with its own per-part table of
contents). Use `-d/--out-dir DIR` to collect the parts in a dedicated
directory:

```sh
files2md ./project -o project.md -p 200 -d ./dump
# -> ./dump/project-1.md, ./dump/project-2.md, ...
```

## Wishlist / TODOs

* Add support for direct installation via PyPI.
* Per-set opt-in/opt-out by name (e.g. `--no-set binary,noisy`).
* Improve handling of large files (further truncation options).
* Add something like `--continue-on-read-error`.

## Full usage (`--help`)

```
usage: files2md [-h] [-d OUT_DIR] (-o OUT_FILE | -O)
                [--baseline {all,known,none}] [-g GLOB [GLOB ...]]
                [--include-sensitive] [-B GLOB [GLOB ...]] [-l N]
                [--mlpf-approx-pct N] [--include-empty]
                [--default-patterns | --no-default-patterns]
                [--output-encoding ENCODING] [-v N]
                [-f | --force | --no-force] [--output-extension EXT]
                [-1 FILE] [-t | --git-ls-files | --no-git-ls-files] [-p KB]
                [-s FILE]
                [DIR ...]

Convert file structure to markdown.

positional arguments:
  DIR                   Specify one or more input directories. (default: None)

options:
  -h, --help            show this help message and exit
  -d, --out-dir DIR     Directory to write output into; the filename comes
                        from -o / -O. Overrides the directory part of -o.
                        Useful with --split. (default: None)
  -o, --out-file OUT_FILE
                        Output file. (default: None)
  -O, --autoname-output
                        Automatically name the output file. (default: False)
  --baseline {all,known,none}
                        Starting set before patterns are applied: 'all' =
                        include everything (**); 'known' = include only
                        recognised source/text file types; 'none' = start
                        empty and rely on --glob. (default: all)
  -g, --glob GLOB [GLOB ...]
                        Your include/exclude patterns, applied after the
                        built-in sets so they take precedence. Gitignore-style
                        but inverted (same as ripgrep -g): 'PAT' includes,
                        '!PAT' excludes. Repeatable; order is preserved.
                        (default: [])
  --include-sensitive   Include sensitive files (.env, *.pem, id_rsa, ...)
                        that are otherwise always excluded last -- even by
                        --glob '**'. (default: False)
  -B, --binary-patterns GLOB [GLOB ...]
                        Wildmatch patterns to match binary files. These files
                        will be included in the output but without their
                        content. (default: [])
  -l, --max-lines-per-file N
                        Maximum number of lines to read from each file. 0 = no
                        limit. (default: 0)
  --mlpf-approx-pct N   Read N% extra lines if doing so would avoid truncation
                        of a file. (default: 25)
  --include-empty       Include empty files in the output. (default: False)
  --default-patterns, --no-default-patterns
                        Apply the built-in everyday exclude sets (binary, vcs,
                        generated, noisy). Disable with --no-default-patterns.
                        Sensitive-file exclusion is separate and stays on
                        regardless (see --include-sensitive). (default: True)
  --output-encoding ENCODING
                        Output file encoding. (default: utf-8)
  -v, --verbose N       Verbosity level; higher shows more (1 = summary only,
                        0 = silent). (default: 5)
  -f, --force, --no-force
                        Force overwrite output file(s). (default: False)
  --output-extension EXT
                        Output file extension. (default: txt)
  -1, --first-pass FILE
                        Also write a JSON manifest of the selected files
                        (paths, line ranges, sizes) to FILE -- a dry-run view
                        for tuning --baseline/--glob. (default: None)
  -t, --git-ls-files, --no-git-ls-files
                        Use 'git ls-files' to list files in input directories.
                        (default: False)
  -p, --split KB        Split output into multiple files of [approximate] size
                        `KB` kilobytes each. (default: 0)
  -s, --sub-rules-file FILE
                        Specify a file containing text substitution rules.
                        (default: None)
```

## License

MIT
