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
        stem = self.initial_path.parent / self.initial_path.stem
        suffix = self.initial_path.suffix
        new_suffix = f"-{self.current_split_num}.{suffix}"
        return stem.with_suffix(new_suffix)

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

        def build_md_formatter() -> MdFormatter:
            if md_formatter is not None:
                return md_formatter
            return MdFormatter(
                tag_str=self.tag_substr,
                exclude_empty=not self.include_empty,
                max_lines_per_file=self.max_lines_per_file,
                mlpf_approx_pct=self.mlpf_approx_pct,
                sub_rules_file=sub_rules_file,
            )

        self.mdfmt: MdFormatter = build_md_formatter()

    def make_md(
        self,
    ):
        in_dirs = self.in_dirs
        files = self.files
        path_descs = {file: self.describe_path(file, in_dirs) for file in files}
        header = self.mdfmt.make_header_md(self.project_name, path_descs.values())
        self.output_handler.write(header)
        self.output_handler.on_after_md_header()
        for file in sorted(files):
            if any(
                ofh_path.samefile(file)
                for ofh_path in self.output_handler.get_filepaths()
            ):
                continue
            pathdesc = path_descs[file]
            mdstr, content_truncated, content_excluded = self.mdfmt.file_to_md(
                file, pathdesc
            )
            self.output_handler.write(mdstr)
            self.output_handler.on_after_md_section()
            self.summary_track_file(file, mdstr, content_truncated, content_excluded)

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
    ):
        self.tag_str = tag_str
        self.exclude_empty = exclude_empty
        self.max_lines_per_file = max_lines_per_file
        self.mlpf_approx_pct = mlpf_approx_pct
        self.sub_rules_file = sub_rules_file
        self.compiled_sub_rules = self.compile_sub_rules()

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

    def make_header_md(self, project_name: str, pathdescs: Iterable[str]):
        files_listing = self.make_files_listing(pathdescs)
        header_parts = [
            TEMPLATE_PROJECT.substitute(project_name=project_name),
            TEMPLATE_GENERATOR_TAG.substitute(files2md_version=files2md.__version__),
            TEMPLATE_FILELIST.substitute(files_listing=files_listing),
        ]
        header = "\n".join(header_parts)
        return header

    def make_files_listing(self, pathdescs):
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
