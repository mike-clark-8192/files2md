# Plan: Add Line Numbers to Table of Contents

## Overview
Add start and end line numbers to each file entry in the TOC, showing where that file's content appears in the generated markdown document.

## Current Implementation

### Current Flow
1. `MdWriter.make_md()` generates header with TOC via `mdfmt.make_header_md()`
2. Header is immediately written to output via `output_handler.write(header)` (line 269)
3. Files are processed in a loop and written incrementally to output (lines 271-283)

### Key Files
- `src/files2md/cli/cli_impl.py`: Entry point, calls `MdWriter`
- `src/files2md/md_transform.py`: Contains `MdWriter` and `MdFormatter` classes

### Current TOC Format
```markdown
## File listing:
`project/file1.py`
`project/file2.js`
`project/dir/file3.md`
```

## Problem
The TOC is written before we know the line numbers where each file's content will appear in the document.

## Solution Approach

### Two-Pass Strategy
1. **First pass**: Generate all content in memory, track line numbers for each file
2. **Second pass**: Generate TOC with line numbers, write everything to disk

This works because:
- User confirmed all output should fit in memory
- We can accumulate content, calculate positions, then write in correct order

## Implementation Plan

### 1. Create Data Structures

Add a dataclass to track file positions:
```python
@dataclass
class FilePosition:
    path_desc: str          # e.g., "project/file.py"
    start_line: int         # First line of content
    end_line: int           # Last line of content
    content: str            # Generated markdown for this file
```

### 2. Modify `MdWriter.make_md()`

**Current behavior**: Writes header immediately, then writes files incrementally

**New behavior**:
```python
def make_md(self):
    # Step 1: Generate header WITHOUT file listing
    header_prefix = self.mdfmt.make_header_prefix(self.project_name)

    # Step 2: Generate all file content in memory, track positions
    file_positions: list[FilePosition] = []
    current_line = count_lines(header_prefix) + count_lines(TOC_PLACEHOLDER)

    for file in sorted(files):
        pathdesc = path_descs[file]
        mdstr, truncated, excluded = self.mdfmt.file_to_md(file, pathdesc)

        start_line = current_line + 1
        line_count = count_lines(mdstr)
        end_line = current_line + line_count

        file_positions.append(FilePosition(
            path_desc=pathdesc,
            start_line=start_line,
            end_line=end_line,
            content=mdstr
        ))

        current_line = end_line

    # Step 3: Generate TOC with line numbers
    toc = self.mdfmt.make_files_listing_with_lines(file_positions)
    header = header_prefix + toc + "\n## Filenames and content:\n"

    # Step 4: Write everything to output
    self.output_handler.write(header)
    self.output_handler.on_after_md_header()

    for file_pos in file_positions:
        self.output_handler.write(file_pos.content)
        self.output_handler.on_after_md_section()
```

### 3. Modify `MdFormatter` Methods

**Split `make_header_md()` into two methods**:

```python
def make_header_prefix(self, project_name: str) -> str:
    """Generate the header without the file listing TOC"""
    parts = [
        TEMPLATE_PROJECT.substitute(project_name=project_name),
        TEMPLATE_GENERATOR_TAG.substitute(files2md_version=files2md.__version__),
    ]
    return "\n".join(parts) + "\n"

def make_files_listing_with_lines(self, file_positions: list[FilePosition]) -> str:
    """Generate TOC with line numbers for each file"""
    files_lines = []
    for fp in file_positions:
        # Format: `filename` (lines 10-50)
        files_lines.append(f"`{fp.path_desc}` (lines {fp.start_line}-{fp.end_line})")

    files_listing = "\n".join(files_lines)
    return TEMPLATE_FILELIST.substitute(files_listing=files_listing)
```

### 4. Utility Function

```python
def count_lines(text: str) -> int:
    """Count the number of newline characters in text"""
    if not text:
        return 0
    return text.count('\n')
```

### 5. Handle Split File Mode

For split files (`SplitFileOutputHandler`):
- Each split file would have its own TOC with line numbers relative to that split
- OR disable this feature for split mode (simpler)
- Need to decide which approach

## Questions for User

1. **TOC Format**: What format do you prefer for the line numbers?
   - Option A: `` `filename` (lines 10-50) ``
   - Option B: `` `filename` [10-50] ``
   - Option C: `` `filename` :: 10-50 ``
   - Other?

2. **Line Numbering**: Should we count from line 1 or line 0?
   - Most text editors use 1-based numbering
   - Recommendation: Use 1-based (line 1 is the first line)

3. **Split File Mode**: Should this feature apply to split-file output mode?
   - If yes: Each split file gets its own TOC with relative line numbers
   - If no: Only apply to single-file mode (simpler implementation)
   - Recommendation: Start with single-file only, add split-file support later if needed

4. **Line Counting**: Should we count:
   - Only the content lines (between the fence markers)?
   - All lines including the file header `### filename` and fence markers?
   - Recommendation: Count all lines for the file's section (header + fences + content)

## Testing Strategy

1. Create a test with a few small files
2. Verify line numbers in TOC match actual positions in output
3. Test with empty files
4. Test with truncated files (max-lines-per-file)
5. Test with binary files (excluded content)

## Edge Cases

1. **Empty files**: Still get an entry in TOC with line numbers
2. **Binary files**: Only header line, still counted
3. **Files with excluded content**: Count the exclusion message lines
4. **Very first file**: Starts right after "## Filenames and content:" header

## Implementation Order

1. Add `FilePosition` dataclass
2. Add `count_lines()` utility
3. Split `make_header_md()` into `make_header_prefix()` and `make_files_listing_with_lines()`
4. Modify `MdWriter.make_md()` to use two-pass approach
5. Test with sample files
6. Handle edge cases
7. Update documentation
