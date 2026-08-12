# Meta eBay Glass Scanner

MVP architecture for Meta Ray-Ban Display: identify an item, query eBay, calculate a robust price range, and send a compact result to the glasses display.

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8080
```

Test immediately with mock data:

```bash
curl -X POST http://127.0.0.1:8080/api/scan -H 'Content-Type: application/json' -d '{"query":"Nintendo Game Boy Color Atomic Purple"}'
```

Then set `MOCK_MODE=false` and add your eBay application credentials to `.env`.

## Important

This MVP uses eBay Browse API active listings. It intentionally does NOT pretend active listing prices are sold prices. For a true resale valuation, sold/completed-sale data needs an approved eBay data source.

## Meta glasses integration

The Meta-specific part is intentionally isolated. Add Meta's current Wearables Device Access Toolkit to an Xcode iOS app and implement three operations:

- capture a photo from the glasses
- start/maintain the device session
- render the result on the Display

The scanner/backend does not need to change when the Meta SDK changes.

## Intended flow

Glasses camera -> stable gaze trigger -> photo -> vision model -> item name/query -> eBay -> price estimator -> right-eye Display.

For the first prototype use 3–5 seconds of stable viewing rather than exactly 10 seconds; change the threshold later if desired.
