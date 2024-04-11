import io
import mimetypes
import re
from dataclasses import dataclass, field
from pathlib import Path
from string import Template
from types import ModuleType
from typing import Iterable

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
(likely a binary file)"""
)

TEMPLATE_UNSUPPORTED_MIMETYPE = Template(
    """### `${pathname}`
(content excluded due to unsupported MIME type: ${mimetype})"""
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


class MdTransform:
    def __init__(
        self,
        *,
        max_lines_per_file: int = 0,
        include_empty: bool = False,
        mlpf_approx_pct: int = 25,
    ):
        self.max_lines_per_file = max_lines_per_file
        self.include_empty = include_empty
        self.mlpf_approx_pct = mlpf_approx_pct
        self.tag_substr = self.make_tag_substr()
        self.total_chars_written = 0
        self.summary = TransformSummary()

    def make_md(
        self,
        project_name: str,
        in_dirs: list[Path],
        files: list[Path],
        ofh: io.IOBase,
    ):
        path_descs = {file: self.describe_path(file, in_dirs) for file in files}
        header = self.make_header_md(project_name, path_descs.values())
        ofh.write(header)
        ofh_path = Path(getattr(ofh, "name", ""))
        for file in sorted(files):
            if ofh_path.samefile(file):
                continue
            pathdesc = path_descs[file]
            mdstr, content_excluded = self.file_to_md(file, pathdesc)
            ofh.write(mdstr)
            self.summary_track_file(file, mdstr, content_excluded)

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

    def textfile_to_md(self, file: Path, pathname: str, encoding: str):
        included_lines, omitted_lines = self.read_file_lines(file, encoding)
        omission_msg = ""
        if omitted_lines:
            omission_msg = TEMPLATE_OMISSION.substitute(
                omitted_line_count=len(omitted_lines)
            )
            self.summary.truncated_files.append(file)
        content = "".join(included_lines)
        if self.exclude_by_content(content):
            return ""
        mdlang = self.guess_md_lang(file, content)
        fence = self.fence_for_content(content)
        mdchunk = TEMPLATE_FILE.substitute(
            pathname=pathname,
            fence=fence,
            mdlang=mdlang,
            content=content,
            omission_msg=omission_msg,
        )
        return mdchunk

    def exclude_by_content(self, content: str):
        content_without_ws = content.strip()
        content_is_empty = not content_without_ws
        cfg_exclude_empty = not self.include_empty
        if content_is_empty and cfg_exclude_empty:
            return True
        if self.tag_substr in content:
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

    def file_to_md(self, file: Path, pathname: str) -> tuple[str, bool]:
        """
        Returns a tuple of (mdchunk, content_excluded)

        mdchunk: str
            The markdown content for the file
        content_excluded: bool
            True if the content was excluded, False otherwise
        """
        if self.exclude_by_mime(file):
            return (
                TEMPLATE_UNSUPPORTED_MIMETYPE.substitute(
                    pathname=pathname,
                    mimetype=self.guess_mime_type(file),
                ),
                True,
            )
        encoding = self.detect_encoding(file)
        if encoding == "binary":
            return self.binfile_to_md(file, pathname), True
        return self.textfile_to_md(file, pathname, encoding), False

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

    def describe_path(self, path: Path, bases: list[Path]) -> str:
        for base in bases:
            if base in path.parents:
                relpos = path.relative_to(base).as_posix()
                desc = f"{base.name}/{relpos}"
                return desc
        return path.as_posix()

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

    def summary_track_file(self, file: Path, content: str, content_excluded: bool):
        ext = file.suffix
        if not ext:
            ext = file.name
        suffix2count = self.summary.suffix_to_file_count
        suffix2count[ext] = suffix2count.get(ext, 0) + 1
        self.summary.included_files.append(file)
        if content_excluded:
            self.summary.content_excluded_files[file] = True
        self.summary.files_to_char_count[file] = len(content)

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
