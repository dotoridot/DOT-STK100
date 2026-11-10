#!/usr/bin/env python3
"""Compatibility API for the native rule table renderer."""
try:
    from ._native import call, main as native_main
except ImportError:
    from _native import call, main as native_main

START = '<!-- BEGIN GENERATED RULES -->'
END = '<!-- END GENERATED RULES -->'


def cell(value):
    return call('cell', value)


def render_table(rules):
    return call('render_table', rules)


def render_document(text, rules):
    return call('render_document', text, rules)


def main(argv=None):
    return native_main('render', argv)


if __name__ == '__main__':
    raise SystemExit(main())
