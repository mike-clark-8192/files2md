from pathlib import Path
import charset_normalizer
import files2md.filespecs as filespecs


def detect_encoding(file_path: Path):
    with open(file_path, "rb") as file:
        blob = file.read(100_000)
        matches = charset_normalizer.from_bytes(blob)
        if not matches:
            return "binary"
        best = matches.best()
        if not best:
            return "binary"
        return best.encoding


def guess_md_lang(file_path: Path, _content: str):
    ext = file_path.suffix.removeprefix(".").lower()
    return filespecs.extn2mdlang.get(ext, "")


def binary2md(_file: Path, pathname: str):
    mdchunk = f"""
## `{pathname}`
(likely a binary file)
"""
    return mdchunk

def text2md(file: Path, pathname: str, encoding: str):
    content = file.read_text(encoding=encoding, errors="replace")
    mdlang = guess_md_lang(file, content)
    for i in range(3, 13):
        fence = "`" * i
        if fence not in content:
            break
    mdchunk = f"""
## `{pathname}`
{fence}{mdlang}
{content}
{fence}
"""
    return mdchunk

def file2md(file: Path, pathname: str):
    encoding = detect_encoding(file)
    if encoding == "binary":
        return binary2md(file, pathname)
    return text2md(file, pathname, encoding)

def make_header_md(project_name: str, pathdescs: list[str]):
    files_lines = []
    header_line = f"""# Project: {project_name}
    ## File listing: """
    for pathdesc in pathdescs:
        files_lines.append(f"`{pathdesc}`")
    files_lines_str = "\n".join(files_lines)
    full_header = f"""{header_line}\n\n{files_lines_str}\n"""
    return full_header