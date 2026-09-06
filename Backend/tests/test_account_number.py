import threading

from conftest import _create_user

from clients.services import CustomerService
from common.db import SessionLocal


def _payload(name="Test Business"):
    return {
        "customer_type": "BUSINESS",
        "legal_name": name,
        "display_name": name,
        "email": f"{name.lower().replace(' ', '')}@example.com",
        "phone": "+254700000000",
        "industry": "Technology",
        "customer_category": "SME",
        "segment": "Retail",
    }


def _seed_actor():
    return _create_user(
        "seq-actor", "seq-actor@example.com", "SeqPass!123", role_code="SUPER_ADMIN"
    )


def test_first_account_number_is_padded(db):
    actor = _seed_actor()
    customer = CustomerService.create_customer(db, _payload("First Business"), actor)
    assert customer.customer_number == "0001"


def test_account_numbers_are_sequential_and_unique(db):
    actor = _seed_actor()
    numbers = []
    for i in range(5):
        customer = CustomerService.create_customer(
            db, _payload(f"Business {i}"), actor
        )
        numbers.append(customer.customer_number)
    assert len(set(numbers)) == len(numbers)
    assert numbers == ["0001", "0002", "0003", "0004", "0005"]


def test_concurrent_account_number_generation_is_unique():
    actor = _seed_actor()
    results = []
    errors = []

    def worker():
        session = SessionLocal()
        try:
            customer = CustomerService.create_customer(
                session, _payload(f"Thread Business"), actor
            )
            results.append(customer.customer_number)
        except Exception as exc:
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(results) == 10
    assert len(set(results)) == 10
    for number in results:
        assert len(number) >= 4


def test_account_number_is_persistent_and_never_changes(db):
    actor = _seed_actor()
    customer = CustomerService.create_customer(
        db, _payload("Stable Number Business"), actor
    )
    original_number = customer.customer_number

    # Update other fields — account number must not change.
    customer.legal_name = "Renamed Business"
    customer.version += 1
    db.commit()
    db.refresh(customer)
    assert customer.customer_number == original_number

    # Same number visible through every read path.
    from clients.models import Customer
    reloaded = db.get(Customer, customer.customer_id)
    assert reloaded.customer_number == original_number


def test_account_number_visible_consistently_across_views(admin_client, db):
    actor = _seed_actor()
    customer = CustomerService.create_customer(
        db, _payload("Consistent View Business"), actor
    )
    db.commit()
    number = customer.customer_number

    # Detail
    detail = admin_client.get(f"/api/clients/{customer.customer_id}")
    assert detail.status_code == 200
    assert detail.data["account_number"] == number

    # List
    listed = admin_client.get(f"/api/clients?search={number}")
    assert listed.status_code == 200
    assert listed.data["count"] == 1
    assert listed.data["results"][0]["account_number"] == number

    # Legal-name search returns same number
    search = admin_client.get("/api/clients?search=Consistent%20View")
    assert search.status_code == 200
    assert search.data["results"][0]["account_number"] == number
