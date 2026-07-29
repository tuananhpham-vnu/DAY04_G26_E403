from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


HIGH_TRUST_DOMAINS = {
    "arxiv.org",
    "openai.com",
    "anthropic.com",
    "deepmind.google",
    "ai.google",
    "microsoft.com",
    "nature.com",
    "science.org",
    "acm.org",
    "ieee.org",
    "gov",
    "edu",
}

LOW_TRUST_MARKERS = {
    "blogspot.",
    "medium.com",
    "substack.com",
    "reddit.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "tiktok.com",
}


def _domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return parsed.netloc.lower().replace("www.", "")


def _trust_level(domain: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if any(domain == item or domain.endswith(f".{item}") for item in HIGH_TRUST_DOMAINS):
        reasons.append("recognized primary, academic, company, or institutional domain")
        return "high", reasons
    if any(marker in domain for marker in LOW_TRUST_MARKERS):
        reasons.append("platform or user-generated content; verify with primary sources")
        return "medium", reasons
    reasons.append("unknown domain; verify author, date, and citations")
    return "medium", reasons


def check_sources(sources: list[str] | None = None, claim: str = "", purpose: str = "research") -> dict[str, Any]:
    sources = sources or []
    items: list[dict[str, Any]] = []
    for source in sources:
        domain = _domain(source)
        trust_level, reasons = _trust_level(domain)
        items.append({
            "source": source,
            "domain": domain,
            "trust_level": trust_level,
            "reasons": reasons,
        })

    high_count = sum(1 for item in items if item["trust_level"] == "high")
    recommendation = "use_with_citation" if high_count else "verify_before_using"
    if len(items) < 2:
        recommendation = "add_more_sources"

    return {
        "tool": "source_check",
        "claim": claim,
        "purpose": purpose,
        "source_count": len(items),
        "items": items,
        "recommendation": recommendation,
        "guardrail": "This is a heuristic source-quality screen, not a factual verification result.",
    }
