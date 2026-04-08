import re
import csv
from enum import Enum
from dataclasses import dataclass
from typing import Iterable, Iterator


class LineType(Enum):
    EMPTY = "empty"
    COMMENT = "comment"
    DATA = "data"


@dataclass
class ParsedLine:
    type: LineType
    domain: str
    note: str


@dataclass
class ParsedTarget:
    line_number: int
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


def iter_targets(lines: Iterable[str]) -> Iterator[ParsedTarget]:
    for line_number, line in enumerate(lines, start=1):
        parsed = parse_line(line)

        if parsed.type != LineType.DATA:
            continue

        domain = normalize_domain(parsed.domain)

        if not is_valid_domain(domain):
            continue

        yield ParsedTarget(
            line_number=line_number,
            domain=domain,
            note=parsed.note,
        )
