"""Command-line entry point (`ore`). Subcommands are added as the pipeline grows."""

import argparse
from collections.abc import Sequence

from open_rag_engine import __version__

EXIT_USAGE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ore",
        description="Ingest documents and answer questions with cited evidence.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_subparsers(dest="command")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
