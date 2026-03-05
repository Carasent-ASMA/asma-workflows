#!/usr/bin/env python3
"""Extract structural AST context from a git diff using tree-sitter.

Parses ONLY the changed files, finds which functions/methods/classes overlap
with the modified line ranges, and outputs a Unicode-tree summary with:
  - symbol signatures (no bodies)
  - JSDoc / doc comments
  - outgoing calls  (→)
  - incoming callers (←)

Dependencies (optional — degrades gracefully):
    pip install tree-sitter tree-sitter-typescript tree-sitter-javascript \
        tree-sitter-python tree-sitter-c-sharp tree-sitter-sql tree-sitter-yaml
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol, cast


class TSNodeProtocol(Protocol):
    type: str
    text: bytes | str
    children: list[TSNodeProtocol]
    named_children: list[TSNodeProtocol]
    prev_named_sibling: TSNodeProtocol | None
    start_point: tuple[int, int]
    end_point: tuple[int, int]

    def child_by_field_name(self, name: str) -> TSNodeProtocol | None: ...


class TSTreeProtocol(Protocol):
    root_node: TSNodeProtocol


class TSParserProtocol(Protocol):
    def parse(self, source: bytes) -> TSTreeProtocol: ...

# ── Lazy tree-sitter loading ─────────────────────────────────────────────────

_ts_available = False
LanguageFactory: Callable[[object], object] | None = None
ParserFactory: Callable[[object], TSParserProtocol] | None = None
try:
    from tree_sitter import Language, Parser  # type: ignore[import-untyped]

    LanguageFactory = cast(Callable[[object], object], Language)
    ParserFactory = cast(Callable[[object], TSParserProtocol], Parser)
    _ts_available = True
except ImportError:
    LanguageFactory = None
    ParserFactory = None

_languages: dict[str, object] = {}
_LANGUAGE_BY_EXT: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".cs": "csharp",
    ".sql": "sql",
    ".pgsql": "sql",
    ".mssql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _safe_module_language(module: object, attr: str) -> object | None:
    """Build a tree-sitter Language instance from a module function."""
    if LanguageFactory is None:
        return None
    fn_obj = getattr(module, attr, None)
    if fn_obj is None or not callable(fn_obj):
        return None
    language_fn = cast(Callable[[], object], fn_obj)
    return LanguageFactory(language_fn())


def _get_language(ext: str) -> object | None:
    """Return the tree-sitter Language for a file extension, or None."""
    if not _ts_available or LanguageFactory is None:
        return None
    family = _LANGUAGE_BY_EXT.get(ext)
    if family is None:
        return None
    if ext in _languages:
        return _languages[ext]

    lang: object | None = None
    try:
        if family == "typescript":
            import tree_sitter_typescript as tsts  # type: ignore[import-untyped]

            attr = "language_tsx" if ext == ".tsx" else "language_typescript"
            lang = _safe_module_language(tsts, attr)
        elif family == "javascript":
            import tree_sitter_javascript as tsjs  # type: ignore[import-untyped]

            lang = _safe_module_language(tsjs, "language")
        elif family == "python":
            import tree_sitter_python as tspy  # type: ignore[import-untyped]

            lang = _safe_module_language(tspy, "language")
        elif family == "csharp":
            import tree_sitter_c_sharp as tscs  # type: ignore[import-untyped]

            lang = _safe_module_language(tscs, "language")
        elif family == "sql":
            import tree_sitter_sql as tssql  # type: ignore[import-untyped]

            lang = _safe_module_language(tssql, "language")
        elif family == "yaml":
            import tree_sitter_yaml as tsyaml  # type: ignore[import-untyped]

            lang = _safe_module_language(tsyaml, "language")
    except Exception:
        pass

    if lang is not None:
        _languages[ext] = lang
    return lang


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Symbol:
    kind: str  # function | method | class | interface | type
    name: str
    signature: str  # everything before the body
    doc: str  # JSDoc or line comment above
    line: int  # 1-based start
    end_line: int  # 1-based end
    exported: bool
    calls: list[str] = field(default_factory=list[str])
    called_by: list[str] = field(default_factory=list[str])


# ── Git diff → changed line ranges ───────────────────────────────────────────

_HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _diff_line_ranges(commit_range: str, filepath: str) -> list[tuple[int, int]]:
    """Return list of (start, end) 1-based line ranges changed in *filepath*."""
    result = subprocess.run(
        ["git", "diff", "-U0", commit_range, "--", filepath],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    ranges: list[tuple[int, int]] = []
    for line in result.stdout.splitlines():
        m = _HUNK_RE.match(line)
        if m:
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) else 1
            if count > 0:
                ranges.append((start, start + count - 1))
    return ranges


def _overlaps(sym_start: int, sym_end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(sym_start <= r_end and sym_end >= r_start for r_start, r_end in ranges)


# ── AST helpers ───────────────────────────────────────────────────────────────

_DECL_TYPES_BY_FAMILY: dict[str, frozenset[str]] = {
    "typescript": frozenset(
        {
            "function_declaration",
            "generator_function_declaration",
            "method_definition",
            "class_declaration",
            "interface_declaration",
            "type_alias_declaration",
            "abstract_class_declaration",
        }
    ),
    "javascript": frozenset(
        {
            "function_declaration",
            "generator_function_declaration",
            "method_definition",
            "class_declaration",
        }
    ),
    "python": frozenset({"function_definition", "class_definition"}),
    "csharp": frozenset(
        {
            "class_declaration",
            "struct_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
            "method_declaration",
            "constructor_declaration",
            "property_declaration",
        }
    ),
    "sql": frozenset(
        {
            "create_function_statement",
            "create_procedure_statement",
            "create_view_statement",
            "create_table_statement",
            "create_type_statement",
            "create_trigger_statement",
            "create_index_statement",
        }
    ),
}
_ARROW_TYPES = frozenset({"arrow_function", "function_expression", "generator_function"})
_BODY_TYPES_BY_FAMILY: dict[str, frozenset[str]] = {
    "typescript": frozenset({"statement_block", "class_body", "object_type", "interface_body"}),
    "javascript": frozenset({"statement_block", "class_body"}),
    "python": frozenset({"block"}),
    "csharp": frozenset({"block", "accessor_list", "declaration_list"}),
    "sql": frozenset(),
    "yaml": frozenset(),
}
_KIND_MAP_BY_FAMILY: dict[str, dict[str, str]] = {
    "typescript": {
        "function_declaration": "function",
        "generator_function_declaration": "function",
        "method_definition": "method",
        "class_declaration": "class",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "abstract_class_declaration": "class",
    },
    "javascript": {
        "function_declaration": "function",
        "generator_function_declaration": "function",
        "method_definition": "method",
        "class_declaration": "class",
    },
    "python": {
        "function_definition": "function",
        "class_definition": "class",
    },
    "csharp": {
        "class_declaration": "class",
        "struct_declaration": "struct",
        "interface_declaration": "interface",
        "enum_declaration": "enum",
        "record_declaration": "record",
        "method_declaration": "method",
        "constructor_declaration": "constructor",
        "property_declaration": "property",
    },
    "sql": {
        "create_function_statement": "function",
        "create_procedure_statement": "procedure",
        "create_view_statement": "view",
        "create_table_statement": "table",
        "create_type_statement": "type",
        "create_trigger_statement": "trigger",
        "create_index_statement": "index",
    },
    "yaml": {},
}
_CALL_TYPES_BY_FAMILY: dict[str, frozenset[str]] = {
    "typescript": frozenset({"call_expression"}),
    "javascript": frozenset({"call_expression"}),
    "python": frozenset({"call"}),
    "csharp": frozenset({"invocation_expression"}),
    "sql": frozenset({"function_call"}),
    "yaml": frozenset(),
}
_CALL_FIELDS_BY_FAMILY: dict[str, tuple[str, ...]] = {
    "typescript": ("function",),
    "javascript": ("function",),
    "python": ("function",),
    "csharp": ("expression",),
    "sql": ("function", "name"),
    "yaml": (),
}


def _node_text(node: TSNodeProtocol) -> str:
    raw = node.text
    return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)


def _preceding_comment(node: TSNodeProtocol, source_lines: list[str]) -> str:
    """Grab the JSDoc or //‑comment block immediately above *node*."""
    prev = node.prev_named_sibling
    if prev is not None and prev.type == "comment":
        return _node_text(prev).strip()
    start: int = node.start_point[0]
    if start <= 0:
        return ""
    above: str = source_lines[start - 1].strip()
    if not (
        above.startswith("//")
        or above.startswith("#")
        or above.startswith("--")
        or above.endswith("*/")
    ):
        return ""
    lines: list[str] = []
    ln: str = ""
    i: int = start - 1
    while i >= 0:
        ln = source_lines[i].strip()
        if (
            ln.startswith("//")
            or ln.startswith("#")
            or ln.startswith("--")
            or ln.startswith("*")
            or ln.startswith("/*")
        ):
            lines.insert(0, ln)
            if ln.startswith("/*"):
                break
            i -= 1
        else:
            break
    return "\n".join(lines)


