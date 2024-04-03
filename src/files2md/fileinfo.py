DEFAULT_PATTERNS = [
    ## exclude text files
    "!.env",
    "!.envrc",
    "!pdm.lock",
    "!poetry.lock",
    "!Pipfile.lock",
    "!package-lock.json",
    "!yarn.lock",
    "!pnpm-lock.yaml",
    "!.gitignore",
    "!.dockerignore",
    "!.npmignore",
    "!.prettierignore",
    "!.eslintignore",
    "!.gitattributes",
    "!.gitmodules",
    "!.gitconfig",
    "!.gitkeep",
    "!CODE_OF_CONDUCT.md",
    "!CONTRIBUTING.md",
    "!SECURITY.md",
    "!.DS_Store",
    "!*.swp",
    "!*.swo",
    "!*.log",
    # "!*.log.*",
    "!*.tmp",
    "!*.temp",
    "!*.bak",
    "!*.old",
    "!*.orig",
    "!*.rej",
    "!*.swx",
    "!*.swn",
    "!*.swo",
    "!*.swp",
    ## svn conflict files
    "!*.mine",
    # "!*.r*",
    "!*.prej",
    # "!*.wr*",
    "!*.wrk",
    "!*.base",
    "!*.orig",
    ## binary stuff
    "*.dump",
    "*.dmp",
    "*.o",
    "*.obj",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.exe",
    "*.bin",
    "*.a",
    "*.lib",
    "*.apk",
    "*.dylib",
    "*.app",
    "*.appx",
    "*.appxbundle",
    "*.ipa",
    "*.msi",
    "*.msix",
    "*.suo",
    "*.pdb",
    "*.idb",
    "*.ilk",
    "*.exp",
    ## re-include files
    "README",
    "README.md",
    "README.txt",
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    ## exclude dirs
    "!.git/",
    "!.svn/",
    "!.hg/",
    "!.venv/",
    "!venv/",
    "!node_modules/",
    "!__pycache__/",
    "!.tox/",
    "!.pytest_cache/",
    "!/out/",
    "!/dist/",
    "!.pdm-build/",
    "!.github/",
    "!.*cache*/",
    "!.mypy_cache/",
    "!.pytest_cache/",
    "!.nyc_output/",
    "!.coverage/",
    ## some people might like to see the IDE settings,
    ## so we will not exclude these:
    # "!.vscode/",
    # "!.idea/",
    # "!.vs/",
    # "!.sublime/",
    # "!.emacs.d/",
    # "!.vim/",
    # "!.vimrc",
    ## more common cache dirs excluded:
    "!.cache/",
    "!.local/",
    "!.npm/",
    "!.yarn/",
    "!.tox/",
    "!.pytest_cache/",
    "!.mypy_cache/",
    "!.nyc_output/",
    "!.coverage/",
    ## .vscode is not a cache dir, but here are some more:
    "!.serverless*/",
    "!.serverless/",
    "!.terraform*/",
    "!.terraform/",
    "!.vagrant*/",
    "!.vagrant/",
]

IGNORE_MIME_SUPERTYPES = [
    "application",
    "audio",
    "font",
    "image",
    "video",
]

# overrides IGNORE_MIME_SUPERTYPES
OK_MIMETYPES = [
    "application/json",
    "application/manifest+json",
    "application/postscript",
    "application/vnd.adobe.xdp+xml",
    "application/xml",
    "application/xaml+xml",
    "application/opensearchdescription+xml",
    "application/javascript",
    "application/xhtml+xml",
    "Application/xml",
    "application/xml-dtd",
    "application/xslt+xml",
    "application/x-javascript",
    "application/x-sh",
    "application/x-tex",
    "application/x-latex",
    "string",
]

