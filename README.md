# RaaSFinder

RaaSFinder is a from-scratch, evidence-driven Ransomware-as-a-Service discovery project.

## Design principles

- No pre-seeded RaaS groups, addresses, onion services, or CTI databases.
- No external CTI API dependency.
- No AI dependency.
- Discovery is separated into clear-web, public forums, onion sources, and public onion-index discovery channels.
- Collected pages are temporary evidence snapshots. They are parsed and verified, then deleted after a successful structured-data commit.
- Findings are based on deterministic rules, evidence correlation, timestamps, hashes, and confidence scoring.
- The public website displays sanitized structured intelligence, never raw collected pages or sensitive leaked records.

## Repository layout

```text
RaaSFinder/
├── app/                  # deterministic discovery and verification engine
├── config/               # rules and runtime configuration
├── data/                 # local structured state; runtime data is ignored
├── runtime/snapshots/    # temporary HTML snapshots; never committed
├── tests/                # unit tests
├── web/                  # static GitHub Pages interface
└── .github/workflows/    # scheduled discovery and Pages deployment
```

## Discovery model

```text
DISCOVER → SNAPSHOT → PARSE → DETECT → CORRELATE → VERIFY → PERSIST → DELETE SNAPSHOT
```

The initial repository intentionally contains **zero known RaaS seeds**. New entities must emerge from observations and pass deterministic verification before being promoted to intelligence.

## Safety boundary

Collectors are designed for publicly accessible material only. RaaSFinder does not bypass authentication, access controls, paywalls, CAPTCHAs, or private communities, and it does not collect credentials, stolen databases, or personal records for publication.

## Local development

```bash
python -m app.cli --help
python -m pytest
```

The web interface is a static frontend suitable for GitHub Pages. Discovery jobs are designed to run separately through GitHub Actions or another controlled runner.
