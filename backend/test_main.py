import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import main
from database import Base, get_db, init_db, Student, Item, Dealer, PoolBatch


@pytest.fixture
def client():
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    init_db(test_engine)
    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()
    main.app.dependency_overrides[get_db] = override_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def valuation(client, category="Academic Book", condition="Mint", price=1000, months=10, days=0, **extra):
    return client.get("/api/valuate", params={"category": category, "condition": condition, "original_price": price, "months_used": months, "days_used": days, **extra})


def test_category_rates_conditions_and_resale_floor(client):
    assert valuation(client).json()["senior_resale_price"] == 400
    assert valuation(client, condition="Good").json()["senior_resale_price"] == 360
    assert valuation(client, condition="Worn").json()["senior_resale_price"] == 320
    assert valuation(client, category="Hostel Appliance").json()["senior_resale_price"] == 600
    assert valuation(client, category="Hostel Furniture").json()["senior_resale_price"] == 650
    assert valuation(client, category="Hostel Appliance", price=1000, months=36, condition="Worn").json()["senior_resale_price"] == 250
    assert valuation(client, condition="Excellent").status_code == 422


def test_day_transfer_zero_micro_depreciation_and_floor(client):
    assert valuation(client, days=0).json()["day_transfer_price"] == 1000
    assert valuation(client, days=10).json()["day_transfer_price"] == 970
    assert valuation(client, price=1000, days=90).json()["day_transfer_price"] == 730
    assert valuation(client, price=1000, days=365).json()["day_transfer_price"] == 500


def test_trust_formula_saturation_and_threshold_boundaries(client):
    assert valuation(client, on_time_returns=2).json()["trust_score"] == 70
    assert valuation(client, late_returns=2).json()["trust_score"] == 0
    assert valuation(client, on_time_returns=20).json()["trust_score"] == 100
    assert valuation(client, category="Academic Book").json()["trustlend_eligible"] is True
    assert valuation(client, category="Hostel Appliance").json()["trustlend_eligible"] is False
    assert valuation(client, category="Hostel Furniture", on_time_returns=4).json()["trustlend_eligible"] is True


def test_qr_lifecycle_due_scores_unavailable_and_replay(client):
    item = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    lender_id = item["owner_id"]
    borrower_id = "student-a" if lender_id != "student-a" else "student-b"
    requested = client.post("/api/trustlend/borrow", json={"item_id": item["id"], "borrower_id": borrower_id, "lender_id": lender_id})
    assert requested.status_code == 201
    token = requested.json()["token"]
    assert len(token) >= 20
    assert client.post("/api/trustlend/borrow", json={"item_id": item["id"], "borrower_id": borrower_id, "lender_id": lender_id}).status_code == 409
    handover = client.post("/api/trustlend/handover", json={"token": token})
    assert handover.json()["status"] == "active"
    from datetime import datetime
    due = datetime.fromisoformat(handover.json()["due_at"])
    started = datetime.fromisoformat(handover.json()["started_at"])
    assert (due - started).days == 7
    assert client.post("/api/trustlend/handover", json={"token": token}).status_code == 409
    returned = client.post("/api/trustlend/return", json={"token": token})
    assert returned.status_code == 200
    assert returned.json()["borrower_trust_score"] == 60
    assert returned.json()["lender_trust_score"] == 55
    assert client.post("/api/trustlend/return", json={"token": token}).status_code == 409
    loans = client.get("/api/trustlend/loans", params={"student_id": borrower_id}).json()
    assert loans[0]["role"] == "borrower" and "token" not in loans[0]


def test_listing_filters_owner_names_and_isbn(client):
    all_items = client.get("/api/items").json()
    assert len(all_items) == 12
    assert all_items[0]["owner_name"] == "Campus Student A"
    assert all_items[0]["senior_resale_price"] > 0
    filtered = client.get("/api/items", params={"category": "Academic Book", "mode": "Senior Resale", "hostel_block": "B"}).json()
    assert len(filtered) == 1 and filtered[0]["title"] == "Scientific Calculator"
    assert client.get("/api/isbn/9780131103627").json()["title"] == "Engineering Textbooks"
    assert client.get("/api/isbn/missing").status_code == 404
    assert client.post("/api/items", json={"title":"Invalid","owner_id":"student-a","category":"Academic Book","condition":"Fair","original_price":1,"months_used":0,"hostel_block":"A"}).status_code == 422


