#!/usr/bin/env python3

import sys
import argparse
import re
import csv
from enum import Enum, IntEnum
from dataclasses import dataclass


class ExitStatus(IntEnum):
    SUCCESS = 0
    FAILURE = 1


class LineType(Enum):
    EMPTY = "empty"
    COMMENT = "comment"
    DATA = "data"


@dataclass
class ParsedLine:
    type: LineType
    domain: str
    note: str


def parse_line(line: str) -> ParsedLine:
    stripped = line.strip()

    if not stripped:
        return ParsedLine(LineType.EMPTY, "", "")

    if stripped.startswith("#"):
        return ParsedLine(LineType.COMMENT, "", stripped[1:].strip())

    delimiter = ";" if ";" in stripped else "\t"
    reader = csv.reader([stripped], delimiter=delimiter, quotechar='"')

    try:
        row = next(reader)
    except Exception:
        return ParsedLine(LineType.DATA, "", "")

    domain = row[0].strip() if len(row) > 0 else ""
    note = row[1].strip() if len(row) > 1 else ""

    return ParsedLine(LineType.DATA, domain, note)


def normalize_domain(domain: str) -> str:
    return domain.strip().lower().rstrip(".")


def is_valid_domain(domain: str) -> bool:
    if not domain:
        return False

    if len(domain) > 253:
        return False

    if "." not in domain:
        return False

    labels = domain.split(".")

    for label in labels:
        if not label:
            return False

        if len(label) > 63:
            return False

        if label.startswith("-") or label.endswith("-"):
            return False

        if not re.fullmatch(r"[a-z0-9-]+", label):
            return False

    tld = labels[-1]
    if len(tld) < 2 or not re.fullmatch(r"[a-z]+", tld):
        return False

    return True


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
        for line_number, line in enumerate(args.infile, start=1):
            parsed = parse_line(line)

            if parsed.type != LineType.DATA:
                continue

            domain = normalize_domain(parsed.domain)
            note = parsed.note

            if not is_valid_domain(domain):
                print(
                    "Warning: invalid domain at line {0}: {1}".format(
                        line_number, parsed.domain
                    ),
                    file=sys.stderr,
                )
                continue

            print(
                "OK line {0}: domain={1} note={2}".format(
                    line_number, domain, note
                ),
                file=args.outfile,
            )

    except Exception as e:
        print("Error while reading input: {0}".format(e), file=sys.stderr)
        return ExitStatus.FAILURE

    finally:
        if args.infile is not sys.stdin:
            args.infile.close()
        if args.outfile is not sys.stdout:
            args.outfile.close()

    return ExitStatus.SUCCESS


if __name__ == "__main__":
    sys.exit(main())
