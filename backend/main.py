from datetime import timedelta, timezone
from collections import Counter
from threading import Lock
from math import floor
import secrets

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import (SessionLocal, engine, get_db, init_db, utcnow, Student, Item, ISBNRecord, Dealer, BorrowRequest, Purchase, PoolBatch, PoolEntry, DealerBid, PayoutAllocation)

CATEGORIES = {"Academic Book", "Hostel Appliance", "Hostel Furniture"}
CONDITIONS = {"Mint", "Good", "Worn"}
MODES = {"Senior Resale", "Day Transfer", "₹0 TrustLend"}
MONTHLY_RATES = {"Academic Book": .06, "Hostel Appliance": .04, "Hostel Furniture": .035}
CONDITION_FACTORS = {"Mint": 1.0, "Good": .9, "Worn": .8}
STAGES = ["pickup_scheduled", "pooled", "auction_won", "final"]
STAGE_LABELS = ["Hostel Pickup Scheduled", "Pooled in Campus Batch", "Wholesale Dealer Auction Won", "Payout Recorded (Simulated)"]
app = FastAPI(title="CampusLoop Demo API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8080", "http://127.0.0.1:8080"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
_request_counts = Counter()
_counter_lock = Lock()


@app.on_event("startup")
def startup():
    init_db()


@app.middleware("http")
async def count_requests(request: Request, call_next):
    response = await call_next(request)
    if request.url.path != "/metrics":
        with _counter_lock:
            _request_counts[(request.method, request.url.path, response.status_code)] += 1
    return response


def score(on_time, lent, late):
    return min(100, max(0, 50 + 10 * on_time + 5 * lent - 25 * late))


def senior_price(item):
    return max(round(item.original_price * .25), round(item.original_price * (1 - MONTHLY_RATES[item.category] * item.months_used) * CONDITION_FACTORS[item.condition]))


def day_price(item):
    if item.days_used == 0:
        return round(item.original_price)
    return max(round(item.original_price * .50), round(item.original_price * (1 - .003 * item.days_used)))


def price_for_mode(item):
    return senior_price(item) if item.mode == "Senior Resale" else day_price(item)


def item_json(item, db):
    owner = db.get(Student, item.owner_id)
    return {"id": item.id, "title": item.title, "name": item.title, "category": item.category, "condition": item.condition, "original_price": item.original_price, "months_used": item.months_used, "days_used": item.days_used, "owner_id": item.owner_id, "owner_name": owner.name, "hostel_block": item.hostel_block, "block": item.hostel_block, "mode": item.mode, "available": item.available, "senior_resale_price": senior_price(item), "day_transfer_price": day_price(item)}


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    owner_id: str
    category: str
    condition: str
    original_price: int = Field(gt=0, le=10000000)
    months_used: int = Field(ge=0, le=600)
    days_used: int = Field(default=0, ge=0, le=36500)
    hostel_block: str
    mode: str = "Senior Resale"
    isbn: str | None = None


class BorrowInput(BaseModel):
    item_id: int
    borrower_id: str
    lender_id: str


class TokenInput(BaseModel):
    token: str = Field(min_length=20, max_length=128)


class BidInput(BaseModel):
    dealer_id: str
    amount: int = Field(gt=0, le=100000000)


class AddPoolInput(BaseModel):
    item_id: int


class PurchaseInput(BaseModel):
    item_id: int
    buyer_id: str


def require_student(db, student_id):
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(404, f"Unknown student ID: {student_id}")
    return student


def active_batch(db):
    batch = db.query(PoolBatch).filter_by(active=True).order_by(PoolBatch.id.desc()).first()
    if not batch:
        batch = PoolBatch(active=True, stage="pickup_scheduled")
        db.add(batch)
        db.flush()
    return batch


def batch_payload(db, batch):
    entries = db.query(PoolEntry).filter_by(batch_id=batch.id).order_by(PoolEntry.id).all()
    rows = []
    for entry in entries:
        item = db.get(Item, entry.item_id)
        owner = db.get(Student, entry.owner_id)
        rows.append({"item_id": item.id, "title": item.title, "owner_id": entry.owner_id, "owner_name": owner.name, "pool_estimate": round(item.original_price * .42), "scrap_estimate": round(item.original_price * .15)})
    pool, scrap = sum(row["pool_estimate"] for row in rows), sum(row["scrap_estimate"] for row in rows)
    bids = db.query(DealerBid).filter_by(batch_id=batch.id).order_by(DealerBid.amount.desc(), DealerBid.id.asc()).all()
    bid_rows = [{"dealer_id": bid.dealer_id, "dealer_name": db.get(Dealer, bid.dealer_id).name, "amount": bid.amount} for bid in bids]
    payouts = [{"owner_id": p.owner_id, "owner_name": db.get(Student, p.owner_id).name, "amount": p.amount, "payment_status": "simulated"} for p in db.query(PayoutAllocation).filter_by(batch_id=batch.id).order_by(PayoutAllocation.owner_id).all()]
    winner = next((b for b in bid_rows if b["dealer_id"] == batch.winner_dealer_id), None)
    return {"batch_id": batch.id, "stage": batch.stage, "stage_label": STAGE_LABELS[STAGES.index(batch.stage)], "active": batch.active, "entries": rows, "bids": bid_rows, "pool_estimate": pool, "scrap_estimate": scrap, "estimate_ratio": 2.8, "winner": winner, "payouts": payouts, "stages": STAGES, "stage_labels": STAGE_LABELS}


@app.get("/api/valuate")
def valuate(category: str, condition: str, original_price: int = Query(gt=0, le=10000000), months_used: int = Query(ge=0, le=600), days_used: int = Query(0, ge=0, le=36500), on_time_returns: int = Query(0, ge=0, le=10000), late_returns: int = Query(0, ge=0, le=10000), items_lent: int = Query(0, ge=0, le=10000)):
    if category not in CATEGORIES:
        raise HTTPException(422, "Unsupported category")
    if condition not in CONDITIONS:
        raise HTTPException(422, "Unsupported condition")
    trust_score = score(on_time_returns, items_lent, late_returns)
    threshold = 50 if category == "Academic Book" else 65
    factor = CONDITION_FACTORS[condition]
    senior = max(round(original_price * .25), round(original_price * (1 - MONTHLY_RATES[category] * months_used) * factor))
    day = round(original_price) if days_used == 0 else max(round(original_price * .50), round(original_price * (1 - .003 * days_used)))
    return {"senior_resale_price": senior, "day_transfer_price": day, "trust_score": trust_score, "trustlend_eligible": trust_score >= threshold, "trustlend_threshold": threshold, "trustlend_deposit": 0 if trust_score >= threshold else None, "dealer_pool_estimate": round(original_price * .42), "individual_scrap_estimate": round(original_price * .15)}


@app.get("/api/items")
def get_items(category: str | None = None, mode: str | None = None, hostel_block: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Item)
    if category is not None: query = query.filter(Item.category == category)
    if mode is not None: query = query.filter(Item.mode == mode)
    if hostel_block is not None: query = query.filter(Item.hostel_block == hostel_block)
    return [item_json(item, db) for item in query.order_by(Item.id).all()]


@app.post("/api/items", status_code=201)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)):
    if payload.category not in CATEGORIES: raise HTTPException(422, "Unsupported category")
    if payload.condition not in CONDITIONS: raise HTTPException(422, "Unsupported condition")
    if payload.mode not in MODES: raise HTTPException(422, "Unsupported mode")
    if payload.hostel_block not in "ABCD": raise HTTPException(422, "hostel_block must be A, B, C, or D")
    require_student(db, payload.owner_id)
    if payload.isbn and not db.get(ISBNRecord, payload.isbn): raise HTTPException(404, "ISBN not found")
    item = Item(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return item_json(item, db)


@app.get("/api/students")
def get_students(db: Session = Depends(get_db)):
    return [{"id": student.id, "name": student.name, "block": student.block, "on_time_returns": student.on_time_returns, "items_lent": student.items_lent, "late_returns": student.late_returns, "trust_score": student.trust_score} for student in db.query(Student).order_by(Student.block, Student.id).all()]


@app.get("/api/isbn/{isbn}")
def isbn_lookup(isbn: str, db: Session = Depends(get_db)):
    record = db.get(ISBNRecord, isbn)
    if not record: raise HTTPException(404, "ISBN not found")
    return {"isbn": record.isbn, "title": record.title, "category": record.category, "original_price": record.original_price}


def purchase_payload(purchase, db):
    buyer, seller = db.get(Student, purchase.buyer_id), db.get(Student, purchase.seller_id)
    return {"order_id": purchase.id, "item_id": purchase.item_id, "buyer_id": buyer.id, "buyer_name": buyer.name, "seller_id": seller.id, "seller_name": seller.name, "amount": purchase.amount, "created_at": purchase.created_at.isoformat(), "payment_status": purchase.payment_status}


@app.post("/api/purchases", status_code=201)
def create_purchase(payload: PurchaseInput, db: Session = Depends(get_db)):
    buyer = require_student(db, payload.buyer_id)
    item = db.get(Item, payload.item_id)
    if not item: raise HTTPException(404, "Item not found")
    if item.owner_id == buyer.id: raise HTTPException(400, "You cannot purchase your own listing")
    if not item.available: raise HTTPException(409, "Item is unavailable")
    if item.mode == "₹0 TrustLend": raise HTTPException(400, "TrustLend listings cannot be purchased")
    seller = require_student(db, item.owner_id)
    item.available = False
    purchase = Purchase(item_id=item.id, buyer_id=buyer.id, seller_id=seller.id, amount=price_for_mode(item), payment_status="simulated")
    db.add(purchase); db.commit(); db.refresh(purchase)
    return purchase_payload(purchase, db)


@app.get("/api/purchases")
def get_purchases(student_id: str, db: Session = Depends(get_db)):
    require_student(db, student_id)
    rows = db.query(Purchase).filter((Purchase.buyer_id == student_id) | (Purchase.seller_id == student_id)).order_by(Purchase.id.desc()).all()
    return [purchase_payload(row, db) for row in rows]


@app.post("/api/trustlend/borrow", status_code=201)
def borrow(payload: BorrowInput, db: Session = Depends(get_db)):
    item = db.get(Item, payload.item_id)
    if not item: raise HTTPException(404, "Item not found")
    borrower, lender = require_student(db, payload.borrower_id), require_student(db, payload.lender_id)
    if borrower.id == lender.id: raise HTTPException(400, "Borrower and lender must be different students")
    if item.owner_id != lender.id: raise HTTPException(400, "Lender must own the item")
    if item.mode != "₹0 TrustLend": raise HTTPException(400, "Item is not listed for TrustLend")
    if not item.available: raise HTTPException(409, "Item is currently unavailable")
    threshold = 50 if item.category == "Academic Book" else 65
    if borrower.trust_score < threshold: raise HTTPException(403, f"Trust score {borrower.trust_score} is below category threshold {threshold}")
    token = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(hours=24)
    request = BorrowRequest(item_id=item.id, borrower_id=borrower.id, lender_id=lender.id, token=token, token_expires_at=expires, status="requested")
    item.available = False
    db.add(request); db.commit(); db.refresh(request)
    return {"request_id": request.id, "item_id": item.id, "token": token, "expires_at": expires.isoformat(), "status": request.status}


@app.post("/api/trustlend/handover")
def handover(payload: TokenInput, db: Session = Depends(get_db)):
    loan = db.query(BorrowRequest).filter_by(token=payload.token).first()
    if not loan: raise HTTPException(404, "Invalid QR token")
    if loan.status != "requested": raise HTTPException(409, "Borrow request is not awaiting handover")
    expiry = loan.token_expires_at
    if expiry.tzinfo is None: expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < utcnow(): raise HTTPException(410, "QR token has expired")
    loan.status = "active"; loan.started_at = utcnow(); loan.due_at = loan.started_at + timedelta(days=7)
    db.commit()
    return {"request_id": loan.id, "status": loan.status, "started_at": loan.started_at.isoformat(), "due_at": loan.due_at.isoformat()}


@app.post("/api/trustlend/return")
def return_item(payload: TokenInput, db: Session = Depends(get_db)):
    loan = db.query(BorrowRequest).filter_by(token=payload.token).first()
    if not loan: raise HTTPException(404, "Invalid QR token")
    if loan.status == "requested": raise HTTPException(409, "Item cannot be returned before handover")
    if loan.status != "active": raise HTTPException(409, "Loan has already been returned")
    returned = utcnow(); loan.returned_at = returned; loan.status = "returned"
    borrower, lender = require_student(db, loan.borrower_id), require_student(db, loan.lender_id)
    due = loan.due_at
    if due.tzinfo is None: due = due.replace(tzinfo=timezone.utc)
    if returned <= due: borrower.on_time_returns += 1
    else: borrower.late_returns += 1
    lender.items_lent += 1
    db.get(Item, loan.item_id).available = True
    db.commit()
    return {"request_id": loan.id, "status": loan.status, "returned_at": returned.isoformat(), "borrower_trust_score": borrower.trust_score, "lender_trust_score": lender.trust_score}


@app.get("/api/trustlend/loans")
def loan_history(student_id: str, db: Session = Depends(get_db)):
    require_student(db, student_id)
    loans = db.query(BorrowRequest).filter((BorrowRequest.borrower_id == student_id) | (BorrowRequest.lender_id == student_id)).order_by(BorrowRequest.id.desc()).all()
    result = []
    for loan in loans:
        borrower, lender, item = db.get(Student, loan.borrower_id), db.get(Student, loan.lender_id), db.get(Item, loan.item_id)
        roles = []
        if loan.borrower_id == student_id: roles.append("borrower")
        if loan.lender_id == student_id: roles.append("lender")
        result.append({"request_id": loan.id, "item_id": item.id, "item_title": item.title, "borrower_id": borrower.id, "borrower_name": borrower.name, "lender_id": lender.id, "lender_name": lender.name, "role": roles[0] if len(roles) == 1 else "borrower_and_lender", "status": loan.status, "started_at": loan.started_at.isoformat() if loan.started_at else None, "due_at": loan.due_at.isoformat() if loan.due_at else None, "returned_at": loan.returned_at.isoformat() if loan.returned_at else None})
    return result


@app.get("/api/leaderboard")
def leaderboard(db: Session = Depends(get_db)):
    blocks = []
    for block in "ABCD":
        students = db.query(Student).filter_by(block=block).all()
        blocks.append({"block": block, "trust_score": sum(s.trust_score for s in students), "on_time_returns": sum(s.on_time_returns for s in students), "residents": len(students)})
    blocks.sort(key=lambda row: (-row["trust_score"], -row["on_time_returns"], row["block"]))
    return {"blocks": blocks}


@app.get("/api/dealer-pool")
def dealer_pool(db: Session = Depends(get_db)):
    batch = db.query(PoolBatch).order_by(PoolBatch.id.desc()).first()
    return batch_payload(db, batch or active_batch(db))

@app.post("/api/dealer-pool/add")
def add_to_pool(payload: AddPoolInput, db: Session = Depends(get_db)):
    batch = active_batch(db)
    if batch.stage != "pickup_scheduled": raise HTTPException(409, "Pool is no longer accepting items")
    item = db.get(Item, payload.item_id)
    if not item: raise HTTPException(404, "Item not found")
    if db.query(PoolEntry).filter_by(item_id=item.id).first(): raise HTTPException(409, "Item is already in a pool batch")
    db.add(PoolEntry(batch_id=batch.id, item_id=item.id, owner_id=item.owner_id)); db.commit()
    return batch_payload(db, batch)


@app.post("/api/dealer-pool/bid")
def place_bid(payload: BidInput, db: Session = Depends(get_db)):
    batch = active_batch(db)
    dealer = db.get(Dealer, payload.dealer_id)
    if not dealer: raise HTTPException(404, "Dealer not found")
    if not dealer.verified: raise HTTPException(403, "Dealer is not verified")
    if batch.stage != "pooled": raise HTTPException(409, "Bids are accepted only after pooling")
    top = db.query(func.max(DealerBid.amount)).filter_by(batch_id=batch.id).scalar() or 0
    if payload.amount <= top: raise HTTPException(400, f"Bid must exceed current top bid of ₹{top}")
    db.add(DealerBid(batch_id=batch.id, dealer_id=dealer.id, amount=payload.amount)); db.commit()
    return batch_payload(db, batch)


@app.post("/api/dealer-pool/advance")
def advance_pool(db: Session = Depends(get_db)):
    batch = active_batch(db)
    entries = db.query(PoolEntry).filter_by(batch_id=batch.id).all()
    if batch.stage == "pickup_scheduled":
        if not entries: raise HTTPException(409, "Cannot pool an empty batch")
        batch.stage = "pooled"
    elif batch.stage == "pooled":
        bids = db.query(DealerBid).filter_by(batch_id=batch.id).order_by(DealerBid.amount.desc(), DealerBid.id.asc()).all()
        if not bids: raise HTTPException(409, "At least one bid is required before selecting a winner")
        batch.winner_dealer_id = bids[0].dealer_id
        batch.stage = "auction_won"
    elif batch.stage == "auction_won":
        winning = db.query(DealerBid).filter_by(batch_id=batch.id).order_by(DealerBid.amount.desc(), DealerBid.id.asc()).first()
        totals = {}
        for entry in entries:
            item = db.get(Item, entry.item_id)
            totals[entry.owner_id] = totals.get(entry.owner_id, 0) + round(item.original_price * .42)
        denom = sum(totals.values())
        allocations = {owner: floor(winning.amount * value / denom) for owner, value in totals.items()} if denom else {}
        if allocations: allocations[sorted(allocations)[-1]] += winning.amount - sum(allocations.values())
        for owner, amount in sorted(allocations.items()): db.add(PayoutAllocation(batch_id=batch.id, owner_id=owner, amount=amount))
        batch.stage = "final"; batch.active = False
    else:
        raise HTTPException(409, "Pool is already at final stage")
    db.commit()
    return batch_payload(db, batch)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try: db.execute(text("SELECT 1"))
    except Exception: raise HTTPException(503, "Database unavailable")
    return {"status": "ok", "database": "reachable"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics(db: Session = Depends(get_db)):
    with _counter_lock: snapshot = sorted(_request_counts.items())
    lines = ["# HELP campusloop_http_requests_total Total HTTP requests excluding metrics scrapes", "# TYPE campusloop_http_requests_total counter"]
    for (method, path, status), count in snapshot:
        safe_path = path.replace('\\', '').replace('"', '')
        lines.append(f'campusloop_http_requests_total{{method="{method}",path="{safe_path}",status="{status}"}} {count}')
    active = db.query(BorrowRequest).filter_by(status="active").count()
    pooled = db.query(PoolEntry).join(PoolBatch).filter(PoolBatch.active.is_(True)).count()
    lines += ["# HELP campusloop_active_borrows Active TrustLend loans", "# TYPE campusloop_active_borrows gauge", f"campusloop_active_borrows {active}", "# HELP campusloop_pooled_items Items in active dealer pool", "# TYPE campusloop_pooled_items gauge", f"campusloop_pooled_items {pooled}"]
    return "\n".join(lines) + "\n"
