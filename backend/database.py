import os
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./campusloop.db")
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    block: Mapped[str] = mapped_column(String, nullable=False)
    on_time_returns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    late_returns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_lent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    @property
    def trust_score(self):
        return min(100, max(0, 50 + 10 * self.on_time_returns + 5 * self.items_lent - 25 * self.late_returns))


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    condition: Mapped[str] = mapped_column(String, nullable=False)
    original_price: Mapped[int] = mapped_column(Integer, nullable=False)
    months_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    days_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    hostel_block: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, default="Senior Resale", nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    isbn: Mapped[str | None] = mapped_column(String, nullable=True)


class ISBNRecord(Base):
    __tablename__ = "isbn_records"
    isbn: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    original_price: Mapped[int] = mapped_column(Integer, nullable=False)


class Dealer(Base):
    __tablename__ = "dealers"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BorrowRequest(Base):
    __tablename__ = "borrow_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    borrower_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    lender_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    token: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    token_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default="requested", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Purchase(Base):
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    seller_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    payment_status: Mapped[str] = mapped_column(String, default="simulated", nullable=False)


class PoolBatch(Base):
    __tablename__ = "pool_batches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stage: Mapped[str] = mapped_column(String, default="pickup_scheduled", nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    winner_dealer_id: Mapped[str | None] = mapped_column(ForeignKey("dealers.id"))


class PoolEntry(Base):
    __tablename__ = "pool_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("pool_batches.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), nullable=False, unique=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)


class DealerBid(Base):
    __tablename__ = "dealer_bids"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("pool_batches.id"), nullable=False)
    dealer_id: Mapped[str] = mapped_column(ForeignKey("dealers.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PayoutAllocation(Base):
    __tablename__ = "payout_allocations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("pool_batches.id"), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(bind_engine=None, seed=True):
    target = bind_engine or engine
    Base.metadata.create_all(target)
    with target.begin() as conn:
        conn.execute(text("UPDATE items SET condition='Mint' WHERE condition='Excellent'"))
        conn.execute(text("UPDATE items SET condition='Worn' WHERE condition IN ('Fair','Poor')"))
        conn.execute(text("UPDATE dealers SET name='Mysuru Book Syndicate' WHERE id='dealer-green'"))
        conn.execute(text("UPDATE dealers SET name='Deccan Campus Wholesalers' WHERE id='dealer-campus'"))
        conn.execute(text("UPDATE dealers SET name='Kaveri Recycling Corp' WHERE id='dealer-reuse'"))
        conn.execute(text("UPDATE pool_batches SET stage='pickup_scheduled' WHERE stage='collecting'"))
        conn.execute(text("UPDATE pool_batches SET stage='pooled' WHERE stage='bidding'"))
        conn.execute(text("UPDATE items SET mode='₹0 TrustLend' WHERE isbn='9780198069116' AND category='Academic Book' AND available=1 AND NOT EXISTS (SELECT 1 FROM items WHERE mode='₹0 TrustLend') AND NOT EXISTS (SELECT 1 FROM borrow_requests WHERE borrow_requests.item_id=items.id) AND NOT EXISTS (SELECT 1 FROM purchases WHERE purchases.item_id=items.id) AND NOT EXISTS (SELECT 1 FROM pool_entries WHERE pool_entries.item_id=items.id)"))
    if not seed:
        return
    factory = sessionmaker(bind=target, autoflush=False, expire_on_commit=False)
    with factory() as db:
        if db.query(Student).count() == 0:
            db.add_all([Student(id=f"student-{b.lower()}", name=f"Campus Student {b}", block=b) for b in "ABCD"])
        if db.query(Dealer).count() == 0:
            db.add_all([Dealer(id="dealer-green", name="Mysuru Book Syndicate", verified=True), Dealer(id="dealer-campus", name="Deccan Campus Wholesalers", verified=True), Dealer(id="dealer-reuse", name="Kaveri Recycling Corp", verified=True)])
        db.flush()
        if db.query(Item).count() == 0:
            sample = [
                ("Engineering Textbooks", "Academic Book", "Good", 2400, 8, "A", "Senior Resale", "9780131103627"),
                ("Electric Kettle", "Hostel Appliance", "Good", 1800, 10, "A", "Day Transfer", None),
                ("Study Lamp", "Hostel Appliance", "Mint", 900, 5, "A", "Senior Resale", None),
                ("Orthopaedic Mattress", "Hostel Furniture", "Good", 6500, 14, "B", "Day Transfer", None),
                ("Scientific Calculator", "Academic Book", "Mint", 1600, 6, "B", "Senior Resale", "9780471117094"),
                ("Steam Iron Box", "Hostel Appliance", "Worn", 2200, 18, "B", "Day Transfer", None),
                ("Mini Cooler", "Hostel Appliance", "Good", 8500, 12, "C", "Senior Resale", None),
                ("Engineering Drafter", "Academic Book", "Good", 1300, 9, "C", "Senior Resale", None),
                ("Lab Coat", "Academic Book", "Good", 1100, 7, "C", "Day Transfer", None),
                ("Extension Board", "Hostel Appliance", "Worn", 750, 16, "D", "Senior Resale", None),
                ("Engineering Mathematics Textbook", "Academic Book", "Good", 1900, 11, "D", "₹0 TrustLend", "9780198069116"),
                ("Hostel Study Chair", "Hostel Furniture", "Worn", 2800, 20, "D", "Day Transfer", None),
            ]
            for title, category, condition, price, months, block, mode, isbn in sample:
                db.add(Item(title=title, category=category, condition=condition, original_price=price, months_used=months, owner_id=f"student-{block.lower()}", hostel_block=block, mode=mode, isbn=isbn, days_used=0))
        if db.query(ISBNRecord).count() == 0:
            db.add_all([ISBNRecord(isbn="9780131103627", title="Engineering Textbooks", category="Academic Book", original_price=2400), ISBNRecord(isbn="9780471117094", title="Scientific Calculator", category="Academic Book", original_price=1600), ISBNRecord(isbn="9780198069116", title="Engineering Mathematics Textbook", category="Academic Book", original_price=1900)])
        if db.query(PoolBatch).count() == 0:
            db.add(PoolBatch(stage="pickup_scheduled", active=True))
        db.commit()
