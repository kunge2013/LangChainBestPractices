"""
Tests for T0 source data import (section 2.5).
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.exceptions import LedgerError
from app.models.t0 import LedgerT0SourceRecord
from app.services.t0_service import _parse_excel_row, import_source_data


class TestParseExcelRow:
    def test_parse_valid_row(self):
        row = {
            "公司（公司代码）": "A000",
            "年（财年）": "2026",
            "凭证号码（SAP凭证号)": "SAP001",
            "项（SAP凭证行项）": "001",
            "期间": "6",
            "过帐日期": "2026-06-15",
            "对象(客户编码（M码）)": "M001",
            "本位币金额（正数为欠费金额，负数为预存金额）": "1000.00",
        }
        dto = _parse_excel_row(row)
        assert dto is not None
        assert dto.company_code == "A000"
        assert dto.fiscal_year == "2026"
        assert dto.during == "6"
        assert dto.bill_ym == "202606"
        assert dto.amount == Decimal("1000.00")
        assert dto.amount_type == "0"  # positive -> arrears
        assert dto.cust_m_code == "M001"

    def test_parse_negative_amount_is_prepay(self):
        row = {
            "公司（公司代码）": "A000",
            "年（财年）": "2026",
            "期间": "3",
            "对象(客户编码（M码）)": "M001",
            "本位币金额（正数为欠费金额，负数为预存金额）": "-500.00",
        }
        dto = _parse_excel_row(row)
        assert dto is not None
        assert dto.amount == Decimal("-500.00")
        assert dto.amount_type == "1"  # negative -> prepay

    def test_parse_skip_empty_company(self):
        row = {
            "公司（公司代码）": "",
            "年（财年）": "2026",
            "期间": "6",
            "对象(客户编码（M码）)": "M001",
            "本位币金额（正数为欠费金额，负数为预存金额）": "1000.00",
        }
        dto = _parse_excel_row(row)
        assert dto is None

    def test_parse_during_padding(self):
        row = {
            "公司（公司代码）": "A000",
            "年（财年）": "2026",
            "期间": "3",
            "对象(客户编码（M码）)": "M001",
            "本位币金额（正数为欠费金额，负数为预存金额）": "100",
        }
        dto = _parse_excel_row(row)
        assert dto.bill_ym == "202603"

    def test_parse_during_two_digits(self):
        row = {
            "公司（公司代码）": "A000",
            "年（财年）": "2026",
            "期间": "12",
            "对象(客户编码（M码）)": "M001",
            "本位币金额（正数为欠费金额，负数为预存金额）": "100",
        }
        dto = _parse_excel_row(row)
        assert dto.bill_ym == "202612"


class TestImportSourceData:
    def test_import_valid_rows(self, db_session):
        rows = [
            {
                "公司（公司代码）": "A000",
                "年（财年）": "2026",
                "凭证号码（SAP凭证号)": "SAP001",
                "项（SAP凭证行项）": "001",
                "期间": "6",
                "过帐日期": "2026-06-15",
                "对象(客户编码（M码）)": "M001",
                "本位币金额（正数为欠费金额，负数为预存金额）": "1000.00",
            },
            {
                "公司（公司代码）": "A000",
                "年（财年）": "2026",
                "期间": "7",
                "对象(客户编码（M码）)": "M002",
                "本位币金额（正数为欠费金额，负数为预存金额）": "-500.00",
            },
        ]
        count = import_source_data(db_session, rows)
        assert count == 2

        records = db_session.query(LedgerT0SourceRecord).all()
        assert len(records) == 2
        assert records[0].bill_ym == "202606"
        assert records[0].amount_type == "0"
        assert records[1].bill_ym == "202607"
        assert records[1].amount_type == "1"

    def test_import_skips_empty_company(self, db_session):
        rows = [
            {"公司（公司代码）": "", "年（财年）": "2026", "期间": "6",
             "对象(客户编码（M码）)": "M001",
             "本位币金额（正数为欠费金额，负数为预存金额）": "1000.00"},
            {"公司（公司代码）": "A000", "年（财年）": "2026", "期间": "6",
             "对象(客户编码（M码）)": "M002",
             "本位币金额（正数为欠费金额，负数为预存金额）": "500.00"},
        ]
        count = import_source_data(db_session, rows)
        assert count == 1

    def test_import_empty_raises(self, db_session):
        rows = [{"公司（公司代码）": "", "年（财年）": "2026"}]
        with pytest.raises(LedgerError):
            import_source_data(db_session, rows)

    def test_import_batch_over_1000(self, db_session):
        """Test that batch flushing works for large datasets."""
        rows = [
            {
                "公司（公司代码）": "A000",
                "年（财年）": "2026",
                "期间": "6",
                "对象(客户编码（M码）)": f"M{i:04d}",
                "本位币金额（正数为欠费金额，负数为预存金额）": "100.00",
            }
            for i in range(1500)
        ]
        count = import_source_data(db_session, rows)
        assert count == 1500
        assert db_session.query(LedgerT0SourceRecord).count() == 1500
