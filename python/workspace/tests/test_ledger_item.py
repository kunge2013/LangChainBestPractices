"""
Tests for ledger item service (sections 3.1 - 3.5).
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.exceptions import LedgerError
from app.models.ledger_item import LedgerItemRecord
from app.models.t0 import LedgerT0SourceRecord
from app.schemas.ledger_item import EdaItemDTO
from app.services.ledger_item_service import (
    import_eda_data,
    import_t0_arrears,
    query_ledger_items,
    refresh_eda_acct_attr,
    refresh_t0_acct_attr,
)


class TestT0ArrearsImport:
    def _setup_source_data(self, db_session, count=5):
        for i in range(count):
            db_session.add(LedgerT0SourceRecord(
                cust_p_code=f"P{i:03d}",
                cust_m_code=f"M{i:03d}",
                company_code="A000",
                fiscal_year="2026",
                during="6",
                bill_ym="202606",
                amount=Decimal("1000.00"),
                amount_type="0",
                voucher_date=date(2026, 6, 15),
                acct_subject_code="P041S002",
            ))
        db_session.flush()

    def test_import_success(self, db_session):
        self._setup_source_data(db_session, 5)
        result = import_t0_arrears(db_session, "0")
        assert result.success_count == 5
        assert result.source_count == 5

        records = db_session.query(LedgerItemRecord).all()
        assert len(records) == 5
        assert records[0].is_t0_init == "1"
        assert records[0].item_type == "0"
        assert records[0].rmb_all == Decimal("1000.00")
        assert records[0].arrears_amount == Decimal("1000.00")
        assert records[0].cancel_amount == Decimal("0")
        assert records[0].cust_name is None  # left empty for refresh

    def test_import_wrong_amount_type_raises(self, db_session):
        with pytest.raises(LedgerError):
            import_t0_arrears(db_session, "1")

    def test_import_no_source_data_raises(self, db_session):
        with pytest.raises(LedgerError):
            import_t0_arrears(db_session, "0")

    def test_import_excludes_prepay_data(self, db_session):
        """AMOUNT_TYPE='1' should NOT be imported."""
        db_session.add(LedgerT0SourceRecord(
            cust_p_code="P001",
            cust_m_code="M001",
            bill_ym="202606",
            amount=Decimal("-500.00"),
            amount_type="1",
            acct_subject_code="P041S002",
        ))
        db_session.add(LedgerT0SourceRecord(
            cust_p_code="P002",
            cust_m_code="M002",
            bill_ym="202606",
            amount=Decimal("1000.00"),
            amount_type="0",
            acct_subject_code="P041S002",
        ))
        db_session.flush()

        result = import_t0_arrears(db_session, "0")
        assert result.success_count == 1
        records = db_session.query(LedgerItemRecord).all()
        assert len(records) == 1
        assert records[0].cust_p_code == "P002"

    def test_import_large_batch(self, db_session):
        """Test cursor pagination with > 5000 records."""
        self._setup_source_data(db_session, 6000)
        result = import_t0_arrears(db_session, "0")
        assert result.success_count == 6000
        assert db_session.query(LedgerItemRecord).count() == 6000


class TestEdaImport:
    def test_import_success(self, db_session):
        eda_data = {
            100: [
                EdaItemDTO(
                    acct_subject_code="P041S002",
                    rmb_all=Decimal("1000.00"),
                    arrears_amount=Decimal("1000.00"),
                    acct_id=100,
                    bill_ym="202608",
                    item_id=1001,
                    item_type="1",
                ),
                EdaItemDTO(
                    acct_subject_code="P041S003",
                    rmb_all=Decimal("2000.00"),
                    arrears_amount=Decimal("2000.00"),
                    acct_id=100,
                    bill_ym="202608",
                    item_id=1002,
                    item_type="2",
                ),
            ],
        }
        result = import_eda_data(db_session, "202608", eda_data)
        assert result.insert_count == 2
        assert result.delete_count == 0
        assert result.total_amount == Decimal("3000.00")
        assert result.failed_acct_count == 0

        records = db_session.query(LedgerItemRecord).filter_by(
            is_t0_init="0"
        ).all()
        assert len(records) == 2
        assert records[0].item_type == "1"
        assert records[1].item_type == "2"

    def test_import_idempotent_delete_reinsert(self, db_session):
        eda_data = {
            100: [
                EdaItemDTO(
                    acct_subject_code="P041S002",
                    rmb_all=Decimal("1000.00"),
                    arrears_amount=Decimal("1000.00"),
                    acct_id=100,
                    bill_ym="202608",
                    item_id=1001,
                    item_type="1",
                ),
            ],
        }
        import_eda_data(db_session, "202608", eda_data)

        # Re-import should delete old + insert new
        eda_data2 = {
            100: [
                EdaItemDTO(
                    acct_subject_code="P041S003",
                    rmb_all=Decimal("2000.00"),
                    arrears_amount=Decimal("2000.00"),
                    acct_id=100,
                    bill_ym="202608",
                    item_id=1002,
                    item_type="2",
                ),
            ],
        }
        result = import_eda_data(db_session, "202608", eda_data2)
        assert result.delete_count == 1
        assert result.insert_count == 1

        records = db_session.query(LedgerItemRecord).filter_by(
            is_t0_init="0"
        ).all()
        assert len(records) == 1
        assert records[0].acct_subject_code == "P041S003"

    def test_import_empty_raises(self, db_session):
        with pytest.raises(LedgerError):
            import_eda_data(db_session, "202608", {})

    def test_import_empty_bill_ym_raises(self, db_session):
        with pytest.raises(LedgerError):
            import_eda_data(db_session, "", {})


class TestLedgerItemQuery:
    def _setup_items(self, db_session):
        for i in range(5):
            db_session.add(LedgerItemRecord(
                cust_p_code=f"P{i:03d}",
                cust_name=f"客户{i}",
                acct_name=f"账户{i}",
                acct_cd=f"ACC{i:03d}",
                bill_ym="202606",
                batch_no="202608",
                item_type="0",
                rmb_all=Decimal("10000"),
                arrears_amount=Decimal("5000"),
                cancel_amount=Decimal("5000"),
                acct_subject_code="P041S002",
                is_t0_init="1" if i < 3 else "0",
            ))
        db_session.flush()

    def test_query_all(self, db_session):
        self._setup_items(db_session)
        page = query_ledger_items(db_session)
        assert page.total == 5
        assert len(page.list) == 5

    def test_query_by_p_code(self, db_session):
        self._setup_items(db_session)
        page = query_ledger_items(db_session, cust_p_code="P000")
        assert page.total == 1
        assert page.list[0].cust_p_code == "P000"

    def test_query_by_acct_name_like(self, db_session):
        self._setup_items(db_session)
        page = query_ledger_items(db_session, acct_name="账户0")
        assert page.total == 1

    def test_query_by_is_t0_init(self, db_session):
        self._setup_items(db_session)
        page = query_ledger_items(db_session, is_t0_init="1")
        assert page.total == 3

        page2 = query_ledger_items(db_session, is_t0_init="0")
        assert page2.total == 2

    def test_query_by_arrears_period(self, db_session):
        self._setup_items(db_session)
        page = query_ledger_items(db_session, arrears_period="202606")
        assert page.total == 5

    def test_query_pagination(self, db_session):
        self._setup_items(db_session)
        page = query_ledger_items(db_session, offset=0, limit=2)
        assert page.total == 5
        assert len(page.list) == 2

        page2 = query_ledger_items(db_session, offset=2, limit=2)
        assert len(page2.list) == 2


class TestT0AcctRefresh:
    def _setup_t0_items(self, db_session, p_codes):
        for p in p_codes:
            db_session.add(LedgerItemRecord(
                cust_p_code=p,
                cust_name=None,
                acct_name=None,
                acct_cd=None,
                bill_ym="202606",
                batch_no="202608",
                item_type="0",
                rmb_all=Decimal("1000"),
                arrears_amount=Decimal("1000"),
                acct_subject_code="P041S002",
                is_t0_init="1",
            ))
        db_session.flush()

    def test_refresh_success(self, db_session):
        p_codes = ["P001", "P002", "P003"]
        self._setup_t0_items(db_session, p_codes)

        acct_info = {
            "P001": {"cust_name": "客户A", "acct_name": "账户A",
                     "acct_cd": "ACC001", "acct_id": 100},
            "P002": {"cust_name": "客户B", "acct_name": "账户B",
                     "acct_cd": "ACC002", "acct_id": 200},
            "P003": {"cust_name": "客户C", "acct_name": "账户C",
                     "acct_cd": "ACC003", "acct_id": 300},
        }
        result = refresh_t0_acct_attr(db_session, acct_info_lookup=acct_info)
        assert result.refreshed_p_code_count == 3
        assert result.unrefreshed_p_code_count == 0

        rec = db_session.query(LedgerItemRecord).filter_by(
            cust_p_code="P001"
        ).first()
        assert rec.cust_name == "客户A"
        assert rec.acct_cd == "ACC001"
        assert rec.acct_id == 100

    def test_refresh_no_match(self, db_session):
        p_codes = ["P001", "P002"]
        self._setup_t0_items(db_session, p_codes)

        # Empty lookup - no matches
        result = refresh_t0_acct_attr(db_session, acct_info_lookup={})
        assert result.refreshed_p_code_count == 0
        assert result.unrefreshed_p_code_count == 2

    def test_refresh_no_pending(self, db_session):
        result = refresh_t0_acct_attr(db_session)
        assert result.refreshed_p_code_count == 0
        assert result.unrefreshed_p_code_count == 0

    def test_refresh_partial_match(self, db_session):
        p_codes = ["P001", "P002", "P003"]
        self._setup_t0_items(db_session, p_codes)

        acct_info = {
            "P001": {"cust_name": "客户A", "acct_name": "账户A",
                     "acct_cd": "ACC001", "acct_id": 100},
        }
        result = refresh_t0_acct_attr(db_session, acct_info_lookup=acct_info)
        assert result.refreshed_p_code_count == 1
        assert result.unrefreshed_p_code_count == 2


class TestEdaAcctRefresh:
    def _setup_eda_items(self, db_session, acct_ids):
        for aid in acct_ids:
            db_session.add(LedgerItemRecord(
                cust_p_code=None,
                cust_name=None,
                acct_name=None,
                acct_cd=None,
                acct_id=aid,
                bill_ym="202608",
                batch_no="202608",
                item_type="1",
                rmb_all=Decimal("1000"),
                arrears_amount=Decimal("1000"),
                acct_subject_code="P041S002",
                is_t0_init="0",
            ))
        db_session.flush()

    def test_refresh_success(self, db_session):
        acct_ids = [100, 200]
        self._setup_eda_items(db_session, acct_ids)

        acct_info = {
            100: {"cust_name": "客户A", "party_nbr": "P001",
                  "acct_name": "账户A", "acct_cd": "ACC001"},
            200: {"cust_name": "客户B", "party_nbr": "P002",
                  "acct_name": "账户B", "acct_cd": "ACC002"},
        }
        result = refresh_eda_acct_attr(
            db_session, "202608", "202608", acct_info_lookup=acct_info
        )
        assert result.refreshed_acct_id_count == 2

        rec = db_session.query(LedgerItemRecord).filter_by(
            acct_id=100
        ).first()
        assert rec.cust_p_code == "P001"
        assert rec.cust_name == "客户A"
        assert rec.acct_cd == "ACC001"

    def test_refresh_no_pending(self, db_session):
        result = refresh_eda_acct_attr(db_session, "202608", "202608")
        assert result.refreshed_acct_id_count == 0
