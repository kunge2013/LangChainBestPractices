"""
Integration tests for API endpoints.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_claim import LedgerClaimRecord
from app.models.ledger_payoff import LedgerPayoffRecord
from app.models.t0 import LedgerT0BaseRecord


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestT0BaseAPI:
    def test_import_and_query(self, client, db_session):
        # Import
        resp = client.post("/api/v1/t0-base/import", json={
            "cutoff_period": "202606",
            "data_list": [
                {
                    "cust_p_code": "P001",
                    "t0_arrears_acct": "100000.00",
                    "t0_arrears_fin": "95000.00",
                    "diff_remark": "历史差异",
                },
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0"
        assert data["data"]["insert_count"] == 1

        # Query
        resp = client.post("/api/v1/t0-base/query", json={
            "cust_p_code": "P001",
            "cutoff_period": "202606",
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0"
        assert data["data"]["total"] == 1
        assert data["data"]["list"][0]["cust_p_code"] == "P001"
        # Decimal may be serialized as string or float
        diff_val = data["data"]["list"][0]["t0_arrears_diff"]
        assert float(diff_val) == 5000.0


class TestLedgerItemAPI:
    def test_query_empty(self, client):
        resp = client.post("/api/v1/ledger-item/query", json={
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "0"
        assert data["data"]["total"] == 0

    def test_query_with_data(self, client, db_session):
        db_session.add(LedgerItemRecord(
            cust_p_code="P001",
            cust_name="客户A",
            acct_name="账户A",
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("5000"),
            cancel_amount=Decimal("5000"),
            acct_subject_code="P041S002",
            is_t0_init="1",
        ))
        db_session.flush()

        resp = client.post("/api/v1/ledger-item/query", json={
            "cust_p_code": "P001",
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 1
        assert data["data"]["list"][0]["cust_p_code"] == "P001"

    def test_init_t0_no_source_data(self, client):
        resp = client.post("/api/v1/ledger-item/init-t0?amount_type=0")
        assert resp.status_code == 400
        data = resp.json()
        assert "无有效的T0欠费数据" in data["message"]


class TestClaimRecordAPI:
    def test_query_claims(self, client, db_session):
        db_session.add(LedgerClaimRecord(
            payment_id=1001,
            finance_id="3001",
            cust_p_code="P001",
            cust_name="客户A",
            acct_name="账户A",
            acct_cd="ACC001",
            deposit_ym="202607",
            deposit_amount=Decimal("50000"),
            used_amount=Decimal("10000"),
            available_balance=Decimal("40000"),
            is_t0_init="0",
            status_cd="1000",
        ))
        db_session.flush()

        resp = client.post("/api/v1/claim-record/query", json={
            "cust_p_code": "P001",
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 1
        assert data["data"]["list"][0]["cust_p_code"] == "P001"


class TestTempClaimAPI:
    def test_query_finance_empty(self, client):
        resp = client.post("/api/v1/tmp-claim/query-finance", json={
            "payment_month": "202607",
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0


class TestWriteOffAPI:
    def test_pre_check_no_data(self, client):
        resp = client.post("/api/v1/write-off/pre-check", json={
            "write_off_month": "202608",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["can_write_off"] is True


class TestPayoffRecordAPI:
    def test_query_empty(self, client):
        resp = client.post("/api/v1/payoff-record/query", json={
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0

    def test_query_with_data(self, client, db_session):
        db_session.add(LedgerPayoffRecord(
            cancel_amount=Decimal("10000"),
            ledger_claim_id=1,
            ledger_item_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1000",
            write_off_date=datetime(2026, 8, 3),
            batch_no="WO202607",
        ))
        db_session.flush()

        resp = client.post("/api/v1/payoff-record/query", json={
            "cust_p_code": "P001",
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 1


class TestReportAPI:
    def test_query_empty(self, client):
        resp = client.post("/api/v1/report/query", json={
            "report_month": "202608",
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0


class TestDiffAPI:
    def test_generate_no_report_raises(self, client):
        resp = client.post("/api/v1/acct-pay-diff/generate", json={
            "period": "202607",
        })
        assert resp.status_code == 400
        data = resp.json()
        assert "报表" in data["message"]

    def test_query_empty(self, client):
        resp = client.post("/api/v1/acct-pay-diff/query", json={
            "page_num": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["total"] == 0