def _extract_signature(
    node: TSNodeProtocol,
    source_lines: list[str],
    body_types: frozenset[str],
) -> str:
    """Return the signature WITHOUT the body (e.g. no { … })."""
    start: int = node.start_point[0]
    body: TSNodeProtocol | None = next(
        (c for c in node.children if c.type in body_types),
        None,
    )
    if body:
        end: int = body.start_point[0]
        col: int = body.start_point[1]
        sig_lines = source_lines[start : end + 1]
        if sig_lines:
            sig_lines[-1] = sig_lines[-1][:col].rstrip()
        return "\n".join(ln.rstrip() for ln in sig_lines).rstrip(" {").strip()
    return source_lines[start].strip() if start < len(source_lines) else ""


def _extract_calls(
    node: TSNodeProtocol,
    call_types: frozenset[str],
    call_fields: tuple[str, ...],
) -> list[str]:
    """Collect unique callee names (simplified) inside *node*."""
    calls: set[str] = set()

    def _walk(n: TSNodeProtocol) -> None:
        if n.type in call_types:
            fn: TSNodeProtocol | None = None
            for field in call_fields:
                fn = n.child_by_field_name(field)
                if fn is not None:
                    break
            if fn is None and n.named_children:
                fn = n.named_children[0]
            if fn:
                name = _node_text(fn).split("(")[0].strip()
                if 0 < len(name) < 80:
                    calls.add(name)
        for child in n.children:
            _walk(child)

    _walk(node)
    return sorted(calls)


