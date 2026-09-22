# srp-irrigation

Scrape SRP flood irrigation schedules with Playwright and store observations in DuckDB.

Run:

```bash
uv run srp-irrigation
```

The scraper uses a visible Firefox browser and logs human-like pauses between meaningful browser actions.

## SRP API

Get subdivision names:
https://water.gateway.srpnet.com/subdivisions/getsubdivisions/{onlynonirrigated: bool}
https://water.gateway.srpnet.com/subdivisions/getsubdivisions/false

Get subdivision schedule:
https://water.gateway.srpnet.com/schedule/subdivision/1374
https://water.gateway.srpnet.com/schedule/subdivision/{id: int32}

search address:
https://water.gateway.srpnet.com/customer/address/search/253%20E%205th
