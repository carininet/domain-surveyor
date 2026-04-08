#!/usr/bin/env python3

import sys
import argparse
from enum import IntEnum

from domain_surveyor.core.input_parser import iter_targets


class ExitStatus(IntEnum):
    SUCCESS = 0
    FAILURE = 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="DomainSurveyor - initialization and input reader"
    )

    parser.add_argument(
        "-i",
        "--infile",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Input file (default: stdin)",
    )

    parser.add_argument(
        "-o",
        "--outfile",
        type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="Output file (default: stdout)",
    )

    args = parser.parse_args()

    try:
        for target in iter_targets(args.infile):
            print(
                "OK line {0}: domain={1} note={2}".format(
                    target.line_number,
                    target.domain,
                    target.note,
                ),
                file=args.outfile,
            )

    except Exception as e:
        print(f"Error while reading input: {e}", file=sys.stderr)
        return ExitStatus.FAILURE

    finally:
        if args.infile is not sys.stdin:
            args.infile.close()
        if args.outfile is not sys.stdout:
            args.outfile.close()

    return ExitStatus.SUCCESS


if __name__ == "__main__":
    sys.exit(main())
