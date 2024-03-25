from pathlib import Path
from typing import Any, Iterable
import contextlib


class VPrinter(contextlib.AbstractContextManager):
    def __init__(self, verbosity: int = 0, default_verbosity: int = 1):
        self.verbosity = verbosity
        self.default_verbosity = default_verbosity
        pass

    def __enter__(self):
        self.print_fn(self.default_verbosity, "=" * 78)
        return self

    def __exit__(self, *exc):
        self.print_fn(self.default_verbosity, "=" * 78)

    def section(self, verbosity: int, title: str, items: Any, delim: str = ""):
        if verbosity > self.verbosity:
            return
        print(f" ⮦ {title} ⮧ ".center(78, "-"))
        if isinstance(items, dict):
            for k, v in items.items():
                print(f"{k}: {v}")
        elif isinstance(items, Iterable):
            desc = list(map(str, items))
            if delim:
                print(delim.join(desc))
            else:
                print(desc)
        else:
            print(str(items))

    def print_fn(self, verbosity: int, *args, **kwargs):
        if verbosity > self.verbosity:
            return
        print(*args, **kwargs)
