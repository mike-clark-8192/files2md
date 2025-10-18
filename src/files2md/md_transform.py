import io
import mimetypes
import re
from abc import ABC, abstractmethod
import contextlib
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from types import ModuleType
from typing import TYPE_CHECKING, Iterable, final, override
import typing

import pathspec

import files2md
import files2md.fileinfo as fileinfo

try:
    import charset_normalizer as charset_normalizer_

    charset_normalizer = charset_normalizer_
except ImportError:
    charset_normalizer = None  # type: ignore

TEMPLATE_PROJECT = Template("""# Project: ${project_name}""")

TEMPLATE_FILELIST = Template(
    """## File listing:
${files_listing}

## Filenames and content:
"""
)

TEMPLATE_FILE = Template(
    """
### `${pathname}`
${fence}${mdlang}
${content}
${fence}${omission_msg}

"""
)

TEMPLATE_BINARY_FILE = Template(
    """### `${pathname}`
(binary file detected, content excluded)
"""
)

TEMPLATE_MARKED_BINARY_FILE = Template(
    """
### `${pathname}`
(marked as binary file)

"""
)

TEMPLATE_UNSUPPORTED_MIMETYPE = Template(
    """### `${pathname}`
(content excluded due to unsupported MIME type: ${mimetype})
"""
)


TEMPLATE_OMISSION = Template(
    """
(NB: ${omitted_line_count} lines omitted for brevity)
"""
)

# In case someone wants to run files2md on files2md itself, we don't want to
# exclude files2md's own source code by noticing the tag in this source code.
TEMPLATE_GENERATOR_TAG = Template(
    " ".join(
        [
            "(this",
            "document",
            "was",
            "generated",
            "by",
            "files2md",
            "v${files2md_version}).",
            "\n",
        ]
    )
)


MIN_FENCE_LEN = 3
MAX_FENCE_LEN = 12


def count_lines(text: str) -> int:
    """Count the number of lines in text, as a text editor would.

    Args:
        text: The text to count lines in

    Returns:
        The number of lines. A trailing newline doesn't count as an extra line.

    Examples:
        count_lines("abc") -> 1
        count_lines("abc\n") -> 1
        count_lines("abc\ndef") -> 2
        count_lines("abc\ndef\n") -> 2
        count_lines("abc\n\n") -> 2
    """
    if not text:
        return 0
    lines = text.split('\n')
    if text.endswith('\n'):
        return len(lines) - 1
    return len(lines)


@dataclass
class FilePosition:
    """Represents the position of a file's content in the generated markdown."""
    path_desc: str          # e.g., "project/file.py"
    start_line: int         # First line of file's section (the ### header line)
    end_line: int           # Last line of file's section (after closing fence)
    content: str            # Generated markdown for this file


@dataclass(kw_only=True)
class TransformSummary:
    # files that were truncated due to max_lines_per_file
    truncated_files: list[Path] = field(default_factory=list)
    # count of included files by suffix
    suffix_to_file_count: dict[str, int] = field(default_factory=dict)
    # list of included files
    included_files: list[Path] = field(default_factory=list)
    # char count of included files
    files_to_char_count: dict[Path, int] = field(default_factory=dict)
    # files that will be listed in the Markdown but have their content excluded (e.g. binary files)
    content_excluded_files: dict[Path, bool] = field(default_factory=dict)


class OutputHandler(ABC):
    @abstractmethod
    def write(self, s: str):
        pass

    @abstractmethod
    def on_after_md_header(self):
        pass

    @abstractmethod
    def on_after_md_section(self):
        pass

    @abstractmethod
    def on_complete(self):
        pass

    @abstractmethod
    def get_filepaths(self) -> list[Path]:
        pass


class SingleFileOutputHandler(OutputHandler):
    def __init__(self, ofh: io.TextIOWrapper):
        self.ofh = ofh

    @override
    def write(self, s: str):
        self.ofh.write(s)

    @override
    def on_after_md_header(self):
        pass

    @override
    def on_after_md_section(self):
        pass

    @override
    def on_complete(self):
        self.ofh.close()

    @override
    def get_filepaths(self) -> list[Path]:
        if not hasattr(self.ofh, "name"):
            return []
        return [Path(self.ofh.name)]


