"""Pretty-print tabular data."""

import warnings
from collections import namedtuple
from collections.abc import Iterable, Sized
from html import escape as htmlescape
from itertools import chain, zip_longest as izip_longest
from functools import reduce, partial
import io
import re
import math
import textwrap
import dataclasses
import sys

try:
    import wcwidth  # optional wide-character (CJK) support
except ImportError:
    wcwidth = None


def _is_file(f):
    return isinstance(f, io.IOBase)


__all__ = ["tabulate", "tabulate_formats", "simple_separated_format"]
try:
    from .version import version as __version__  # noqa: F401
except ImportError:
    pass  # running __init__.py as a script, AppVeyor pytests


# minimum extra space in headers
MIN_PADDING = 2

# Whether or not to preserve leading/trailing whitespace in data.
PRESERVE_WHITESPACE = False

# TextWrapper breaks words longer than 'width'.
_BREAK_LONG_WORDS = True
# TextWrapper is breaking hyphenated words.
_BREAK_ON_HYPHENS = True


_DEFAULT_FLOATFMT = "g"
_DEFAULT_INTFMT = ""
_DEFAULT_MISSINGVAL = ""
# default align will be overwritten by "left", "center" or "decimal"
# depending on the formatter
_DEFAULT_ALIGN = "default"


# if True, enable wide-character (CJK) support
WIDE_CHARS_MODE = wcwidth is not None

# Constant that can be used as part of passed rows to generate a separating line
# It is purposely an unprintable character, very unlikely to be used in a table
SEPARATING_LINE = "\001"

Line = namedtuple("Line", ["begin", "hline", "sep", "end"])


DataRow = namedtuple("DataRow", ["begin", "sep", "end"])


# A table structure is supposed to be:
#
#     --- lineabove ---------
#         headerrow
#     --- linebelowheader ---
#         datarow
#     --- linebetweenrows ---
#     ... (more datarows) ...
#     --- linebetweenrows ---
#         last datarow
#     --- linebelow ---------
#
# TableFormat's line* elements can be
#
#   - either None, if the element is not used,
#   - or a Line tuple,
#   - or a function: [col_widths], [col_alignments] -> string.
#
# TableFormat's *row elements can be
#
#   - either None, if the element is not used,
#   - or a DataRow tuple,
#   - or a function: [cell_values], [col_widths], [col_alignments] -> string.
#
# padding (an integer) is the amount of white space around data values.
#
# with_header_hide:
#
#   - either None, to display all table elements unconditionally,
#   - or a list of elements not to be displayed if the table has column headers.
#
TableFormat = namedtuple(
    "TableFormat",
    [
        "lineabove",
        "linebelowheader",
        "linebetweenrows",
        "linebelow",
        "headerrow",
        "datarow",
        "padding",
        "with_header_hide",
    ],
)


def _is_separating_line_value(value):
    return type(value) is str and value.strip() == SEPARATING_LINE


def _is_separating_line(row):
    row_type = type(row)
    is_sl = (row_type == list or row_type == str) and (
        (len(row) >= 1 and _is_separating_line_value(row[0]))
        or (len(row) >= 2 and _is_separating_line_value(row[1]))
    )

    return is_sl


def _pipe_segment_with_colons(align, colwidth):
    """Return a segment of a horizontal line with optional colons which
    indicate column's alignment (as in `pipe` output format)."""
    w = colwidth
    if align in ["right", "decimal"]:
        return ("-" * (w - 1)) + ":"
    elif align == "center":
        return ":" + ("-" * (w - 2)) + ":"
    elif align == "left":
        return ":" + ("-" * (w - 1))
    else:
        return "-" * w


def _pipe_line_with_colons(colwidths, colaligns):
    """Return a horizontal line with optional colons to indicate column's
    alignment (as in `pipe` output format)."""
    if not colaligns:  # e.g. printing an empty data frame (github issue #15)
        colaligns = [""] * len(colwidths)
    segments = [_pipe_segment_with_colons(a, w) for a, w in zip(colaligns, colwidths)]
    return "|" + "|".join(segments) + "|"


def _grid_segment_with_colons(colwidth, align):
    """Return a segment of a horizontal line with optional colons which indicate
    column's alignment in a grid table."""
    width = colwidth
    if align == "right":
        return ("=" * (width - 1)) + ":"
    elif align == "center":
        return ":" + ("=" * (width - 2)) + ":"
    elif align == "left":
        return ":" + ("=" * (width - 1))
    else:
        return "=" * width


def _grid_line_with_colons(colwidths, colaligns):
    """Return a horizontal line with optional colons to indicate column's alignment
    in a grid table."""
    if not colaligns:
        colaligns = [""] * len(colwidths)
    segments = [_grid_segment_with_colons(w, a) for a, w in zip(colaligns, colwidths)]
    return "+" + "+".join(segments) + "+"