FILEEXT_TO_MDLANG = {
    ".1": "troff",
    ".2": "troff",
    ".3": "troff",
    ".4": "troff",
    ".4th": "forth",
    ".5": "troff",
    ".6": "troff",
    ".7": "troff",
    ".8": "troff",
    ".9": "troff",
    ".apl": "apl",
    ".asc": "asciiarmor",
    ".asn": "asn1",
    ".asn1": "asn1",
    ".b": "brainfuck",
    ".bash": "shell",
    ".bat": "batch",
    ".bf": "brainfuck",
    ".build": "python",
    ".bzl": "python",
    ".c": "cpp",
    ".c++": "cpp",
    ".cc": "cpp",
    ".cfg": "ttcn-cfg",
    ".cjs": "javascript",
    ".cl": "lisp",
    ".clj": "clojure",
    ".cljc": "clojure",
    ".cljs": "clojure",
    ".cljx": "clojure",
    ".cmake.in": "cmake",
    ".cmake": "cmake",
    ".cmd": "batch",
    ".cob": "cobol",
    ".coffee": "coffeescript",
    ".cpp": "cpp",
    ".cpy": "cobol",
    ".cql": "sql",
    ".cr": "crystal",
    ".cs": "clike",
    ".css": "css",
    ".cxx": "cpp",
    ".cyp": "cypher",
    ".cypher": "cypher",
    ".d": "d",
    ".dart": "clike",
    ".diff": "diff",
    ".dtd": "dtd",
    ".dyalog": "apl",
    ".dyl": "dylan",
    ".dylan": "dylan",
    ".e": "eiffel",
    ".ecl": "ecl",
    ".edn": "clojure",
    ".el": "lisp",
    ".elm": "elm",
    ".erl": "erlang",
    ".f": "fortran",
    ".f77": "fortran",
    ".f90": "fortran",
    ".f95": "fortran",
    ".factor": "factor",
    ".feature": "gherkin",
    ".for": "fortran",
    ".forth": "forth",
    ".fs": "mllike",
    ".fth": "forth",
    ".gemspec": "ruby",
    ".go": "go",
    ".gradle": "groovy",
    ".groovy": "groovy",
    ".gss": "css",
    ".h": "cpp",
    ".h++": "cpp",
    ".handlebars": "html",
    ".hbs": "html",
    ".hh": "cpp",
    ".hpp": "cpp",
    ".hs": "haskell",
    ".htm": "html",
    ".html": "html",
    ".hx": "haxe",
    ".hxml": "haxe",
    ".hxx": "cpp",
    ".in": "properties",
    ".ini": "properties",
    ".ino": "cpp",
    ".intr": "dylan",
    ".irb": "ruby",
    ".j2": "jinja2",
    ".java": "java",
    ".jinja": "jinja2",
    ".jinja2": "jinja2",
    ".jl": "julia",
    ".js": "javascript",
    ".jse": "javascript",
    ".json": "json",
    ".jsonld": "javascript",
    ".jsx": "javascript",
    ".ksh": "shell",
    ".kt": "clike",
    ".less": "css",
    ".lisp": "lisp",
    ".ls": "livescript",
    ".ltx": "stex",
    ".lua": "lua",
    ".m": "clike",
    ".map": "json",
    ".markdown": "markdown",
    ".mbox": "mbox",
    ".md": "markdown",
    ".mjs": "javascript",
    ".mkd": "markdown",
    ".ml": "mllike",
    ".mli": "mllike",
    ".mll": "mllike",
    ".mly": "mllike",
    ".mm": "clike",
    ".mo": "modelica",
    ".mps": "mumps",
    ".msc": "mscgen",
    ".mscgen": "mscgen",
    ".mscin": "mscgen",
    ".msgenny": "mscgen",
    ".nb": "mathematica",
    ".nq": "ntriples",
    ".nsh": "nsis",
    ".nsi": "nsis",
    ".nt": "ntriples",
    ".nut": "clike",
    ".oz": "oz",
    ".p": "pascal",
    ".pas": "pascal",
    ".patch": "diff",
    ".pgp": "asciiarmor",
    ".php": "php",
    ".php3": "php",
    ".php4": "php",
    ".php5": "php",
    ".php7": "php",
    ".phtml": "php",
    ".pig": "pig",
    ".pl": "perl",
    ".pls": "sql",
    ".pm": "perl",
    ".podspec": "ruby",
    ".pp": "puppet",
    ".pro": "idl",
    ".properties": "properties",
    ".proto": "protobuf",
    ".ps1": "powershell",
    ".psd1": "powershell",
    ".psm1": "powershell",
    ".pxd": "python",
    ".pxi": "python",
    ".py": "python",
    ".pyw": "python",
    ".pyx": "python",
    ".q": "q",
    ".r": "r",
    ".r": "r",
    ".rake": "ruby",
    ".rb": "ruby",
    ".rb": "ruby",
    ".rbw": "ruby",
    ".rq": "sparql",
    ".rs": "rust",
    ".s": "gas",
    ".sas": "sas",
    ".scala": "clike",
    ".scm": "scheme",
    ".scss": "css",
    ".sh": "shell",
    ".sieve": "sieve",
    ".sig": "asciiarmor",
    ".siv": "sieve",
    ".sparql": "sparql",
    ".spec": "rpm",
    ".sql": "sql",
    ".ss": "scheme",
    ".st": "smalltalk",
    ".styl": "stylus",
    ".svg": "xml",
    ".swift": "swift",
    ".tcl": "tcl",
    ".tex": "stex",
    ".text": "stex",
    ".textile": "textile",
    ".thor": "ruby",
    ".toml": "toml",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".ttcn": "ttcn",
    ".ttcn3": "ttcn",
    ".ttcnpp": "ttcn",
    ".ttl": "turtle",
    ".v": "verilog",
    ".vb": "vb",
    ".vbe": "vbscript",
    ".vbs": "vbscript",
    ".vhd": "vhdl",
    ".vhdl": "vhdl",
    ".vtl": "velocity",
    ".wast": "wast",
    ".wat": "wast",
    ".webidl": "webidl",
    ".wl": "mathematica",
    ".wls": "mathematica",
    ".xml": "xml",
    ".xquery": "xquery",
    ".xsd": "xml",
    ".xsl": "xml",
    ".xu": "mscgen",
    ".xy": "xquery",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".ys": "yacas",
    ".z80": "z80",
    # ---------------------
    ".md": "markdown",
    ".py": "python",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "fish",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".kt": "kotlin",
    ".rs": "rust",
    ".go": "go",
    ".php": "php",
    ".sql": "sql",
    ".rb": "ruby",
    ".r": "r",
    ".lua": "lua",
    ".swift": "swift",
    ".scala": "scala",
    ".groovy": "groovy",
    ".gradle": "groovy",
    ".xml": "xml",
    ".svg": "xml",
    ".csv": "csv",
    ".tsv": "csv",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".properties": "ini",
    ".env": "ini",
    ".gitignore": "ini",
    ".dockerignore": "ini",
    ".gitattributes": "ini",
    ".gitmodules": "ini",
    ".gitconfig": "ini",
    ".gitkeep": "ini",
    ".git": "ini",
    ".hgignore": "ini",
    ".hg": "ini",
    ".npmignore": "ini",
    ".yarnignore": "ini",
    ".editorconfig": "ini",
    ".babelrc": "json",
    ".eslintrc": "json",
    ".prettierrc": "json",
    ".prettierignore": "json",
    ".babelignore": "json",
    ".flowconfig": "ini",
    ".eslintignore": "ini",
    ".eslintcache": "json",
    ".babelcache": "json",
    ".prettiercache": "json",
    ".prettier": "json",
    ".babel": "json",
    ".eslint": "json",
    ".flow": "json",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".proto": "protobuf",
    ".asciidoc": "asciidoc",
    ".adoc": "asciidoc",
    ".ad": "asciidoc",
    ".asc": "asciidoc",
    ".tex": "latex",
    ".latex": "latex",
    ".bib": "latex",
    ".ltx": "latex",
    ".sty": "latex",
    ".cls": "latex",
    ".dtx": "latex",
    ".ins": "latex",
    ".mk": "makefile",
    ".makefile": "makefile",
    ".make": "makefile",
    ".mkfile": "makefile",
    ".mkfile": "makefile",
    ".mk": "makefile",
    ".ninja": "ninja",
    ".gn": "ninja",
    ".gninja": "ninja",
    ".ninja": "ninja",
    ".gninja": "ninja",
    ".cmake": "cmake",
    ".cmake.in": "cmake",
    ".cmakecache": "cmmake",
    ".pl": "perl",
    ".pm": "perl",
    ".t": "perl",
    ".pod": "perl",
    ".cgi": "perl",
    ".po": "gettext",
    ".pot": "gettext",
    ".mo": "gettext",
    ".cs": "csharp",
    ".csproj": "xml",
    ".sln": "xml",
    ".fs": "fsharp",
    ".fsproj": "xml",
    ".fsi": "fsharp",
    ".fsx": "fsharp",
    ".fsi": "fsharp",
    ".dsw": "xml",
    ".dsp": "xml",
    ".vbs": "vbscript",
    ".vba": "vbscript",
    ".vbe": "vbscript",
    ".vb": "vbscript",
    ".vbscript": "vbscript",
    ".jse": "javascript",
    ".vbe": "vbscript",
    ".wsf": "xml",
    ".bashrc": "bash",
    ".zshrc": "bash",
    ".fishrc": "fish",
    ".bash_profile": "bash",
    ".bash_aliases": "bash",
    ".bash_functions": "bash",
    ".bash_logout": "bash",
    ".bash_history": "bash",
    ".bash_login": "bash",
    ".vimrc": "vim",
    ".vim": "vim",
    ".gvimrc": "vim",
    ".nvim": "vim",
    ".nvimrc": "vim",
    ".env": "ini",
    ".envrc": "ini",
    ".env.example": "ini",
    ".envrc.example": "ini",
    ".env.sample": "ini",
    ".envrc.sample": "ini",
    ".env.local": "ini",
    ".envrc.local": "ini",
    ".env.dev": "ini",
    ".swift": "swift",
    ".swiftui": "swift",
    ".swiftplayground": "swift",
    ".swiftmodule": "swift",
    ".swiftsource": "swift",
    ".el": "lisp",
    ".erlang": "erlang",
    ".hrl": "erlang",
    ".es": "erlang",
    ".escript": "erlang",
    ".haskell": "haskell",
    ".hs": "haskell",
    ".lhs": "haskell",
    ".cabal": "haskell",
    ".hie": "haskell",
    ".cargo": "rust",
    ".pem": "text",
    ".asc": "text",
    ".crt": "text",
    ".csr": "text",
    ".key": "text",
    ".htaccess": "apache",
}
