# source_check

## Purpose

`source_check` screens a list of URLs/domains for basic source-quality risk before the agent uses them in a research digest or claim summary.

It is a heuristic helper, not a fact checker. It classifies domains as higher trust when they are clearly primary, institutional, academic, or well-known research/company sources, and asks the user/agent to verify unknown or user-generated sources.

## When to use

Use this tool when the user asks to:

- check whether sources look credible;
- compare citation quality;
- identify weak sources in a source list;
- review source risk before publishing or summarizing.

Do not use it for normal web search. Use `lookup` first if the user has not provided sources.

## Arguments

- `sources`: list of URLs or domains to inspect.
- `claim`: optional claim/topic the sources are meant to support.
- `purpose`: optional purpose such as `research`, `publishing`, `policy`, or `summary`.

## Output

Returns:

- per-source domain and trust level;
- reasons;
- source count;
- recommendation;
- guardrail explaining that the result is heuristic.