def _mediawiki_row_with_attrs(separator, cell_values, colwidths, colaligns):
    alignment = {
        "left": "",
        "right": 'style="text-align: right;"| ',
        "center": 'style="text-align: center;"| ',
        "decimal": 'style="text-align: right;"| ',
    }
    # hard-coded padding _around_ align attribute and value together
    # rather than padding parameter which affects only the value
    values_with_attrs = [
        " " + alignment.get(a, "") + c + " " for c, a in zip(cell_values, colaligns)
    ]
    colsep = separator * 2
    return (separator + colsep.join(values_with_attrs)).rstrip()


def _textile_row_with_attrs(cell_values, colwidths, colaligns):
    cell_values[0] += " "
    alignment = {"left": "<.", "right": ">.", "center": "=.", "decimal": ">."}
    values = (alignment.get(a, "") + v for a, v in zip(colaligns, cell_values))
    return "|" + "|".join(values) + "|"


def _html_begin_table_without_header(colwidths_ignore, colaligns_ignore):
    # this table header will be suppressed if there is a header row
    return "<table>\n<tbody>"


def _html_row_with_attrs(celltag, unsafe, cell_values, colwidths, colaligns):
    alignment = {
        "left": "",
        "right": ' style="text-align: right;"',
        "center": ' style="text-align: center;"',
        "decimal": ' style="text-align: right;"',
    }
    if unsafe:
        values_with_attrs = [
            "<{0}{1}>{2}</{0}>".format(celltag, alignment.get(a, ""), c)
            for c, a in zip(cell_values, colaligns)
        ]
    else:
        values_with_attrs = [
            "<{0}{1}>{2}</{0}>".format(celltag, alignment.get(a, ""), htmlescape(c))
            for c, a in zip(cell_values, colaligns)
        ]
    rowhtml = "<tr>{}</tr>".format("".join(values_with_attrs).rstrip())
    if celltag == "th":  # it's a header row, create a new table header
        rowhtml = f"<table>\n<thead>\n{rowhtml}\n</thead>\n<tbody>"
    return rowhtml


def _moin_row_with_attrs(celltag, cell_values, colwidths, colaligns, header=""):
    alignment = {
        "left": "",
        "right": '<style="text-align: right;">',
        "center": '<style="text-align: center;">',
        "decimal": '<style="text-align: right;">',
    }
    values_with_attrs = [
        "{}{} {} ".format(celltag, alignment.get(a, ""), header + c + header)
        for c, a in zip(cell_values, colaligns)
    ]
    return "".join(values_with_attrs) + "||"


def _latex_line_begin_tabular(colwidths, colaligns, booktabs=False, longtable=False):
    alignment = {"left": "l", "right": "r", "center": "c", "decimal": "r"}
    tabular_columns_fmt = "".join([alignment.get(a, "l") for a in colaligns])
    return "\n".join(
        [
            ("\\begin{tabular}{" if not longtable else "\\begin{longtable}{")
            + tabular_columns_fmt
            + "}",
            "\\toprule" if booktabs else "\\hline",
        ]
    )


def _asciidoc_row(is_header, *args):
    """handle header and data rows for asciidoc format"""

    def make_header_line(is_header, colwidths, colaligns):
        # generate the column specifiers

        alignment = {"left": "<", "right": ">", "center": "^", "decimal": ">"}
        # use the column widths generated by tabulate for the asciidoc column width specifiers
        asciidoc_alignments = zip(
            colwidths, [alignment[colalign] for colalign in colaligns]
        )
        asciidoc_column_specifiers = [
            f"{width:d}{align}" for width, align in asciidoc_alignments
        ]
        header_list = ['cols="' + (",".join(asciidoc_column_specifiers)) + '"']

        # generate the list of options (currently only "header")
        options_list = []

        if is_header:
            options_list.append("header")

        if options_list:
            header_list += ['options="' + ",".join(options_list) + '"']

        # generate the list of entries in the table header field

        return "[{}]\n|====".format(",".join(header_list))

    if len(args) == 2:
        # two arguments are passed if called in the context of aboveline
        # print the table header with column widths and optional header tag
        return make_header_line(False, *args)

    elif len(args) == 3:
        # three arguments are passed if called in the context of dataline or headerline
        # print the table line and make the aboveline if it is a header

        cell_values, colwidths, colaligns = args
        data_line = "|" + "|".join(cell_values)

        if is_header:
            return make_header_line(True, colwidths, colaligns) + "\n" + data_line
        else:
            return data_line

    else:
        raise ValueError(
            " _asciidoc_row() requires two (colwidths, colaligns) "
            + "or three (cell_values, colwidths, colaligns) arguments) "
        )


LATEX_ESCAPE_RULES = {
    r"&": r"\&",
    r"%": r"\%",
    r"$": r"\$",
    r"#": r"\#",
    r"_": r"\_",
    r"^": r"\^{}",
    r"{": r"\{",
    r"}": r"\}",
    r"~": r"\textasciitilde{}",
    "\\": r"\textbackslash{}",
    r"<": r"\ensuremath{<}",
    r">": r"\ensuremath{>}",
}


def _latex_row(cell_values, colwidths, colaligns, escrules=LATEX_ESCAPE_RULES):
    def escape_char(c):
        return escrules.get(c, c)

    escaped_values = ["".join(map(escape_char, cell)) for cell in cell_values]
    rowfmt = DataRow("", "&", "\\\\")
    return _build_simple_row(escaped_values, rowfmt)


