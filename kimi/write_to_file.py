#!/usr/bin/env python3
"""
write_to_file.py

Scan a UTF-8 markdown file for <write_to_file> blocks, extract <path> and <content>,
and write the content to the specified path. Supports multiple blocks, inline tags,
and multi-line content.

Usage:
  python3 write_to_file.py response.md [--dry-run] [--base-dir DIR] [--verbose]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple


OPEN_BLOCK = "<write_to_file>"
CLOSE_BLOCK = "</write_to_file>"
OPEN_PATH = "<path>"
CLOSE_PATH = "</path>"
OPEN_CONTENT = "<content>"
CLOSE_CONTENT = "</content>"


class ParseError(Exception):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract <write_to_file> blocks and write files.")
    parser.add_argument("markdown_file", help="Path to the markdown file (UTF-8).")
    parser.add_argument("--dry-run", action="store_true", help="Report actions without writing files.")
    parser.add_argument("--base-dir", type=str, default=None,
                        help="Base directory to resolve relative <path> entries.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose diagnostics.")
    return parser.parse_args()


def validate_utf8(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="strict", newline=None) as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise ParseError(f"Input file is not valid UTF-8: {e}") from e
    except FileNotFoundError:
        raise ParseError(f"Input file not found: {path}")
    except OSError as e:
        raise ParseError(f"Failed to read input file: {e}") from e


def find_tag_inline(line: str, open_tag: str, close_tag: str) -> Optional[Tuple[str, str]]:
    """
    If line contains <tag>... </tag> inline, return (before, inside, after).
    If only opening is present without closing, return None.
    """
    start = line.find(open_tag)
    if start == -1:
        return None
    end = line.find(close_tag, start + len(open_tag))
    if end == -1:
        return None
    inside = line[start + len(open_tag):end]
    before = line[:start]
    after = line[end + len(close_tag):]
    return before, inside, after


def normalize_path(p: str, base_dir: Optional[Path]) -> Path:
    raw = Path(p.strip())
    if not raw.is_absolute() and base_dir is not None:
        return (base_dir / raw).resolve()
    return raw.resolve()


def parse_blocks(lines: List[str], verbose: bool = False) -> List[dict]:
    blocks: List[dict] = []
    i = 0
    n = len(lines)

    inside_block = False
    path_collecting = False
    content_collecting = False

    current_block = {}
    current_path_parts: List[str] = []
    current_content_parts: List[str] = []
    block_start_line = -1

    while i < n:
        raw_line = lines[i]
        line = raw_line.strip()

        if not inside_block:
            if line == OPEN_BLOCK:
                inside_block = True
                current_block = {"path": None, "contents": []}
                current_path_parts = []
                current_content_parts = []
                path_collecting = False
                content_collecting = False
                block_start_line = i + 1  # 1-based for user
                if verbose:
                    print(f"[parse] Enter block at line {block_start_line}", file=sys.stderr)
            elif OPEN_BLOCK in line and line != OPEN_BLOCK:
                # // Strict: block tag must be on its own line to avoid ambiguity
                raise ParseError(f"Malformed block opening at line {i+1}: '{raw_line.rstrip()}'")
            i += 1
            continue

        # inside_block == True
        if line == CLOSE_BLOCK:
            if path_collecting or content_collecting:
                raise ParseError(f"Unclosed tag before </write_to_file> at line {i+1}")
            # finalize block
            if current_block.get("path") is None:
                raise ParseError(f"Missing <path> in block starting at line {block_start_line}")
            if not current_block["contents"]:
                raise ParseError(f"Missing <content> in block starting at line {block_start_line}")
            blocks.append(current_block)
            inside_block = False
            if verbose:
                print(f"[parse] Exit block at line {i+1}", file=sys.stderr)
            i += 1
            continue

        # Prevent nested blocks
        if line == OPEN_BLOCK:
            raise ParseError(f"Nested <write_to_file> at line {i+1} is not supported")

        # Handle path
        if not path_collecting and current_block.get("path") is None:
            inline = find_tag_inline(raw_line, OPEN_PATH, CLOSE_PATH)
            if inline is not None:
                _, inside, _ = inline
                current_block["path"] = inside.strip()
                i += 1
                continue
            if line == OPEN_PATH:
                path_collecting = True
                current_path_parts = []
                i += 1
                continue

        if path_collecting:
            close_idx = raw_line.find(CLOSE_PATH)
            if close_idx != -1:
                # Collect up to close tag
                content_part = raw_line[:close_idx]
                current_path_parts.append(content_part)
                path_text = "".join(current_path_parts).strip()
                current_block["path"] = path_text
                path_collecting = False
                i += 1
                continue
            else:
                current_path_parts.append(raw_line)
                i += 1
                continue

        # Handle content
        inline = find_tag_inline(raw_line, OPEN_CONTENT, CLOSE_CONTENT)
        if inline is not None:
            _, inside, _ = inline
            # Inline content line: take inside exactly
            current_block["contents"].append(inside)
            i += 1
            continue

        if line == OPEN_CONTENT:
            content_collecting = True
            current_content_parts = []
            i += 1
            continue

        if content_collecting:
            close_idx = raw_line.find(CLOSE_CONTENT)
            if close_idx != -1:
                # Finish content, include all chars before close tag
                content_part = raw_line[:close_idx]
                current_content_parts.append(content_part)
                # Join with exact line breaks as in input
                content_text = "".join(current_content_parts)
                current_block["contents"].append(content_text)
                content_collecting = False
                i += 1
                continue
            else:
                current_content_parts.append(raw_line)
                i += 1
                continue

        # Any other line inside block is ignored (comments, spacing, etc.)
        i += 1

    if inside_block:
        raise ParseError(f"Unclosed <write_to_file> block starting at line {block_start_line}")

    return blocks


def write_outputs(blocks: List[dict], base_dir: Optional[Path], dry_run: bool, verbose: bool) -> Tuple[int, List[str]]:
    errors = 0
    results: List[str] = []

    for idx, blk in enumerate(blocks, start=1):
        dest_path = normalize_path(blk["path"], base_dir)
        # Concatenate multiple contents if present (in order)
        payload = "\n".join(blk["contents"]) if len(blk["contents"]) > 1 else blk["contents"][0]

        if verbose or dry_run:
            print(f"[plan] File {idx}: {dest_path}", file=sys.stderr)
            print(f"[plan] Size: {len(payload)} chars", file=sys.stderr)

        try:
            if not dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                # Write with UTF-8 and Unix newlines
                with dest_path.open("w", encoding="utf-8", newline="\n") as f:
                    f.write(payload)
            results.append(str(dest_path))
        except OSError as e:
            print(f"[error] Failed to write '{dest_path}': {e}", file=sys.stderr)
            errors += 1

    return errors, results


def main() -> int:
    args = parse_args()
    md_path = Path(args.markdown_file)
    base_dir = Path(args.base_dir).resolve() if args.base_dir else None

    try:
        text = validate_utf8(md_path)
    except ParseError as e:
        print(f"[fatal] {e}", file=sys.stderr)
        return 1

    lines = text.splitlines(keepends=True)

    try:
        blocks = parse_blocks(lines, verbose=args.verbose)
    except ParseError as e:
        print(f"[parse-error] {e}", file=sys.stderr)
        return 1

    if not blocks:
        print("[info] No <write_to_file> blocks found; nothing to do.", file=sys.stderr)
        return 0

    # Summarize planned actions
    if args.verbose or args.dry_run:
        for i, blk in enumerate(blocks, start=1):
            resolved = normalize_path(blk["path"], base_dir)
            total_len = sum(len(x) for x in blk["contents"])
            print(f"[summary] #{i}: path='{resolved}' content_len={total_len}", file=sys.stderr)

    errors, results = write_outputs(blocks, base_dir, args.dry_run, args.verbose)

    if args.dry_run:
        print("[dry-run] Skipped writing files. Planned outputs:", file=sys.stderr)
        for r in results:
            print(f" - {r}", file=sys.stderr)

    if errors:
        print(f"[done] Completed with {errors} error(s).", file=sys.stderr)
        return 2

    print(f"[done] Wrote {len(results)} file(s).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
