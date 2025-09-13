#!/usr/bin/env python3
"""
write_to_file.py

Scan a UTF-8 markdown file for <write_to_file> blocks, extract <path> and <content>,
and write the content to the specified path. Includes path safety validation,
atomic writes, enhanced error context, and optional backups.

Usage:
  python3 write_to_file.py response.md [--dry-run] [--base-dir DIR] [--verbose] [--backup]
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

OPEN_BLOCK = "<write_to_file>"
CLOSE_BLOCK = "</write_to_file>"
OPEN_PATH = "<path>"
CLOSE_PATH = "</path>"
OPEN_CONTENT = "<content>"
CLOSE_CONTENT = "</content>"


class ParseError(Exception):
    def __init__(self, message: str, line: int | None = None, context: str | None = None):
        super().__init__(message)
        self.line = line
        self.context = context

    def __str__(self) -> str:
        result = super().__str__()
        if self.line is not None:
            result += f" (line {self.line})"
        if self.context:
            result += f"\nContext: {self.context.rstrip()}"
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract <write_to_file> blocks and write files.")
    parser.add_argument("markdown_file", help="Path to the markdown file (UTF-8).")
    parser.add_argument("--dry-run", action="store_true", help="Report actions without writing files.")
    parser.add_argument("--base-dir", type=str, default=None,
                        help="Base directory to resolve and confine <path> entries.")
    parser.add_argument("--backup", action="store_true",
                        help="Create a timestamped backup before overwriting existing files.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose diagnostics.")
    return parser.parse_args()


def validate_utf8(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="strict", newline=None) as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise ParseError(f"Input file is not valid UTF-8: {e}")
    except FileNotFoundError:
        raise ParseError(f"Input file not found: {path}")
    except OSError as e:
        raise ParseError(f"Failed to read input file: {e}")


def find_tag_inline(line: str, open_tag: str, close_tag: str) -> Optional[Tuple[str, str, str]]:
    """
    If line contains <tag>...</tag> inline, return (before, inside, after); else None.
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


def parse_blocks(lines: List[str], verbose: bool = False) -> List[dict]:
    blocks: List[dict] = []

    i = 0
    n = len(lines)

    inside_block = False
    path_collecting = False
    content_collecting = False

    current_block: dict = {}
    current_path_parts: List[str] = []
    current_content_parts: List[str] = []
    block_start_line = -1

    while i < n:
        raw_line = lines[i]
        stripped = raw_line.strip()

        if not inside_block:
            if stripped == OPEN_BLOCK:
                inside_block = True
                current_block = {"path": None, "contents": []}
                current_path_parts = []
                current_content_parts = []
                path_collecting = False
                content_collecting = False
                block_start_line = i + 1  # 1-based
                if verbose:
                    print(f"[parse] Enter block at line {block_start_line}", file=sys.stderr)
            elif OPEN_BLOCK in stripped and stripped != OPEN_BLOCK:
                raise ParseError("Malformed block opening", line=i + 1, context=raw_line)
            i += 1
            continue

        # inside a block
        if stripped == CLOSE_BLOCK:
            if path_collecting or content_collecting:
                raise ParseError("Unclosed tag before </write_to_file>", line=i + 1, context=raw_line)
            if current_block.get("path") is None:
                raise ParseError("Missing <path> in block", line=block_start_line)
            if not current_block["contents"]:
                raise ParseError("Missing <content> in block", line=block_start_line)
            blocks.append(current_block)
            inside_block = False
            if verbose:
                print(f"[parse] Exit block at line {i+1}", file=sys.stderr)
            i += 1
            continue

        if stripped == OPEN_BLOCK:
            raise ParseError("Nested <write_to_file> not supported", line=i + 1, context=raw_line)

        # Path handling
        if not path_collecting and current_block.get("path") is None:
            inline = find_tag_inline(raw_line, OPEN_PATH, CLOSE_PATH)
            if inline is not None:
                _, inside, _ = inline
                current_block["path"] = inside.strip()
                i += 1
                continue
            if stripped == OPEN_PATH:
                path_collecting = True
                current_path_parts = []
                i += 1
                continue

        if path_collecting:
            close_idx = raw_line.find(CLOSE_PATH)
            if close_idx != -1:
                current_path_parts.append(raw_line[:close_idx])
                path_text = "".join(current_path_parts).strip()
                current_block["path"] = path_text
                path_collecting = False
                i += 1
                continue
            else:
                current_path_parts.append(raw_line)
                i += 1
                continue

        # Content handling
        inline = find_tag_inline(raw_line, OPEN_CONTENT, CLOSE_CONTENT)
        if inline is not None:
            _, inside, _ = inline
            current_block["contents"].append(inside)
            i += 1
            continue

        if stripped == OPEN_CONTENT:
            content_collecting = True
            current_content_parts = []
            i += 1
            continue

        if content_collecting:
            close_idx = raw_line.find(CLOSE_CONTENT)
            if close_idx != -1:
                current_content_parts.append(raw_line[:close_idx])
                content_text = "".join(current_content_parts)
                current_block["contents"].append(content_text)
                content_collecting = False
                i += 1
                continue
            else:
                current_content_parts.append(raw_line)
                i += 1
                continue

        # Ignore other lines within a block
        i += 1

    if inside_block:
        raise ParseError("Unclosed <write_to_file> block", line=block_start_line)

    return blocks