def test_purchase_identity_amount_status_history_and_rejections(client):
    item = next(row for row in client.get("/api/items").json() if row["mode"] == "Senior Resale")
    buyer = "student-d" if item["owner_id"] != "student-d" else "student-c"
    response = client.post("/api/purchases", json={"item_id": item["id"], "buyer_id": buyer})
    assert response.status_code == 201
    order = response.json()
    assert order["buyer_id"] == buyer and order["seller_id"] == item["owner_id"]
    assert order["amount"] == item["senior_resale_price"] and order["payment_status"] == "simulated"
    assert client.get("/api/purchases", params={"student_id": buyer}).json()[0]["order_id"] == order["order_id"]
    assert client.post("/api/purchases", json={"item_id": item["id"], "buyer_id": buyer}).status_code == 409
    own = next(row for row in client.get("/api/items").json() if row["owner_id"] == "student-a" and row["available"])
    assert client.post("/api/purchases", json={"item_id": own["id"], "buyer_id": "student-a"}).status_code == 400
    free = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    assert client.post("/api/purchases", json={"item_id": free["id"], "buyer_id": "student-b"}).status_code == 400


def test_dealer_names_bids_stage_labels_and_exact_allocations(client):
    initial = client.get("/api/dealer-pool").json()
    assert initial["stage"] == "pickup_scheduled"
    assert initial["stage_label"] == "Hostel Pickup Scheduled"
    items = client.get("/api/items").json()[:3]
    for row in items:
        assert client.post("/api/dealer-pool/add", json={"item_id": row["id"]}).status_code == 200
    assert client.post("/api/dealer-pool/add", json={"item_id": items[0]["id"]}).status_code == 409
    pooled = client.post("/api/dealer-pool/advance")
    assert pooled.json()["stage"] == "pooled"
    assert client.post("/api/dealer-pool/advance").status_code == 409
    assert client.post("/api/dealer-pool/bid", json={"dealer_id":"dealer-green", "amount":3000}).status_code == 200
    assert client.post("/api/dealer-pool/bid", json={"dealer_id":"dealer-campus", "amount":3000}).status_code == 400
    client.post("/api/dealer-pool/bid", json={"dealer_id":"dealer-campus", "amount":3500})
    state = client.get("/api/dealer-pool").json()
    assert {bid["dealer_name"] for bid in state["bids"]} == {"Mysuru Book Syndicate", "Deccan Campus Wholesalers"}
    assert state["estimate_ratio"] == 2.8
    won = client.post("/api/dealer-pool/advance").json()
    assert won["stage"] == "auction_won" and won["winner"]["dealer_id"] == "dealer-campus"
    final = client.post("/api/dealer-pool/advance").json()
    assert final["stage"] == "final" and sum(row["amount"] for row in final["payouts"]) == 3500
    assert all(row["payment_status"] == "simulated" for row in final["payouts"])
    assert client.get("/api/dealer-pool").json()["stage"] == "final"
    assert client.post("/api/dealer-pool/advance").status_code == 409


def test_health_metrics_counter_gauges_and_no_scrape_feedback(client):
    assert client.get("/health").json()["status"] == "ok"
    client.get("/api/items")
    before = client.get("/metrics").text
    assert "campusloop_http_requests_total" in before
    assert "campusloop_active_borrows 0" in before
    assert "campusloop_pooled_items 0" in before
    assert client.get("/metrics").text == before


def test_demo_student_roster_exposes_role_and_trust_fields(client):
    roster = client.get("/api/students").json()
    assert [(student["id"], student["block"]) for student in roster] == [
        ("student-a", "A"), ("student-b", "B"), ("student-c", "C"), ("student-d", "D")
    ]
    assert all(student["name"].startswith("Campus Student") for student in roster)
    assert all(student["trust_score"] == 50 for student in roster)
    assert all({"on_time_returns", "late_returns", "items_lent"} <= student.keys() for student in roster)


def test_day_transfer_purchase_uses_micro_depreciation_and_seller_history(client):
    listing = client.post("/api/items", json={
        "title": "Day transfer history case",
        "owner_id": "student-a",
        "category": "Hostel Appliance",
        "condition": "Good",
        "original_price": 1000,
        "months_used": 0,
        "days_used": 10,
        "hostel_block": "A",
        "mode": "Day Transfer"
    })
    assert listing.status_code == 201
    assert listing.json()["day_transfer_price"] == 970
    purchase = client.post("/api/purchases", json={"item_id": listing.json()["id"], "buyer_id": "student-b"})
    assert purchase.status_code == 201
    assert purchase.json()["amount"] == 970
    assert purchase.json()["seller_name"] == "Campus Student A"
    seller_history = client.get("/api/purchases", params={"student_id": "student-a"}).json()
    assert len(seller_history) == 1
    assert seller_history[0]["order_id"] == purchase.json()["order_id"]
    assert seller_history[0]["buyer_id"] == "student-b"


