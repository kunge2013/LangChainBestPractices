"""
Tests for T0 base record (section 11.x).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.exceptions import LedgerError
from app.models.t0 import LedgerT0BaseRecord
from app.schemas.t0 import T0BaseImportItem, T0BaseImportRequest
from app.services.t0_service import import_t0_base, query_t0_base


class TestT0BaseImport:
    def test_import_new_records(self, db_session):
        request = T0BaseImportRequest(
            cutoff_period="202606",
            data_list=[
                T0BaseImportItem(
                    cust_p_code="P001",
                    t0_arrears_acct=Decimal("100000.00"),
                    t0_arrears_fin=Decimal("95000.00"),
                    diff_remark="历史差异",
                ),
                T0BaseImportItem(
                    cust_p_code="P002",
                    t0_arrears_acct=Decimal("50000.00"),
                    t0_arrears_fin=Decimal("50000.00"),
                ),
            ],
        )
        result = import_t0_base(db_session, request)
        assert result.insert_count == 2
        assert result.update_count == 0
        assert result.total_diff_amount == Decimal("5000.00")

    def test_import_upsert_updates_existing(self, db_session):
        request = T0BaseImportRequest(
            cutoff_period="202606",
            data_list=[
                T0BaseImportItem(
                    cust_p_code="P001",
                    t0_arrears_acct=Decimal("100000.00"),
                    t0_arrears_fin=Decimal("95000.00"),
                ),
            ],
        )
        import_t0_base(db_session, request)

        # Re-import with different amounts
        request2 = T0BaseImportRequest(
            cutoff_period="202606",
            data_list=[
                T0BaseImportItem(
                    cust_p_code="P001",
                    t0_arrears_acct=Decimal("120000.00"),
                    t0_arrears_fin=Decimal("100000.00"),
                ),
            ],
        )
        result = import_t0_base(db_session, request2)
        assert result.insert_count == 0
        assert result.update_count == 1

        rec = db_session.query(LedgerT0BaseRecord).filter_by(
            cust_p_code="P001"
        ).first()
        assert rec.t0_arrears_acct == Decimal("120000.00")
        assert rec.t0_arrears_diff == Decimal("20000.00")

    def test_import_empty_cutoff_raises(self, db_session):
        request = T0BaseImportRequest(
            cutoff_period="",
            data_list=[],
        )
        with pytest.raises(LedgerError):
            import_t0_base(db_session, request)

    def test_diff_calculation(self, db_session):
        request = T0BaseImportRequest(
            cutoff_period="202606",
            data_list=[
                T0BaseImportItem(
                    cust_p_code="P001",
                    t0_arrears_acct=Decimal("100000.00"),
                    t0_arrears_fin=Decimal("80000.00"),
                ),
            ],
        )
        import_t0_base(db_session, request)
        rec = db_session.query(LedgerT0BaseRecord).filter_by(
            cust_p_code="P001"
        ).first()
        assert rec.t0_arrears_diff == Decimal("20000.00")


class TestT0BaseQuery:
    def test_query_by_p_code(self, db_session):
        for i in range(5):
            db_session.add(LedgerT0BaseRecord(
                cust_p_code=f"P{i:03d}",
                cutoff_period="202606",
                t0_arrears_acct=Decimal("10000"),
                t0_arrears_fin=Decimal("9000"),
                t0_arrears_diff=Decimal("1000"),
            ))
        db_session.flush()

        total, rows = query_t0_base(db_session, cust_p_code="P000")
        assert total == 1
        assert rows[0].cust_p_code == "P000"

    def test_query_pagination(self, db_session):
        for i in range(25):
            db_session.add(LedgerT0BaseRecord(
                cust_p_code=f"P{i:03d}",
                cutoff_period="202606",
                t0_arrears_acct=Decimal("10000"),
                t0_arrears_fin=Decimal("9000"),
                t0_arrears_diff=Decimal("1000"),
            ))
        db_session.flush()

        total, rows = query_t0_base(db_session, offset=0, limit=10)
        assert total == 25
        assert len(rows) == 10

        total2, rows2 = query_t0_base(db_session, offset=10, limit=10)
        assert len(rows2) == 10

    def test_query_by_cutoff_period(self, db_session):
        db_session.add(LedgerT0BaseRecord(
            cust_p_code="P001",
            cutoff_period="202606",
            t0_arrears_acct=Decimal("10000"),
            t0_arrears_fin=Decimal("9000"),
            t0_arrears_diff=Decimal("1000"),
        ))
        db_session.add(LedgerT0BaseRecord(
            cust_p_code="P001",
            cutoff_period="202607",
            t0_arrears_acct=Decimal("20000"),
            t0_arrears_fin=Decimal("18000"),
            t0_arrears_diff=Decimal("2000"),
        ))
        db_session.flush()

        total, rows = query_t0_base(db_session, cust_p_code="P001", cutoff_period="202606")
        assert total == 1
        assert rows[0].cutoff_period == "202606"

        total2, rows2 = query_t0_base(db_session, cust_p_code="P001")
        assert total2 == 2