def _parse_yaml_symbols(source: str, tree: TSTreeProtocol) -> list[Symbol]:
    """Extract YAML key symbols for config diffs (Hasura and other services)."""
    lines = source.splitlines()
    symbols: list[Symbol] = []
    pair_types = frozenset({"block_mapping_pair", "flow_pair"})

    def _walk(node: TSNodeProtocol) -> None:
        if node.type in pair_types:
            key = node.child_by_field_name("key")
            key_text = _node_text(key).strip() if key else "?"
            symbols.append(
                Symbol(
                    kind="key",
                    name=key_text,
                    signature=f"key {key_text}",
                    doc=_preceding_comment(node, lines),
                    line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    exported=False,
                )
            )
        for child in node.named_children:
            _walk(child)

    _walk(tree.root_node)
    return symbols


def _parse_symbols(source: str, language: object, family: str) -> list[Symbol]:
    """Parse *source* and return all top-level symbols."""
    if ParserFactory is None:
        return []
    parser = ParserFactory(language)
    tree = parser.parse(source.encode("utf-8"))

    if family == "yaml":
        return _parse_yaml_symbols(source, tree)

    lines = source.splitlines()
    symbols: list[Symbol] = []
    decl_types = _DECL_TYPES_BY_FAMILY.get(family, frozenset())
    body_types = _BODY_TYPES_BY_FAMILY.get(family, frozenset())
    kind_map = _KIND_MAP_BY_FAMILY.get(family, {})
    call_types = _CALL_TYPES_BY_FAMILY.get(family, frozenset())
    call_fields = _CALL_FIELDS_BY_FAMILY.get(family, tuple())

    def _process(node: TSNodeProtocol, exported: bool = False) -> None:
        if family in ("typescript", "javascript") and node.type == "export_statement":
            for child in node.named_children:
                _process(child, exported=True)
            return

        if family == "python" and node.type == "decorated_definition":
            for child in node.named_children:
                _process(child, exported=exported)
            return

        if node.type in decl_types:
            name_node = node.child_by_field_name("name")
            name = _node_text(name_node) if name_node else "?"
            symbols.append(
                Symbol(
                    kind=kind_map.get(node.type, node.type) or "unknown",
                    name=name,
                    signature=_extract_signature(node, lines, body_types),
                    doc=_preceding_comment(node, lines),
                    line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    exported=exported,
                    calls=_extract_calls(node, call_types, call_fields),
                )
            )
            # Recurse into class body for methods
            if node.type in (
                "class_declaration",
                "abstract_class_declaration",
                "struct_declaration",
                "record_declaration",
            ):
                for child in node.named_children:
                    if child.type in ("class_body", "declaration_list"):
                        for member in child.named_children:
                            _process(member, exported=exported)
            return

        # const foo = () => {} / const foo = function() {}
        if family in ("typescript", "javascript") and node.type == "lexical_declaration":
            for decl in node.named_children:
                if decl.type == "variable_declarator":
                    val = decl.child_by_field_name("value")
                    if val and val.type in _ARROW_TYPES:
                        nm = decl.child_by_field_name("name")
                        symbols.append(
                            Symbol(
                                kind="function",
                                name=_node_text(nm) if nm else "?",
                                signature=_extract_signature(node, lines, body_types),
                                doc=_preceding_comment(node, lines),
                                line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                                exported=exported,
                                calls=_extract_calls(val, call_types, call_fields),
                            )
                        )

    root_children = tree.root_node.children
    for child in root_children:
        _process(child)

    return symbols


