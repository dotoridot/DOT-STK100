#!/usr/bin/env python3
"""Compatibility API for native provisional warning triage."""
try:
    from ._native import ROOT, call, main as native_main
except ImportError:
    from _native import ROOT, call, main as native_main


def evaluate(cases):
    return call('evaluate', cases)


def main(argv=None):
    return native_main('evaluate', argv)


if __name__ == '__main__':
    raise SystemExit(main())
