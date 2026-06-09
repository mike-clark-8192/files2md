# How file selection works

`files2md` decides which files to include by building a single ordered list of
[gitwildmatch](https://github.com/cpburnz/python-pathspec) patterns and applying
**last-match-wins** semantics (the same model as `.gitignore` / ripgrep).

Polarity is **inverted from a raw `.gitignore`** (and identical to ripgrep's
`-g`): a bare pattern **includes**, and a `!`-prefixed pattern **excludes**.

```
*.py        # include all Python files
!build/     # ...but exclude the build/ directory
```

## The four layers

Patterns are assembled top-to-bottom. Because the last matching pattern wins, a
lower layer overrides a higher one:

| Layer | Source | Role |
|------:|--------|------|
| 0 | `--baseline` | the starting set |
| 1 | everyday exclude sets | carve out low-signal junk |
| 2 | `-g` / `--glob` | **your** patterns — override layers 0 and 1 |
| 3 | sensitive excludes | secrets — the last word, override-proof |

### Layer 0 — baseline (`--baseline all|known|none`)

- `all` *(default)* — start from `**` (everything). Denylist style.
- `known` — start from only recognised source/text file types (derived from the
  built-in extension→language map plus common names like `README`, `Makefile`,
  `Dockerfile`). Allowlist style.
- `none` — start empty; include nothing until you add `-g` patterns.

### Layer 1 — everyday excludes (`--no-default-patterns` to disable)

Four categories, all on by default: `binary`, `vcs`, `generated`, `noisy`
(see `EVERYDAY_EXCLUDE_SETS` in `src/files2md/fileinfo.py`). These are
*overridable* — a Layer 2 include brings a file back.

### Layer 2 — your patterns (`-g` / `--glob`)

Your include/exclude patterns. Repeatable and order-preserving; sits **after**
the built-in excludes, so you always have precedence over them. This is the one
place command-line patterns live (there is no separate `--exclude` flag — use
`-g '!PAT'`).

### Layer 3 — sensitive excludes (`--include-sensitive` to lift)

`.env`, `*.pem`, `id_rsa`, and friends (see `SENSITIVE_EXCLUDES`). Applied
**after** your patterns, so even `-g '**'` cannot re-expose them by accident.
Opt in deliberately with `--include-sensitive`.

## Worked examples

```sh
# Everything except junk; secrets stay out. (the default)
files2md ./project -o out.md

# Only known source types, plus one extra extension.
files2md ./project --baseline known -g '*.weirdext' -o out.md

# Everything, including the junk, but still no secrets.
files2md ./project --no-default-patterns -o out.md

# Literally everything, secrets included (your own throwaway project).
files2md ./project --no-default-patterns --include-sensitive -o out.md

# Full manual control: nothing unless you name it.
files2md ./project --baseline none -g '*.py' 'src/**' '!**/test_*.py' -o out.md
```