class SplitFileOutputHandler(OutputHandler):
    def __init__(
        self, *, initial_path: Path, kb_per_file: int, output_encoding: str = "utf-8"
    ):
        self.initial_path = initial_path
        self.kb_per_file = kb_per_file
        self.output_encoding = output_encoding
        self.output_paths: list[Path] = []
        self.current_split_num: int = 0
        self.current_output_fh = None
        self.current_output_path = None
        self.current_output_fh, self.current_output_path = self.split()

    def split(self) -> tuple[io.TextIOWrapper, Path]:
        if self.current_output_fh:
            self.current_output_fh.close()
        if self.current_output_path:
            self.output_paths.append(self.current_output_path)
        self.current_split_num += 1
        current_split_path = self.get_current_split_filepath()
        self.current_output_fh = open(
            current_split_path, "w", encoding=self.output_encoding
        )
        self.current_output_path = current_split_path
        return self.current_output_fh, self.current_output_path

    def get_current_split_filepath(self):
        """
        for example:
            * if self.initial_path is == /tmp/data/foo.md
            * and self.current_split_num == 1
        then:
            * return == /tmp/data/foo-1.md
        """
        parent = self.initial_path.parent
        stem = self.initial_path.stem
        suffix = self.initial_path.suffix
        new_name = f"{stem}-{self.current_split_num}{suffix}"
        return parent / new_name

    @override
    def write(self, s: str):
        self.current_output_fh.write(s)

    @override
    def on_after_md_header(self):
        self.split()

    @override
    def on_after_md_section(self):
        if not self.current_output_fh:
            return
        tell = self.current_output_fh.tell()
        if tell > self.kb_per_file * 1000:
            self.split()

    @override
    def on_complete(self):
        if self.current_output_fh:
            self.current_output_fh.close()

    @override
    def get_filepaths(self) -> list[Path]:
        return self.output_paths + [self.current_output_path]


# if is type checking:

if TYPE_CHECKING:
    SplitFileOutputHandler(
        initial_path=Path(""), kb_per_file=0, output_encoding="utf-8"
    )


