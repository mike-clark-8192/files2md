# files2md

`files2md` is a Python utility designed to convert a directory of files into a
single Markdown document. This tool could be useful for sharing project structures
and contents with others.

You might find it particularly useful as a way to share a project with an AI
Chat Assistant like ChatGPT, Google Gemini, or GitHub Copilot.

## Installation

Currently, `files2md` does not support direct installation from PyPI. To use
the tool, either clone it and run it directly, or use pip's ability to
install directly from a Git repository:

```sh
pip install git+https://github.com/mike-clark-8192/files2md.git
```

## Basic Usage

```sh
python3 -m files2md.cli [InputDirectory] [OutputFile.md]
```

## Features

- Recursive directory traversal.
- Converts file contents to Markdown code blocks with language hint based on file extension.
- Uses gitignore-style include/exclude [patterns](https://github.com/cpburnz/python-pathspec).
- Detects file encodings and converts to UTF-8.
- Detects and excludes binary files.
- Excludes common directories like `.git` and `node_modules`.
- Excludes files that often contain sensitive data (`.env` and `.envrc`). (!)   
  (!) If this is a concern, please review the output to ensure that no sensitive data is included.

## Wishlist / TODOs

* Add support for direct installation via PyPI.
* Add configuration options for including/excluding specific file types or directories.
* Improve handling of large files (e.g., truncation options).
* Add support for honoring `.gitignore` files.
* Warn about / detect potentially sensitive data.
* Add something like --continue-on-read-error

## Usage

```
Convert file structure to markdown.

positional arguments:
  in_dir                Input directory.
  out_file              Output markdown file.

options:
  -h, --help            show this help message and exit
  -g GLOB [GLOB ...], --glob-patterns GLOB [GLOB ...]
                        Wildmatch patterns to include files and directories. (default: [])
  -x GLOB [GLOB ...], --exclude-patterns GLOB [GLOB ...]
                        Wildmatch patterns to exclude files and directories. (default: [])
  -l N, --max-lines-per-file N
                        Maximum number of lines to read from each file. 0 = no limit. (default: 0)
  --mlpf-approx-pct N   Read N% extra lines if doing so would avoid truncation of a file. (default: 25)
  --include-empty       Include empty files in the output. (default: False)
  -D, --no-default-patterns
                        Turn off built-in include/exclude patterns. (default: True)
  --output-encoding ENCODING
                        Output file encoding. (default: utf-8)
  -v, --verbose         Increase verbosity. (default: 0)
```

## License

MIT
