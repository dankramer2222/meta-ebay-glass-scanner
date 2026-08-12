import os, base64, time
from statistics import median
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()
MOCK = os.getenv("MOCK_MODE", "true").lower() == "true"
BASE = os.getenv("EBAY_API_BASE", "https://api.ebay.com")
CID = os.getenv("EBAY_CLIENT_ID", "")
SECRET = os.getenv("EBAY_CLIENT_SECRET", "")
MARKET = os.getenv("EBAY_MARKETPLACE_ID", "EBAY_US")

app = FastAPI(title="Meta eBay Glass Scanner", version="0.1.0")
_token, _expires = None, 0

class ScanRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    max_results: int = Field(50, ge=5, le=200)

class ScanResponse(BaseModel):
    item: str
    low: float
    median: float
    high: float
    sample_size: int
    currency: str = "USD"
    source: str
    warning: str

def estimate(values):
    values = sorted(float(x) for x in values if float(x) > 0)
    if not values: raise ValueError("No usable prices")
    if len(values) >= 10:
        a, b = values[int(len(values)*.1)], values[min(len(values)-1, int(len(values)*.9))]
        values = [x for x in values if a <= x <= b]
    def pct(p):
        k=(len(values)-1)*p; f=int(k); c=min(f+1,len(values)-1)
        return values[f] if f==c else values[f]+(values[c]-values[f])*(k-f)
    return pct(.2), median(values), pct(.8), len(values)

async def ebay_token():
    global _token, _expires
    if _token and time.time() < _expires-60: return _token
    if not CID or not SECRET: raise RuntimeError("Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET")
    basic=base64.b64encode(f"{CID}:{SECRET}".encode()).decode()
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.post(f"{BASE}/identity/v1/oauth2/token",headers={"Authorization":f"Basic {basic}","Content-Type":"application/x-www-form-urlencoded"},data={"grant_type":"client_credentials","scope":"https://api.ebay.com/oauth/api_scope"})
        r.raise_for_status(); d=r.json()
    _token=d["access_token"]; _expires=time.time()+int(d.get("expires_in",7200)); return _token

async def ebay_search(q, limit):
    token=await ebay_token()
    async with httpx.AsyncClient(timeout=15) as c:
        r=await c.get(f"{BASE}/buy/browse/v1/item_summary/search",headers={"Authorization":f"Bearer {token}","X-EBAY-C-MARKETPLACE-ID":MARKET},params={"q":q,"limit":min(limit,200),"filter":"buyingOptions:{FIXED_PRICE}"})
        r.raise_for_status(); return r.json().get("itemSummaries",[])

@app.get("/health")
async def health(): return {"ok":True,"mock_mode":MOCK}

@app.post("/api/scan",response_model=ScanResponse)
async def scan(req: ScanRequest):
    if MOCK:
        prices=[69,74,79,82,85,89,95,99,110,129,139]
        low,med,high,n=estimate(prices)
        return ScanResponse(item=req.query,low=round(low,2),median=round(med,2),high=round(high,2),sample_size=n,source="Mock eBay data",warning="Demo data")
    try:
        items=await ebay_search(req.query,req.max_results)
        prices=[float(x["price"]["value"]) for x in items if x.get("price",{}).get("value")]
        currency=next((x["price"].get("currency") for x in items if x.get("price",{}).get("currency")),"USD")
        low,med,high,n=estimate(prices)
        return ScanResponse(item=req.query,low=round(low,2),median=round(med,2),high=round(high,2),sample_size=n,currency=currency,source="eBay active listings",warning="Asking-price estimate; not sold/completed-sale data.")
    except Exception as e: raise HTTPException(502,str(e))
