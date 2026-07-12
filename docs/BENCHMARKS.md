# Benchmarks

Published whatever they say. Same machine, same FastAPI substrate,
same fifty-row dataset: the cambered render paths against the JSON
endpoint an equivalent SPA would call. The SPA's bundle download,
parse, and hydration are not billed here — these are its best-case
numbers, and the comparison is still close.

Machine: arm64 · Python 3.14.0 · concurrency 32 · 6s per row

| path | req/s | bytes | p50 ms |
|------|------:|------:|-------:|
| HTML page (full document) | 2,018 | 5,956 | 15.6 |
| Boosted fragment | 2,006 | 5,869 | 15.8 |
| Chart (agent projection) | 1,962 | 6,142 | 15.9 |
| JSON API (SPA baseline) | 2,066 | 2,023 | 15.3 |

Reading: the fragment and chart cost less than the full page; the
JSON baseline saves bytes it later spends client-side rendering
them. Server-rendering fifty rows is not the expensive part of a
web application.

Regenerate: `uv run python scripts/bench.py`