def test_purchase_unknown_student_and_item_ids_return_not_found(client):
    item = next(row for row in client.get("/api/items").json() if row["mode"] == "Senior Resale")
    assert client.post("/api/purchases", json={"item_id": item["id"], "buyer_id": "missing-student"}).status_code == 404
    assert client.post("/api/purchases", json={"item_id": 9999, "buyer_id": "student-b"}).status_code == 404
    assert client.get("/api/purchases", params={"student_id": "missing-student"}).status_code == 404


def test_lender_loan_history_includes_participants_without_qr_token(client):
    item = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    requested = client.post("/api/trustlend/borrow", json={
        "item_id": item["id"], "borrower_id": "student-a", "lender_id": item["owner_id"]
    })
    assert requested.status_code == 201
    lender_history = client.get("/api/trustlend/loans", params={"student_id": item["owner_id"]}).json()
    assert len(lender_history) == 1
    loan = lender_history[0]
    assert loan["role"] == "lender"
    assert loan["borrower_name"] == "Campus Student A"
    assert loan["lender_name"] == item["owner_name"]
    assert loan["status"] == "requested"
    assert "token" not in loan
    assert "token_expires_at" not in loan


def test_trustlend_requires_free_listing_owner_and_distinct_borrower(client):
    trust_item = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    other_lender = "student-a" if trust_item["owner_id"] != "student-a" else "student-b"
    assert client.post("/api/trustlend/borrow", json={
        "item_id": trust_item["id"], "borrower_id": "student-a", "lender_id": other_lender
    }).status_code == 400
    assert client.post("/api/trustlend/borrow", json={
        "item_id": trust_item["id"], "borrower_id": trust_item["owner_id"], "lender_id": trust_item["owner_id"]
    }).status_code == 400
    sale_item = next(row for row in client.get("/api/items").json() if row["mode"] == "Senior Resale")
    borrower = "student-d" if sale_item["owner_id"] != "student-d" else "student-c"
    assert client.post("/api/trustlend/borrow", json={
        "item_id": sale_item["id"], "borrower_id": borrower, "lender_id": sale_item["owner_id"]
    }).status_code == 400


def test_hostel_trustlend_threshold_uses_persisted_borrower_score(client):
    listing = client.post("/api/items", json={
        "title": "Threshold appliance",
        "owner_id": "student-b",
        "category": "Hostel Appliance",
        "condition": "Good",
        "original_price": 1200,
        "months_used": 0,
        "days_used": 0,
        "hostel_block": "B",
        "mode": "₹0 TrustLend"
    }).json()
    denied = client.post("/api/trustlend/borrow", json={
        "item_id": listing["id"], "borrower_id": "student-a", "lender_id": "student-b"
    })
    assert denied.status_code == 403
    book = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    for expected in (60, 70):
        request = client.post("/api/trustlend/borrow", json={
            "item_id": book["id"], "borrower_id": "student-a", "lender_id": book["owner_id"]
        }).json()
        client.post("/api/trustlend/handover", json={"token": request["token"]})
        result = client.post("/api/trustlend/return", json={"token": request["token"]})
        assert result.json()["borrower_trust_score"] == expected
    assert client.post("/api/trustlend/borrow", json={
        "item_id": listing["id"], "borrower_id": "student-a", "lender_id": "student-b"
    }).status_code == 201


def test_expired_qr_token_cannot_handover(client, monkeypatch):
    from datetime import timedelta

    item = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    request = client.post("/api/trustlend/borrow", json={
        "item_id": item["id"], "borrower_id": "student-a", "lender_id": item["owner_id"]
    }).json()
    actual_now = main.utcnow
    monkeypatch.setattr(main, "utcnow", lambda: actual_now() + timedelta(hours=25))
    response = client.post("/api/trustlend/handover", json={"token": request["token"]})
    assert response.status_code == 410
    assert response.json()["detail"] == "QR token has expired"


def test_late_return_decrements_trust_and_persists_history(client, monkeypatch):
    from datetime import timedelta

    item = next(row for row in client.get("/api/items").json() if row["mode"] == "₹0 TrustLend")
    request = client.post("/api/trustlend/borrow", json={
        "item_id": item["id"], "borrower_id": "student-a", "lender_id": item["owner_id"]
    }).json()
    client.post("/api/trustlend/handover", json={"token": request["token"]})
    actual_now = main.utcnow
    monkeypatch.setattr(main, "utcnow", lambda: actual_now() + timedelta(days=8))
    returned = client.post("/api/trustlend/return", json={"token": request["token"]})
    assert returned.json()["borrower_trust_score"] == 25
    assert returned.json()["lender_trust_score"] == 55
    history = client.get("/api/trustlend/loans", params={"student_id": "student-a"}).json()
    assert history[0]["status"] == "returned"
    assert history[0]["returned_at"] is not None