# ── Tree formatter ────────────────────────────────────────────────────────────


def _format_tree(filepath: str, symbols: list[Symbol]) -> str:
    out = [filepath]
    for i, sym in enumerate(symbols):
        last = i == len(symbols) - 1
        pfx = "└── " if last else "├── "
        cnt = "    " if last else "│   "

        exp = "export " if sym.exported else ""
        sig = sym.signature
        # The signature already contains keywords like "export", "async", "function"
        # so just use the raw signature without prepending kind
        if sig.startswith("export ") or sig.startswith("async ") or any(
            sig.startswith(k) for k in ("function ", "class ", "interface ", "type ")
        ):
            out.append(f"{pfx}{sig}")
        else:
            out.append(f"{pfx}{exp}{sym.kind} {sig}")

        if sym.doc:
            first_line = sym.doc.split("\n")[0][:120]
            out.append(f"{cnt}📝 {first_line}")
        if sym.calls:
            names = ", ".join(sym.calls[:8])
            if len(sym.calls) > 8:
                names += f" … +{len(sym.calls) - 8}"
            out.append(f"{cnt}→ calls: {names}")
        if sym.called_by:
            out.append(f"{cnt}← called by: {', '.join(sym.called_by[:5])}")

    return "\n".join(out)


# ── Public API ────────────────────────────────────────────────────────────────


def extract_diff_ast(commit_range: str, changed_files: list[str]) -> str:
    """Return a tree-formatted AST summary of symbols touched by the diff.

    Gracefully returns ``""`` when tree-sitter is not installed.
    """
    if not _ts_available:
        return ""

    sections: list[str] = []

    for filepath in changed_files:
        ext = Path(filepath).suffix.lower()
        family = _LANGUAGE_BY_EXT.get(ext)
        if family is None:
            continue
        language = _get_language(ext)
        if language is None:
            continue

        p = Path(filepath)
        if not p.exists():
            continue
        source = p.read_text(encoding="utf-8", errors="replace")

        ranges = _diff_line_ranges(commit_range, filepath)
        if not ranges:
            continue

        all_symbols = _parse_symbols(source, language, family)
        if not all_symbols:
            continue

        changed = [s for s in all_symbols if _overlaps(s.line, s.end_line, ranges)]
        if not changed:
            continue

        # Resolve incoming call edges from the full file
        for sym in all_symbols:
            for call_name in sym.calls:
                base = call_name.split(".")[-1]
                for target in changed:
                    if target.name == base and sym.name not in target.called_by:
                        target.called_by.append(sym.name)

        sections.append(_format_tree(filepath, changed))

    return "\n\n".join(sections)
