import re


def generate_binaryprefix_to_size_dict() -> dict[str, int]:
    prefix_to_size: dict[str, int] = {}
    for i, prefix in enumerate(["", "K", "M", "G", "T", "P", "E"]):
        prefix_to_size[prefix] = 10 ** (3 * i)
        if prefix == "":
            continue
        prefix_to_size[prefix + "i"] = 2 ** (10 * i)
    return prefix_to_size


def generate_humansize_regex() -> re.Pattern:
    keys = list(sorted(BINARYPREFIX_TO_SIZE.keys(), key=len, reverse=True))
    prefixes = list(map(re.escape, keys))
    re_prefix_alternation = "|".join(prefixes)
    re_pattern = rf"""
    ^\s*
    (?P<number>[0-9.]+)
    \s*
    (?P<binaryprefix>{re_prefix_alternation})
    (?P<unit>[^\s]*)
    \s*$
    """
    return re.compile(re_pattern, re.VERBOSE | re.IGNORECASE)


BINARYPREFIX_TO_SIZE: dict[str, int] = generate_binaryprefix_to_size_dict()
BINARYPREFIX_LOWER_TO_SIZE: dict[str, int] = {
    k.lower(): v for k, v in BINARYPREFIX_TO_SIZE.items()
}
HUMANSIZE_REGEX = generate_humansize_regex()


def humansize_to_size(humansize: str) -> int:
    def _invalid_size(msg: str = "", e: Exception | None = None) -> ValueError:
        msg = f": {msg}" if msg else ""
        value_error = ValueError(f"Invalid size '{humansize}'{msg}")
        value_error.__cause__ = e
        return value_error

    match = HUMANSIZE_REGEX.match(humansize)
    if not match:
        raise _invalid_size()
    number = match.group("number")
    binaryprefix = match.group("binaryprefix")
    unit = match.group("unit")
    if unit == "b":
        raise ValueError(
            f"Invalid size: {humansize}; unit '{unit}' is ambiguous; use 'B' for bytes."
        )
    if not (unit == "" or unit == "B"):
        raise ValueError(f"Invalid size: {humansize}; unknown unit '{unit}'.")
    try:
        number = float(number)
    except ValueError as e:
        raise _invalid_size(str(e), e)
    prefix_size = BINARYPREFIX_LOWER_TO_SIZE.get(binaryprefix.lower(), None)
    if prefix_size is None:
        raise ValueError(f"unknown binary prefix: {unit}")
    return int(number * prefix_size)