def test_legacy_label_migration_preserves_existing_rows_and_is_idempotent():
    test_engine = create_engine("sqlite://")
    Base.metadata.create_all(test_engine)
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as db:
        db.add(Student(id="legacy-a", name="Legacy Resident", block="A"))
        db.add(Dealer(id="dealer-green", name="GreenLoop Recyclers", verified=True))
        db.add(PoolBatch(stage="bidding", active=True))
        db.flush()
        db.add(Item(
            title="Saved legacy book",
            category="Academic Book",
            condition="Excellent",
            original_price=800,
            months_used=2,
            owner_id="legacy-a",
            hostel_block="A",
            mode="Day Transfer",
            days_used=4
        ))
        db.commit()
    init_db(test_engine, seed=False)
    init_db(test_engine, seed=False)
    with TestingSession() as db:
        item = db.query(Item).one()
        assert item.title == "Saved legacy book"
        assert item.condition == "Mint"
        assert item.mode == "Day Transfer" and item.days_used == 4
        assert db.query(Student).count() == 1
        assert db.get(Dealer, "dealer-green").name == "Mysuru Book Syndicate"
        assert db.query(PoolBatch).one().stage == "pooled"
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def test_three_dealer_names_and_remainder_go_to_sorted_final_owner(client):
    items = client.get("/api/items").json()
    selected = [next(row for row in items if row["owner_id"] == owner) for owner in ("student-a", "student-b", "student-c")]
    for item in selected:
        client.post("/api/dealer-pool/add", json={"item_id": item["id"]})
    assert client.post("/api/dealer-pool/advance").json()["stage"] == "pooled"
    for dealer_id, amount in (("dealer-green", 4000), ("dealer-campus", 4500), ("dealer-reuse", 5000)):
        assert client.post("/api/dealer-pool/bid", json={"dealer_id": dealer_id, "amount": amount}).status_code == 200
    names = {bid["dealer_name"] for bid in client.get("/api/dealer-pool").json()["bids"]}
    assert names == {"Mysuru Book Syndicate", "Deccan Campus Wholesalers", "Kaveri Recycling Corp"}
    assert client.post("/api/dealer-pool/advance").json()["winner"]["dealer_id"] == "dealer-reuse"
    final = client.post("/api/dealer-pool/advance").json()
    assert {row["owner_id"]: row["amount"] for row in final["payouts"]} == {
        "student-a": 689,
        "student-b": 1867,
        "student-c": 2444
    }
    assert sum(row["amount"] for row in final["payouts"]) == 5000


def test_unverified_dealer_cannot_bid_on_pooled_batch(client):
    dependency = main.app.dependency_overrides[get_db]()
    db = next(dependency)
    db.add(Dealer(id="dealer-unverified", name="Unverified Dealer", verified=False))
    db.commit()
    dependency.close()
    item = client.get("/api/items").json()[0]
    client.post("/api/dealer-pool/add", json={"item_id": item["id"]})
    assert client.post("/api/dealer-pool/advance").json()["stage"] == "pooled"
    rejected = client.post("/api/dealer-pool/bid", json={"dealer_id": "dealer-unverified", "amount": 1000})
    assert rejected.status_code == 403
    assert rejected.json()["detail"] == "Dealer is not verified"


def test_block_leaderboard_breaks_equal_scores_alphabetically(client):
    leaderboard = client.get("/api/leaderboard").json()["blocks"]
    assert [row["block"] for row in leaderboard] == ["A", "B", "C", "D"]
    assert all(row["trust_score"] == 50 and row["on_time_returns"] == 0 for row in leaderboard)


def test_listing_accepts_exact_conditions_and_returns_computed_owner_values(client):
    for condition, expected in (("Mint", 1000), ("Good", 900), ("Worn", 800)):
        response = client.post("/api/items", json={
            "title": f"Condition {condition}",
            "owner_id": "student-c",
            "category": "Academic Book",
            "condition": condition,
            "original_price": 1000,
            "months_used": 0,
            "days_used": 0,
            "hostel_block": "C",
            "mode": "Senior Resale"
        })
        assert response.status_code == 201
        item = response.json()
        assert item["condition"] == condition
        assert item["owner_name"] == "Campus Student C"
        assert item["senior_resale_price"] == expected
        assert item["day_transfer_price"] == 1000
