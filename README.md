# CampusLoop

CampusLoop helps campus communities keep useful goods in circulation through resale, day transfer, no-cost lending, and pooled dealer bids. The project includes a FastAPI/SQLite backend, a responsive five-page web app, and a Docker Compose deployment with Prometheus and Grafana.

All students and dealers are seeded demo identities. The application has no authentication, identity provider, payment provider, or real-world dealer verification. Purchases and payout allocations are persisted **simulated records**; no charge, UPI transfer, or disbursement occurs. Valuations are estimates, not guarantees.

## Features

- **Valuation:** category-specific monthly depreciation, condition factors, day-transfer pricing, TrustLend eligibility, and pool/scrap estimates.
- **Marketplace:** exact category/mode/block filters, validated listings, computed prices, simulated checkout, and buyer/seller history.
- **TrustLend:** borrower/lender roles, one-time 24-hour QR token, simulated handover, seven-day loan, return scoring, and lender/borrower history.
- **Dealer pool:** guarded pickup, pooling, auction, and simulated allocation stages with three seeded verified demo dealers.
- **Home story:** a minimal illustrated reuse loop. On wide screens GSAP ScrollTrigger scrubs the path and story cards; Lite mode, narrow screens, reduced-motion preferences, or unavailable animation libraries retain the static story.

See [the UX specification](docs/UX_Design_Thinking_Spec.md) and [editable Figma mockup](docs/campusloop-figma-mockup.svg) for design details and role personas.

## Run with Docker Compose

Requirements: Docker Engine with the Compose plugin.

```sh
docker compose up --build -d
docker compose ps
```

Open <http://localhost:3000>. Compose waits for API/UI health before starting the proxy. Direct page routes are available at:

- `/` or `/index.html` — Home
- `/valuation.html` — Valuation
- `/marketplace.html` — Marketplace
- `/trustlend.html` — TrustLend
- `/dealer-pool.html` — Dealer pool

The proxy exposes the API on the same origin under `/api/`, plus `/health` and `/metrics`. The API container is not published directly to the host.

| Service | Local URL | Purpose |
|---|---|---|
| Web app and reverse proxy | <http://localhost:3000> | Static pages and same-origin API routes |
| Prometheus | <http://localhost:9090> | Metrics and scrape target status |
| Grafana | <http://localhost:3001> | Monitoring UI |

SQLite is stored in the named `campusloop-data` volume. `docker compose down` stops the services and retains the volume. Avoid `docker compose down -v` unless you intend to delete the database. A fresh database is seeded with 12 sample items, four demo students, three demo dealers, and an academic-book TrustLend listing. Startup migrates known legacy labels without dropping user tables or transaction records.

## Run backend tests

```sh
python -m pip install -r backend/requirements.txt
python -m pytest backend/test_main.py -q
```

Tests use isolated in-memory SQLite databases; they do not modify the Compose volume.

## API overview

The API is reached through the web origin (`http://localhost:3000`). Integer amounts are Indian rupees.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/valuate` | Calculate resale/day-transfer values, trust eligibility, pool and scrap estimates |
| `GET`, `POST` | `/api/items` | Browse/filter or create a listing |
| `GET` | `/api/students` | Get seeded demo identities and persisted trust metrics |
| `GET` | `/api/isbn/{isbn}` | Look up a seeded ISBN record |
| `POST`, `GET` | `/api/purchases` | Record simulated checkout; retrieve a student's buyer/seller history |
| `POST` | `/api/trustlend/borrow` | Request a listed loan and receive a one-time token |
| `POST` | `/api/trustlend/handover` | Activate a loan using its token |
| `POST` | `/api/trustlend/return` | Record return and update persisted trust metrics |
| `GET` | `/api/trustlend/loans` | Retrieve borrower/lender history without QR tokens |
| `GET` | `/api/leaderboard` | Rank blocks by resident trust and on-time returns |
| `GET` | `/api/dealer-pool` | Read current or final batch state |
| `POST` | `/api/dealer-pool/add`, `/api/dealer-pool/bid`, `/api/dealer-pool/advance` | Add item, submit increasing bid, or advance one guarded stage |
| `GET` | `/health` | API/database health |
| `GET` | `/metrics` | Prometheus request counter and borrow/pool gauges |

### Valuation inputs

`GET /api/valuate` requires `category`, `condition`, `original_price`, and `months_used`; `days_used`, `on_time_returns`, `late_returns`, and `items_lent` are optional. Categories are `Academic Book`, `Hostel Appliance`, and `Hostel Furniture`. Conditions are exactly `Mint`, `Good`, and `Worn`.

Monthly depreciation rates are 6% for books, 4% for appliances, and 3.5% for furniture. Condition multipliers are 1.0, 0.9, and 0.8. The resale floor is 25% of original price. For day transfer, zero days returns the original price; otherwise depreciation is 0.3% per day with a 50% floor.

```sh
curl 'http://localhost:3000/api/valuate?category=Academic%20Book&condition=Mint&original_price=1000&months_used=10&days_used=0'
```

### Listing and transaction rules

`GET /api/items` accepts exact `category`, `mode`, and `hostel_block` filters. `POST /api/items` accepts the listing fields `title`, `owner_id`, `category`, `condition`, `original_price`, `months_used`, `hostel_block`, and `mode`; `days_used` and `isbn` are optional. Modes are `Senior Resale`, `Day Transfer`, and `₹0 TrustLend`.

Purchases accept `{ "item_id": 1, "buyer_id": "student-b" }`. The seller is derived from listing ownership. Unknown IDs, self-purchase, unavailable items, and TrustLend items are rejected. Checkout records an integer amount and `payment_status: "simulated"`; it does not process money.

TrustLend requires the lender to own an available `₹0 TrustLend` item, distinct lender and borrower IDs, and a persisted borrower score of at least 50 for a book or 65 for either hostel category. Handover tokens expire after 24 hours; activated loans are due after seven days.

The dealer pool advances through `Hostel Pickup Scheduled`, `Pooled in Campus Batch`, `Wholesale Dealer Auction Won`, and `Payout Recorded (Simulated)`. A bid must exceed the current highest bid. Pool estimates use 42% of original price and individual scrap estimates use 15%; their 2.8 ratio is arithmetic only, not a payout guarantee. Allocation remainders go to the final sorted owner ID so recorded allocations sum to the winning demo bid.

## CI and deployment

`.github/workflows/ci-cd.yml` runs Python tests, a HIGH/CRITICAL Trivy filesystem scan, image builds, and Compose route/health smoke checks on pull requests and `main`/`develop` pushes. Publishing is restricted to `main` and skips registries without configured secrets. Azure Container Instances deployment is manual and opt-in (`workflow_dispatch` → `deploy_aci`); no ordinary push deploys to Azure.