class MdWriter(contextlib.AbstractContextManager):
    def __init__(
        self,
        *,
        output: OutputHandler | Path | io.TextIOWrapper,
        max_lines_per_file: int = 0,
        include_empty: bool = False,
        mlpf_approx_pct: int = 25,
        project_name: str,
        in_dirs: list[Path],
        files: list[Path],
        md_formatter: "MdFormatter | None" = None,
        sub_rules_file: str,
        binary_patterns: list[str] | None = None,
    ):
        if isinstance(output, Path):
            output = open(output, "w", encoding="utf-8")
            self.output_handler = SingleFileOutputHandler(output)
        elif isinstance(output, io.TextIOWrapper):
            self.output_handler = SingleFileOutputHandler(output)
        else:
            self.output_handler = output
        self.in_dirs = in_dirs
        self.files = files
        self.project_name = project_name
        self.max_lines_per_file = max_lines_per_file
        self.include_empty = include_empty
        self.mlpf_approx_pct = mlpf_approx_pct
        self.tag_substr = self.make_tag_substr()
        self.total_chars_written = 0
        self.summary = TransformSummary()
        self.binary_patterns = binary_patterns or []

        def build_md_formatter() -> MdFormatter:
            if md_formatter is not None:
                return md_formatter
            return MdFormatter(
                tag_str=self.tag_substr,
                exclude_empty=not self.include_empty,
                max_lines_per_file=self.max_lines_per_file,
                mlpf_approx_pct=self.mlpf_approx_pct,
                sub_rules_file=sub_rules_file,
                binary_patterns=self.binary_patterns,
            )

        self.mdfmt: MdFormatter = build_md_formatter()

    def make_md(self):
        """Generate markdown with TOC containing line numbers for each file."""
        # Determine if we're in split mode
        is_split_mode = isinstance(self.output_handler, SplitFileOutputHandler)

        if is_split_mode:
            self._make_md_split_file()
        else:
            self._make_md_single_file()

    def _make_md_single_file(self):
        """Generate markdown for single-file output with line-numbered TOC."""
        in_dirs = self.in_dirs
        files = self.files

        # Step 1: Generate header prefix (without TOC)
        header_prefix = self.mdfmt.make_header_prefix(self.project_name)

        # Step 2: Generate all file content in memory
        file_data = []
        for file in sorted(files):
            if any(
                ofh_path.samefile(file)
                for ofh_path in self.output_handler.get_filepaths()
            ):
                continue
            pathdesc = self.describe_path(file, in_dirs)
            mdstr, content_truncated, content_excluded = self.mdfmt.file_to_md(
                file, pathdesc
            )
            file_data.append((file, pathdesc, mdstr, content_truncated, content_excluded))

        # Step 3: Calculate line positions
        # First, create dummy positions to estimate TOC size
        dummy_positions = [
            FilePosition(pathdesc, 1, 1, mdstr)
            for _, pathdesc, mdstr, _, _ in file_data
        ]
        dummy_toc = self.mdfmt.make_files_listing_with_lines(dummy_positions)

        # Calculate offset (lines before first file content)
        offset = count_lines(header_prefix + dummy_toc)

        # Now calculate actual positions
        current_line = offset + 1  # +1 for 1-based indexing
        file_positions = []
        for file, pathdesc, mdstr, truncated, excluded in file_data:
            num_lines = count_lines(mdstr)
            # Simple approach: start_line is where this chunk begins, end_line is where it ends
            # This naturally includes any spacing/structure from the template
            start_line = current_line
            end_line = current_line + num_lines - 1
            file_positions.append(FilePosition(pathdesc, start_line, end_line, mdstr))
            current_line = end_line + 1

            # Track for summary
            self.summary_track_file(file, mdstr, truncated, excluded)

        # Step 4: Generate real TOC with calculated positions
        toc = self.mdfmt.make_files_listing_with_lines(file_positions)

        # Step 5: Sanity check - TOC size should match estimate
        if count_lines(toc) != count_lines(dummy_toc):
            raise RuntimeError("TOC size changed after adding line numbers - this should not happen!")

        # Step 6: Write output
        self.output_handler.write(header_prefix + toc)
        self.output_handler.on_after_md_header()

        for fp in file_positions:
            self.output_handler.write(fp.content)
            self.output_handler.on_after_md_section()

    def _make_md_split_file(self):
        """Generate markdown for split-file output with per-split line-numbered TOCs."""
        in_dirs = self.in_dirs
        files = self.files

        # Step 1: Generate header prefix (without TOC)
        header_prefix = self.mdfmt.make_header_prefix(self.project_name)

        # Step 2: Generate all file content in memory
        all_file_data = []
        for file in sorted(files):
            if any(
                ofh_path.samefile(file)
                for ofh_path in self.output_handler.get_filepaths()
            ):
                continue
            pathdesc = self.describe_path(file, in_dirs)
            mdstr, content_truncated, content_excluded = self.mdfmt.file_to_md(
                file, pathdesc
            )
            # Create a temporary FilePosition (line numbers will be recalculated per-split)
            fp = FilePosition(pathdesc, 0, 0, mdstr)
            all_file_data.append((file, fp, content_truncated, content_excluded))

        # Step 3: Partition files into splits based on size
        split_handler = typing.cast(SplitFileOutputHandler, self.output_handler)
        splits = self._partition_files_for_splits(all_file_data, header_prefix, split_handler.kb_per_file)

        # Step 4: For each split, generate TOC with local line numbers and write
        for split_file_data in splits:
            # Extract just the FilePositions for this split
            split_fps = [fp for _, fp, _, _ in split_file_data]

            # Create dummy TOC to measure size
            dummy_positions = [
                FilePosition(fp.path_desc, 1, 1, fp.content)
                for fp in split_fps
            ]
            dummy_toc = self.mdfmt.make_files_listing_with_lines(dummy_positions)

            # Calculate offset for this split
            offset = count_lines(header_prefix + dummy_toc)

            # Recalculate line numbers local to this split
            current_line = offset + 1
            local_positions = []
            for fp in split_fps:
                num_lines = count_lines(fp.content)
                # Simple approach: start_line is where this chunk begins, end_line is where it ends
                # This naturally includes any spacing/structure from the template
                start_line = current_line
                end_line = current_line + num_lines - 1
                local_positions.append(FilePosition(fp.path_desc, start_line, end_line, fp.content))
                current_line = end_line + 1

            # Generate real TOC for this split
            toc = self.mdfmt.make_files_listing_with_lines(local_positions)

            # Write header + TOC + content for this split
            self.output_handler.write(header_prefix + toc)
            # Don't call on_after_md_header() here - we want content in the same file

            for fp in local_positions:
                self.output_handler.write(fp.content)
                self.output_handler.on_after_md_section()

            # Track summary for all files in this split
            for file, _, truncated, excluded in split_file_data:
                # Find the corresponding file position
                for fp in local_positions:
                    self.summary_track_file(file, fp.content, truncated, excluded)
                    break

    def _partition_files_for_splits(
        self,
        all_file_data: list[tuple[Path, FilePosition, bool, bool]],
        header_prefix: str,
        kb_per_file: int
    ) -> list[list[tuple[Path, FilePosition, bool, bool]]]:
        """Partition files into splits based on size limits.

        Args:
            all_file_data: List of (file, FilePosition, truncated, excluded) tuples
            header_prefix: The header text (used to estimate header size per split)
            kb_per_file: Size limit in kilobytes

        Returns:
            List of splits, where each split is a list of file data tuples
        """
        # Estimate header size (we'll add a TOC, but estimate conservatively)
        avg_toc_line_length = 100  # Rough estimate for "`path` (lines N-M)\n"
        est_files_per_split = max(1, (kb_per_file * 1000) // (avg_toc_line_length * 10))

        # Estimate TOC size for a split
        est_toc_lines = min(est_files_per_split, len(all_file_data))
        est_header_size_bytes = len(header_prefix.encode('utf-8')) + (est_toc_lines * avg_toc_line_length)

        splits = []
        current_split = []
        current_size_bytes = est_header_size_bytes
        bytes_limit = kb_per_file * 1000

        for file_data in all_file_data:
            _, fp, _, _ = file_data
            content_size_bytes = len(fp.content.encode('utf-8'))

            # Check if adding this file would exceed the limit
            # (but always include at least one file per split)
            if current_split and (current_size_bytes + content_size_bytes) > bytes_limit:
                # Finish current split and start a new one
                splits.append(current_split)
                current_split = [file_data]
                current_size_bytes = est_header_size_bytes + content_size_bytes
            else:
                # Add to current split
                current_split.append(file_data)
                current_size_bytes += content_size_bytes

        # Don't forget the last split
        if current_split:
            splits.append(current_split)

        return splits

    def make_tag_substr(self):
        tpl = TEMPLATE_GENERATOR_TAG.template.strip()
        spl = re.split(r"(\s+)", tpl)
        substr = "".join(spl[1:-1]).strip()
        return substr

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return self.output_handler.on_complete()

    def describe_path(self, path: Path, bases: list[Path]) -> str:
        for base in bases:
            if base in path.parents:
                relpos = path.relative_to(base).as_posix()
                desc = f"{base.name}/{relpos}"
                return desc
        return path.as_posix()

    def summary_track_file(
        self, file: Path, content: str, content_truncated: bool, content_excluded: bool
    ):
        ext = file.suffix
        if not ext:
            ext = file.name
        suffix2count = self.summary.suffix_to_file_count
        suffix2count[ext] = suffix2count.get(ext, 0) + 1
        self.summary.included_files.append(file)
        if content_excluded:
            self.summary.content_excluded_files[file] = True
        if content_truncated:
            self.summary.truncated_files.append(file)
        self.summary.files_to_char_count[file] = len(content)


class TextSubstituter(ABC):
    @abstractmethod
    def substitute(self, s: str) -> str:
        pass


class RETextSubstituter(TextSubstituter):
    def __init__(self, pattern: str, repl: str):
        self.pattern = re.compile(pattern)
        self.repl = repl
        print(f"RETextSubstituter {pattern=}, {repl=}")

    @override
    def substitute(self, s: str) -> str:
        result = self.pattern.sub(self.repl, s)
        print(f"RETextSubstituter {self.pattern=}, {self.repl=}, {s=}, {result=}")
        return result


class MdFormatter:
    def __init__(
        self,
        *,
        tag_str: str,
        exclude_empty: bool,
        max_lines_per_file: int,
        mlpf_approx_pct: int,
        sub_rules_file: str,
        binary_patterns: list[str] | None = None,
    ):
        self.tag_str = tag_str
        self.exclude_empty = exclude_empty
        self.max_lines_per_file = max_lines_per_file
        self.mlpf_approx_pct = mlpf_approx_pct
        self.sub_rules_file = sub_rules_file
        self.binary_patterns = binary_patterns or []
        self.compiled_sub_rules = self.compile_sub_rules()
        self.binary_pathspec = (
            pathspec.PathSpec.from_lines("gitwildmatch", self.binary_patterns)
            if self.binary_patterns
            else None
        )

    def compile_sub_rules(self) -> list[TextSubstituter]:
        # Linewise comments are supported in the substitution rules file via the `#` character.
        # Inline comments are not supported.
        # To begin a substitution with a literal `#` character, escape it with a backslash.
        # This works because Python's regex parser treats `\#` as a literal `#`.
        # Alternatively you could use a character class: `[#]`.
        # Separate the pattern and replacement with one or more tabs.
        re_comment_line = re.compile(r"^\s*#")
        if not self.sub_rules_file:
            return []
        substituters = []
        with open(self.sub_rules_file) as fh:
            for line in fh:
                if re_comment_line.match(line):
                    continue
                line = line.rstrip("\r\n")
                split = re.split(r"\t+", line)
                if len(split) != 2:
                    continue
                substituter = RETextSubstituter(split[0], split[1])
                substituters.append(substituter)
        return substituters

    def make_header_prefix(self, project_name: str) -> str:
        """Generate the header prefix without the file listing TOC.

        Args:
            project_name: The name of the project

        Returns:
            Header text with project name and generator tag, but no TOC
        """
        header_parts = [
            TEMPLATE_PROJECT.substitute(project_name=project_name),
            TEMPLATE_GENERATOR_TAG.substitute(files2md_version=files2md.__version__),
        ]
        return "\n".join(header_parts) + "\n"

    def make_files_listing_with_lines(self, file_positions: list[FilePosition]) -> str:
        """Generate file listing TOC with line numbers.

        Args:
            file_positions: List of FilePosition objects with line numbers

        Returns:
            Formatted TOC section with line numbers
        """
        files_lines = []
        for fp in file_positions:
            files_lines.append(f"`{fp.path_desc}` (lines {fp.start_line}-{fp.end_line})")
        files_listing = "\n".join(files_lines)
        return TEMPLATE_FILELIST.substitute(files_listing=files_listing)

    def make_header_md(self, project_name: str, pathdescs: Iterable[str]):
        """Generate complete header with file listing (legacy method without line numbers).

        This method is kept for backward compatibility.
        """
        files_listing = self.make_files_listing(pathdescs)
        header_parts = [
            TEMPLATE_PROJECT.substitute(project_name=project_name),
            TEMPLATE_GENERATOR_TAG.substitute(files2md_version=files2md.__version__),
            TEMPLATE_FILELIST.substitute(files_listing=files_listing),
        ]
        header = "\n".join(header_parts)
        return header

    def make_files_listing(self, pathdescs):
        """Generate simple file listing without line numbers (legacy method)."""
        files_lines = []
        for pathdesc in pathdescs:
            files_lines.append(f"`{pathdesc}`")
        files_lines_str = "\n".join(files_lines)
        return files_lines_str

    def binfile_to_md(self, _file: Path, pathname: str):
        mdchunk = TEMPLATE_BINARY_FILE.substitute(pathname=pathname)
        return mdchunk

    def fence_for_content(self, content: str):
        fence = "`" * MIN_FENCE_LEN
        for i in range(MIN_FENCE_LEN, MAX_FENCE_LEN + 1):
            fence = "`" * i
            if fence not in content:
                break
        return fence

    def textfile_to_md(
        self, file: Path, pathname: str, encoding: str
    ) -> tuple[str, bool]:
        included_lines, omitted_lines = self.read_file_lines(file, encoding)
        for tuter in self.compiled_sub_rules:
            included_lines = tuter.substitute("".join(included_lines)).splitlines(True)
        omission_msg = ""
        truncated = False
        if omitted_lines:
            omission_msg = TEMPLATE_OMISSION.substitute(
                omitted_line_count=len(omitted_lines)
            )
            truncated = True
        content = "".join(included_lines)
        if self.exclude_by_content(content):
            return "", truncated
        mdlang = self.guess_md_lang(file, content)
        fence = self.fence_for_content(content)
        mdchunk = TEMPLATE_FILE.substitute(
            pathname=pathname,
            fence=fence,
            mdlang=mdlang,
            content=content,
            omission_msg=omission_msg,
        )
        return mdchunk, truncated

    def exclude_by_content(self, content: str):
        content_without_ws = content.strip()
        content_is_empty = not content_without_ws
        if content_is_empty and self.exclude_empty:
            return True
        if self.tag_str and self.tag_str in content:
            return True
        return False

    def read_file_lines(
        self,
        file: Path,
        encoding: str,
        *,
        encoding_errors: str = "replace",
    ):
        with open(file, encoding=encoding, errors=encoding_errors) as fh:
            lines = []
            omitted_lines = []
            for i, line in enumerate(fh):
                if i < self.max_lines_per_file or self.max_lines_per_file <= 0:
                    lines.append(line)
                else:
                    omitted_lines.append(line)
        if self.mlpf_approx_pct > 0:
            wiggleroom = self.max_lines_per_file * self.mlpf_approx_pct // 100
            if len(omitted_lines) <= wiggleroom:
                lines.extend(omitted_lines)
                omitted_lines = []
        return lines, omitted_lines

    def file_to_md(self, file: Path, pathname: str) -> tuple[str, bool, bool]:
        """
        Returns a tuple of (mdchunk, content_excluded)

        mdchunk: str
            The markdown content for the file
        content_truncated: bool
            True if the content was truncated, False otherwise
        content_excluded: bool
            True if the content was excluded, False otherwise
        """
        truncated = False
        excluded = False

        # Check if file matches binary patterns
        if self.binary_pathspec and self.binary_pathspec.match_file(file):
            truncated = False
            excluded = False
            mdchunk = TEMPLATE_MARKED_BINARY_FILE.substitute(pathname=pathname)
            return mdchunk, truncated, excluded

        has_md_lang = fileinfo.FILEEXT_TO_MDLANG.get(file.suffix.lower(), False)
        if self.exclude_by_mime(file) and not has_md_lang:
            truncated = False
            excluded = True
            return (
                TEMPLATE_UNSUPPORTED_MIMETYPE.substitute(
                    pathname=pathname,
                    mimetype=self.guess_mime_type(file),
                ),
                truncated,
                excluded,
            )
        encoding = self.detect_encoding(file)
        if encoding == "binary":
            truncated = True
            excluded = False
            return self.binfile_to_md(file, pathname), truncated, excluded

        mdchunk, truncated = self.textfile_to_md(file, pathname, encoding)
        return mdchunk, truncated, excluded

    def guess_mime_type(self, file: Path):
        mimetype, _ = mimetypes.guess_type(file)
        if not mimetype:
            return ""
        return mimetype

    def exclude_by_mime(self, file: Path):
        mimetype = self.guess_mime_type(file)
        if mimetype in fileinfo.OK_MIMETYPES:
            return False
        supertype = mimetype.split("/")[0]
        if supertype in fileinfo.IGNORE_MIME_SUPERTYPES:
            return True
        return False

    def detect_encoding(self, file_path: Path, *, max_bytes: int = 100_000):
        if not charset_normalizer:
            return "utf-8"
        with open(file_path, "rb") as file:
            blob = file.read(max_bytes)
            matches = charset_normalizer.from_bytes(blob)
            if not matches:
                return "binary"
            best = matches.best()
            if not best:
                return "binary"
            return best.encoding

    def guess_md_lang(self, file_path: Path, _content: str):
        suffix = file_path.suffix
        if not suffix:
            return ""
        if suffix in fileinfo.FILEEXT_TO_MDLANG:
            return fileinfo.FILEEXT_TO_MDLANG[suffix]
        return fileinfo.FILEEXT_TO_MDLANG.get(suffix.lower(), "")

    def make_tag_substr(self):
        tpl = TEMPLATE_GENERATOR_TAG.template.strip()
        spl = re.split(r"(\s+)", tpl)
        substr = "".join(spl[1:-1]).strip()
        return substr