def _rst_escape_first_column(rows, headers):
    def escape_empty(val):
        if isinstance(val, (str, bytes)) and not val.strip():
            return ".."
        else:
            return val

    new_headers = list(headers)
    new_rows = []
    if headers:
        new_headers[0] = escape_empty(headers[0])
    for row in rows:
        new_row = list(row)
        if new_row:
            new_row[0] = escape_empty(row[0])
        new_rows.append(new_row)
    return new_rows, new_headers


_table_formats = {
    "simple": TableFormat(
        lineabove=Line("", "-", "  ", ""),
        linebelowheader=Line("", "-", "  ", ""),
        linebetweenrows=None,
        linebelow=Line("", "-", "  ", ""),
        headerrow=DataRow("", "  ", ""),
        datarow=DataRow("", "  ", ""),
        padding=0,
        with_header_hide=["lineabove", "linebelow"],
    ),
    "plain": TableFormat(
        lineabove=None,
        linebelowheader=None,
        linebetweenrows=None,
        linebelow=None,
        headerrow=DataRow("", "  ", ""),
        datarow=DataRow("", "  ", ""),
        padding=0,
        with_header_hide=None,
    ),

def _more_generic(type1, type2):
    types = {
        type(None): 0,
        bool: 1,
        int: 2,
        float: 3,
        bytes: 4,
        str: 5,
    }
    invtypes = {
        5: str,
        4: bytes,
        3: float,
        2: int,
        1: bool,
        0: type(None),
    }
    moregeneric = max(types.get(type1, 5), types.get(type2, 5))
    return invtypes[moregeneric]

def _main():
    """\
    Usage: tabulate [options] [FILE ...]

    Pretty-print tabular data.
    See also https://github.com/astanin/python-tabulate

    FILE                      a filename of the file with tabular data;
                              if "-" or missing, read data from stdin.

    Options:

    -h, --help                show this message
    -1, --header              use the first row of data as a table header
    -o FILE, --output FILE    print table to FILE (default: stdout)
    -s REGEXP, --sep REGEXP   use a custom column separator (default: whitespace)
    -F FPFMT, --float FPFMT   floating point number format (default: g)
    -I INTFMT, --int INTFMT   integer point number format (default: "")
    -f FMT, --format FMT      set output table format; supported formats:
                              plain, simple, grid, fancy_grid, pipe, orgtbl,
                              rst, mediawiki, html, latex, latex_raw,
                              latex_booktabs, latex_longtable, tsv
                              (default: simple)
    """
    import getopt

    usage = textwrap.dedent(_main.__doc__)
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            "h1o:s:F:I:f:",
            [
                "help",
                "header",
                "output=",
                "sep=",
                "float=",
                "int=",
                "colalign=",
                "format=",
            ],
        )
    except getopt.GetoptError as e:
        print(e)
        print(usage)
        sys.exit(2)
    headers = []
    floatfmt = _DEFAULT_FLOATFMT
    intfmt = _DEFAULT_INTFMT
    colalign = None
    tablefmt = "simple"
    sep = r"\s+"
    outfile = "-"
    for opt, value in opts:
        if opt in ["-1", "--header"]:
            headers = "firstrow"
        elif opt in ["-o", "--output"]:
            outfile = value
        elif opt in ["-F", "--float"]:
            floatfmt = value
        elif opt in ["-I", "--int"]:
            intfmt = value
        elif opt in ["-C", "--colalign"]:
            colalign = value.split()
        elif opt in ["-f", "--format"]:
            if value not in tabulate_formats:
                print("%s is not a supported table format" % value)
                print(usage)
                sys.exit(3)
            tablefmt = value
        elif opt in ["-s", "--sep"]:
            sep = value
        elif opt in ["-h", "--help"]:
            print(usage)
            sys.exit(0)
    files = [sys.stdin] if not args else args
    with sys.stdout if outfile == "-" else open(outfile, "w") as out:
        for f in files:
            if f == "-":
                f = sys.stdin
            if _is_file(f):
                _pprint_file(
                    f,
                    headers=headers,
                    tablefmt=tablefmt,
                    sep=sep,
                    floatfmt=floatfmt,
                    intfmt=intfmt,
                    file=out,
                    colalign=colalign,
                )
            else:
                with open(f) as fobj:
                    _pprint_file(
                        fobj,
                        headers=headers,
                        tablefmt=tablefmt,
                        sep=sep,
                        floatfmt=floatfmt,
                        intfmt=intfmt,
                        file=out,
                        colalign=colalign,
                    )


def _pprint_file(fobject, headers, tablefmt, sep, floatfmt, intfmt, file, colalign):
    rows = fobject.readlines()
    table = [re.split(sep, r.rstrip()) for r in rows if r.strip()]
    print(
        tabulate(
            table,
            headers,
            tablefmt,
            floatfmt=floatfmt,
            intfmt=intfmt,
            colalign=colalign,
        ),
        file=file,
    )


if __name__ == "__main__":
    _main()
