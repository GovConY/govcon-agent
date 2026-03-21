# govcon-agent

AI-powered government contract sourcing and supplier matching tool for local, state, and federal opportunities.

## Project structure

- `main.py` - CLI entrypoint for fetching opportunities and rendering table/JSON output.
- `scraper/` - Opportunity scraping layer with SAM.gov API support and mock-data fallback.
- `matcher/` - Keyword-based supplier matching module.
- `requirements.txt` - Python dependency list.

## Usage

```bash
python3 main.py --source mock --output table --state MO --location Springfield
python3 main.py --source mock --output table --state MO --location "Greene County"
```

The mock dataset now includes:

- Springfield city bids
- Greene County bids
- Missouri statewide portal opportunities

To use live SAM.gov data, set `SAM_API_KEY` and switch the source:

```bash
export SAM_API_KEY=your_key_here
python3 main.py --source sam --limit 10 --state MO --keyword network
```

If the SAM.gov request fails or no API key is present, the tool automatically falls back to bundled mock opportunities so local development remains reliable.
