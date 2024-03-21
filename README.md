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

## Usage

To use `files2md`, navigate to the directory containing your project and run:

```sh
cd files2md
python3 -m files2md.cli [InputDirectory] [OutputMarkdownFile.md]
```

## Features

- Recursive directory traversal.
- Converts file contents to Markdown code blocks with syntax highlighting based on file extension.
- Excludes binary files and common directories like `.git` and `node_modules`.
- Detects file encodings and converts to UTF-8.
- Excludes files that often contain sensitive data (`.env` and `.envrc`). (!)
(!) If this is a concern, please review the output to ensure that no sensitive data is included.

## Wishlist / TODOs

* Add support for direct installation via PyPI.
* Add configuration options for including/excluding specific file types or directories.
* Improve handling of large files (e.g., truncation options).
* Add support for honoring `.gitignore` files.
* Warn about potentially sensitive data.

## License

MIT
