#!/usr/bin/env python3
"""Compatibility API for the native offline, report-only linter."""
from dataclasses import asdict, dataclass
try:
    from ._native import ROOT, call, main as native_main
except ImportError:
    from _native import ROOT, call, main as native_main

TOOL_VERSION = '0.2.0'
CHECKS = ('protected', 'values', 'identifiers', 'negation', 'uncertainty', 'conditions', 'subject', 'terminology')

@dataclass(frozen=True)
class Token:
    start: int
    end: int
    text: str
    kind: str


def tokens(pattern, text, kind):
    return [Token(**item) for item in call('tokens', pattern, text, kind)]


def protected(text):
    return [Token(**item) for item in call('protected', text)]


def mask(text, spans):
    return call('mask', text, [asdict(item) for item in spans])


def location(text, token):
    return call('location', text, asdict(token) if token else None)


def validate_term_config(data):
    return call('validate_term_config', data)


def review(source, candidate, term_config=None):
    return call('review', source, candidate, term_config)


def main(argv=None):
    return native_main('lint', argv)


if __name__ == '__main__':
    raise SystemExit(main())