def resolve_target_path(path_text: str, base_dir: Optional[Path]) -> Path:
    """
    Resolve a target path, applying base_dir for relative paths when provided,
    and enforcing path safety constraints.
    """
    p = Path(path_text.strip())

    # Absolute path policy
    if p.is_absolute():
        if base_dir is None:
            raise ParseError(f"Absolute paths require --base-dir: '{p}'")
        # If absolute, still ensure it's within base_dir
        resolved = p.resolve()
        base_resolved = base_dir.resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ParseError(f"Path '{p}' escapes base directory '{base_dir}'")
        return resolved

    # Relative path
    if base_dir is not None:
        resolved = (base_dir / p).resolve()
        base_resolved = base_dir.resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError:
            raise ParseError(f"Path '{p}' escapes base directory '{base_dir}'")
        return resolved

    # No base_dir: allow relative paths (resolved against CWD)
    return p.resolve()


def create_backup(path: Path) -> Optional[Path]:
    """
    Create a timestamped backup of an existing file. Returns backup path, or None if not existing.
    """
    if path.exists():
        ts = int(time.time())
        backup_name = f"{path.name}.backup.{ts}"
        backup_path = path.with_name(backup_name)
        shutil.copy2(path, backup_path)
        return backup_path
    return None


def atomic_write(path: Path, content: str) -> None:
    """
    Write file atomically in the same directory to prevent partial writes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # Place temporary file in the same directory for atomic rename
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(path.parent),
        delete=False,
        newline="\n",
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name
    # Atomic replace (POSIX/Windows)
    os.replace(temp_name, path)


def write_outputs(
    blocks: List[dict],
    base_dir: Optional[Path],
    dry_run: bool,
    verbose: bool,
    backup: bool,
) -> Tuple[int, List[str]]:
    errors = 0
    results: List[str] = []

    for idx, blk in enumerate(blocks, start=1):
        path_text = blk["path"]
        try:
            dest_path = resolve_target_path(path_text, base_dir)
        except ParseError as e:
            print(f"[error] {e}", file=sys.stderr)
            errors += 1
            continue

        # Concatenate multiple contents in order with a single newline between segments
        contents: List[str] = blk["contents"]
        payload = "\n".join(contents) if len(contents) > 1 else contents[0]

        if verbose or dry_run:
            print(f"[plan] File {idx}: {dest_path}", file=sys.stderr)
            print(f"[plan] Size: {len(payload)} chars", file=sys.stderr)
            if backup and dest_path.exists():
                simulated_backup = dest_path.with_name(f"{dest_path.name}.backup.<timestamp>")
                print(f"[plan] Backup -> {simulated_backup}", file=sys.stderr)

        try:
            if not dry_run:
                if backup:
                    try:
                        create_backup(dest_path)
                    except OSError as e:
                        print(f"[warn] Failed to create backup for '{dest_path}': {e}", file=sys.stderr)
                atomic_write(dest_path, payload)
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
            try:
                resolved = resolve_target_path(blk["path"], base_dir)
                total_len = sum(len(x) for x in blk["contents"])
                print(f"[summary] #{i}: path='{resolved}' content_len={total_len}", file=sys.stderr)
            except ParseError as e:
                print(f"[summary-error] #{i}: {e}", file=sys.stderr)

    errors, results = write_outputs(
        blocks=blocks,
        base_dir=base_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
        backup=args.backup,
    )

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
