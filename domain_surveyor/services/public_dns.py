"""
Public DNS lookup service.

This module queries DNS using the system-configured resolver and returns
normalized record data for a single domain.

Design goals:
- Python 3.6 compatible
- synchronous and simple
- suitable for execution inside ThreadPoolExecutor
- explicit per-section errors instead of sentinel-heavy mixed values
"""

from __future__ import absolute_import

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import dns.exception
import dns.reversename
import dns.resolver


DNS_EXCEPTIONS = (
    dns.exception.Timeout,
    dns.resolver.NoAnswer,
    dns.resolver.NoNameservers,
    dns.resolver.NXDOMAIN,
)


@dataclass
class PublicDNSResult(object):
    domain: str
    soa_rname: Optional[str] = None
    ns: List[str] = field(default_factory=list)
    mx: List[str] = field(default_factory=list)
    txt: List[str] = field(default_factory=list)
    spf: List[str] = field(default_factory=list)
    dmarc: List[str] = field(default_factory=list)
    ms: List[str] = field(default_factory=list)
    a: List[str] = field(default_factory=list)
    ptr: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)

    @property
    def exists_in_dns(self):
        return self.soa_rname is not None

    def to_dict(self):
        return {
            "domain": self.domain,
            "soa_rname": self.soa_rname,
            "ns": self.ns,
            "mx": self.mx,
            "txt": self.txt,
            "spf": self.spf,
            "dmarc": self.dmarc,
            "ms": self.ms,
            "a": self.a,
            "ptr": self.ptr,
            "errors": self.errors,
            "exists_in_dns": self.exists_in_dns,
        }


def build_resolver(timeout=2.0, lifetime=4.0):
    """
    Build a resolver using system DNS configuration.
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = lifetime
    return resolver


def _sort_unique(values):
    return sorted(set(values))


def _normalize_name(value):
    return value.rstrip(".")


def _normalize_txt_record(rdata):
    """
    Join multi-string TXT records into a single readable string.
    """
    if hasattr(rdata, "strings"):
        parts = []
        for chunk in rdata.strings:
            if isinstance(chunk, bytes):
                parts.append(chunk.decode("utf-8", errors="replace"))
            else:
                parts.append(str(chunk))
        return "".join(parts)

    return str(rdata).strip('"')


def _resolve(resolver, qname, rdtype):
    return list(resolver.resolve(qname, rdtype))


def _lookup_soa(domain, resolver, result):
    try:
        answers = _resolve(resolver, domain, "SOA")
        if answers:
            result.soa_rname = _normalize_name(answers[0].rname.to_text())
            return True

        result.errors["soa"] = "empty answer"
        return False

    except DNS_EXCEPTIONS as exc:
        result.errors["soa"] = exc.__class__.__name__
        return False


def _lookup_ns(domain, resolver, result):
    try:
        answers = _resolve(resolver, domain, "NS")
        result.ns = _sort_unique([
            _normalize_name(answer.to_text())
            for answer in answers
        ])
    except DNS_EXCEPTIONS as exc:
        result.errors["ns"] = exc.__class__.__name__


def _lookup_mx(domain, resolver, result):
    try:
        answers = _resolve(resolver, domain, "MX")
        result.mx = _sort_unique([
            _normalize_name(answer.to_text())
            for answer in answers
        ])
    except DNS_EXCEPTIONS as exc:
        result.errors["mx"] = exc.__class__.__name__


def _lookup_txt_family(domain, resolver, result):
    try:
        answers = _resolve(resolver, domain, "TXT")
    except DNS_EXCEPTIONS as exc:
        result.errors["txt"] = exc.__class__.__name__
        return

    txt_records = []
    spf_records = []
    ms_records = []

    for answer in answers:
        value = _normalize_txt_record(answer)
        value_lower = value.lower()

        if value.upper().startswith("MS="):
            ms_records.append(value.strip())
        elif value_lower.startswith("v=spf1 "):
            spf_records.append(value)
        else:
            txt_records.append(value)

    result.txt = _sort_unique(txt_records)
    result.spf = _sort_unique(spf_records)
    result.ms = _sort_unique(ms_records)


def _lookup_dmarc(domain, resolver, result):
    dmarc_domain = "_dmarc.{0}".format(domain)

    try:
        answers = _resolve(resolver, dmarc_domain, "TXT")
        result.dmarc = _sort_unique([
            _normalize_txt_record(answer)
            for answer in answers
        ])
    except DNS_EXCEPTIONS as exc:
        result.errors["dmarc"] = exc.__class__.__name__


def _lookup_a(domain, resolver, result):
    try:
        answers = _resolve(resolver, domain, "A")
        result.a = _sort_unique([
            answer.to_text()
            for answer in answers
        ])
    except DNS_EXCEPTIONS as exc:
        result.errors["a"] = exc.__class__.__name__


def _lookup_ptr(domain, resolver, result):
    """
    Resolve PTR for every A record found.
    """
    if not result.a:
        return

    ptr_values = []

    for ip_address in result.a:
        try:
            rev_name = dns.reversename.from_address(ip_address)
            answers = _resolve(resolver, rev_name.to_text(), "PTR")
            for answer in answers:
                ptr_values.append(_normalize_name(answer.to_text()))
        except (dns.exception.Timeout,
                dns.resolver.NoAnswer,
                dns.resolver.NoNameservers,
                dns.resolver.NXDOMAIN,
                ValueError):
            continue

    result.ptr = _sort_unique(ptr_values)


def lookup_domain_dns(domain, timeout=2.0, lifetime=4.0):
    """
    Query public DNS for a single domain.

    Parameters:
        domain (str): domain name to resolve
        timeout (float): per-try timeout
        lifetime (float): total query lifetime

    Returns:
        PublicDNSResult
    """
    domain = domain.strip().rstrip(".").lower()
    result = PublicDNSResult(domain=domain)
    resolver = build_resolver(timeout=timeout, lifetime=lifetime)

    has_soa = _lookup_soa(domain, resolver, result)
    if not has_soa:
        return result

    _lookup_ns(domain, resolver, result)
    _lookup_mx(domain, resolver, result)
    _lookup_txt_family(domain, resolver, result)
    _lookup_dmarc(domain, resolver, result)
    _lookup_a(domain, resolver, result)
    _lookup_ptr(domain, resolver, result)

    return result
