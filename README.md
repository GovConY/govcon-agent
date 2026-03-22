# govcon-agent

Regional government contracting discovery tool focused on Springfield, Missouri and nearby official public procurement sources.

## Project structure

- `main.py` - CLI entrypoint for collecting opportunities and rendering source-status and result tables.
- `scraper/` - Source adapter layer, shared models, and mock/live collection logic.
- `matcher/` - Keyword-based supplier matching module used in JSON output.
- `requirements.txt` - Dependency list.

## Mock mode

Mock mode is designed for reliable testing and offline development.

```bash
python3 main.py --source mock --output table --state MO --location Springfield
```

What mock mode does:

- returns bundled Springfield / Greene County / Missouri statewide sample opportunities
- always marks rows with `source_type=mock`
- never mixes fabricated records into live mode

## Live mode

Live mode runs source adapters against official public procurement sources only.

```bash
python3 main.py --source live --output table --state MO --location Springfield
```

What live mode does:

- attempts to fetch each official public source directly
- classifies each source as one of:
  - `working live source`
  - `partially parsed source`
  - `source requiring manual review`
- only returns opportunity rows when the adapter actually parsed them from the live source
- never fabricates live bids when parsing fails

## Output format

Table output prints two sections:

1. **Source Adapter Status** - shows which official sources are working, partially parsed, or need manual review
2. **Opportunity Results** - prints actual result rows with these columns:
   - title
   - agency
   - portal
   - location
   - due date
   - solicitation type
   - source type (`mock` or `live`)
   - URL

JSON output includes both `source_reports` and `opportunities`.

When you need a slimmer machine-readable payload, use compact JSON mode:

```bash
python3 main.py --source live --output json --compact-json --state MO
```

Compact JSON keeps only:

- `title`
- `agency`
- `portal`
- `location`
- `due_date`
- `solicitation_type`
- `source_type`
- `url`
- `match_score`
- `score_reasons`
- `supplier_matches`

## Limitations of live scraping

- Many official procurement pages use vendor-hosted portals, JavaScript-heavy interfaces, bot protection, or request filtering.
- Some official public pages load successfully but do not expose structured solicitation rows in static HTML.
- In those cases, the adapter marks the source as `partially parsed source` or `source requiring manual review` instead of guessing.
- Current live adapters prioritize correctness and transparency over aggressive scraping.

## Known source coverage

Current official source coverage included by the live adapters:

- **City of Springfield, MO** - official bid portal page
- **Greene County, MO** - official procurement page
- **SAM.gov** - official Get Opportunities Public API
- **Missouri statewide procurement portal** - MissouriBUYS bid board
- **Christian County, MO** - official county bidding opportunities page
- **City of Nixa, MO** - official purchasing information page
- **City of Ozark, MO** - official bid postings page
- **City of Republic, MO** - official bid postings page

## SAM.gov setup

The SAM.gov live adapter uses the official **Get Opportunities Public API**:

- Production endpoint: [https://api.sam.gov/opportunities/v2/search](https://api.sam.gov/opportunities/v2/search)
- Official documentation: [SAM.gov Get Opportunities Public API](https://open.gsa.gov/api/get-opportunities-public-api/)

Requirements:

- a SAM.gov public API key
- the `SAM_GOV_API_KEY` environment variable set before running live mode

Example PowerShell setup:

```powershell
$env:SAM_GOV_API_KEY="your-public-api-key"
python main.py --source live --state MO --location Springfield
```

Notes:

- the SAM.gov Opportunities API requires `postedFrom` and `postedTo`; this project uses a rolling 30-day posted-date window so the existing CLI stays unchanged
- the API paginates with `limit` and `offset`; the adapter follows pagination and normalizes each returned opportunity into the existing output schema
- if the API key is missing, the adapter reports that clearly in the source status table instead of fabricating records
- JSON output includes `match_score` and `score_reasons`, and table results are sorted by highest score first

## Example commands

```bash
python3 main.py --source mock --output table --state MO --location Springfield
python3 main.py --source live --output table --state MO --location Springfield
python3 main.py --source all --output json --state MO --location Springfield
python3 main.py --source live --state MO --naics 236220
python3 main.py --source live --state MO --keyword construction --naics 236220,237310
python3 main.py --source live --output json --keyword construction --naics 236220
python3 main.py --source live --state MO --top 3
```
