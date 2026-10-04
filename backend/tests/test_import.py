from datetime import datetime
from io import BytesIO
from pathlib import Path
import sys

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server
from fastapi.testclient import TestClient


def test_parse_ledger_tables_reads_party_opening_balance_and_repeated_party_rows():
    tables = [
        [
            ["Party", "Phone", "Opening Balance"],
            ["Asha Stores", "+91 9876543210", "₹2,000"],
        ],
        [
            ["Party", "Date", "Amount", "Type", "Description"],
            ["Asha Stores", "01/04/2026", "1,250.50", "Gave", "Stock"],
            ["", "02/04/2026", "250", "Got", "Payment"],
        ],
    ]

    result = server.parse_ledger_tables(tables)

    assert result is not None
    assert result["success"] is True
    assert result["parties"] == [{
        "name": "Asha Stores",
        "phone": "9876543210",
        "type": "CUSTOMER",
        "openingBalance": 2000.0,
    }]
    assert [(tx["amount"], tx["type"], tx["note"]) for tx in result["transactions"]] == [
        (1250.5, "DEBIT", "Stock"),
        (250.0, "CREDIT", "Payment"),
    ]
    assert result["transactions"][0]["date"].startswith("2026-04-01")


def test_parse_ledger_tables_supports_separate_debit_and_credit_columns():
    result = server.parse_ledger_tables([[
        ["Customer", "Date", "Debit", "Credit"],
        ["Mohan", "2026-04-03", "500", ""],
        ["", "2026-04-04", "", "125"],
    ]])

    assert result is not None
    assert [(tx["amount"], tx["type"]) for tx in result["transactions"]] == [
        (500.0, "DEBIT"),
        (125.0, "CREDIT"),
    ]


def test_okcredit_backup_parser_reads_positioned_party_rows_and_signed_balances():
    def word(text, x0, x1, top):
        return {"text": text, "x0": x0, "x1": x1, "top": top}

    words = [
        word("CUSTOMER", 213, 280, 96), word("BACKUP", 283, 331, 96), word("REPORT", 334, 381, 96),
        word("NAME", 34, 59, 208), word("MOBILE", 194, 227, 208),
        word("ADVANCE", 348, 389, 208), word("DUE", 494, 511, 208),
        word("Mira🌚❤", 34, 96, 233), word("9199999999", 194, 245, 235),
        word("₹500", 358, 378, 233),
        word("NoPhone", 34, 80, 261), word("₹50,000", 486, 518, 261),
        word("SUPPLIER", 218, 276, 284), word("BACKUP", 279, 327, 284), word("REPORT", 329, 377, 284),
        word("NAME", 34, 59, 396), word("MOBILE", 194, 227, 396),
        word("DUE", 360, 377, 396), word("ADVANCE", 482, 522, 396),
        word("Store", 34, 70, 423), word("9435278463", 194, 245, 423),
        word("₹1,180", 355, 382, 423),
    ]

    result = server.parse_okcredit_backup_words([words])

    assert result is not None
    assert [party["name"] for party in result["parties"]] == [
        "Mira🌚❤",
        "NoPhone",
        "Store",
    ]
    assert [(party["type"], party["openingBalance"]) for party in result["parties"]] == [
        ("CUSTOMER", -500.0),
        ("CUSTOMER", 50000.0),
        ("SUPPLIER", -1180.0),
    ]
    assert [party["phone"] for party in result["parties"]] == [
        "9199999999",
        "",
        "9435278463",
    ]
    assert result["transactions"] == []
    assert any("does not contain transaction history" in warning for warning in result["warnings"])


def test_csv_reader_handles_bom_semicolon_and_indian_amount_grouping():
    tables = server.parse_csv_tables(
        "\ufeffParty;Date;Amount;Type\nAsha Stores;01/04/2026;1,25,000;Gave\n".encode()
    )

    result = server.parse_ledger_tables(tables)

    assert result is not None
    assert result["transactions"][0]["amount"] == 125000.0
    assert result["transactions"][0]["type"] == "DEBIT"


def test_amount_parser_handles_currency_labels_european_decimal_and_scales():
    assert server.parse_amount("Rs. 1,25,000.50") == 125000.5
    assert server.parse_amount("1.250,50") == 1250.5
    assert server.parse_amount("₹1.5 lakh") == 150000.0


def test_text_parser_uses_labeled_party_and_iso_dates():
    result = server.parse_ledger_text("Party: Asha Stores\n2026-04-01 ₹1,250.50 gave stock")

    assert result["parties"][0]["name"] == "Asha Stores"
    assert result["transactions"][0]["partyName"] == "Asha Stores"
    assert result["transactions"][0]["amount"] == 1250.5
    assert result["transactions"][0]["date"].startswith("2026-04-01")


def test_text_parser_warns_when_it_has_to_supply_a_missing_date():
    result = server.parse_ledger_text("Party: Asha Stores\n₹500 gave")

    assert len(result["transactions"]) == 1
    assert any("assigned today's date" in warning for warning in result["warnings"])


def test_text_parser_does_not_read_date_digits_as_opening_balance():
    result = server.parse_ledger_text(
        "Party: Asha Stores\nBalance as of 2026-04-01 ₹500"
    )

    assert result["parties"][0]["openingBalance"] == 500.0
    assert result["transactions"] == []


def test_text_parser_does_not_treat_credit_marker_as_crore_scale():
    result = server.parse_ledger_text("Party: Asha Stores\n2026-04-01 500 Cr")

    assert result["transactions"][0]["amount"] == 500.0
    assert result["transactions"][0]["type"] == "CREDIT"


def test_text_parser_skips_lines_with_both_transaction_directions():
    result = server.parse_ledger_text("Party: Asha Stores\n2026-04-01 ₹500 gave and received")

    assert result["transactions"] == []
    assert any("both money-in and money-out" in warning for warning in result["warnings"])


def test_import_endpoint_accepts_csv_and_returns_parsed_rows():
    client = TestClient(server.app)
    response = client.post(
        "/api/import/parse",
        files={"file": ("ledger.csv", "Party,Date,Amount,Type\nAsha,01/04/2026,500,Gave\n", "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parties"][0]["name"] == "Asha"
    assert body["transactions"][0]["amount"] == 500


def test_import_endpoint_accepts_xlsx_and_returns_parsed_rows():
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Party", "Date", "Amount", "Type"])
    sheet.append(["Asha", datetime(2026, 4, 1), 500, "Gave"])
    content = BytesIO()
    workbook.save(content)

    response = TestClient(server.app).post(
        "/api/import/parse",
        files={
            "file": (
                "ledger.xlsx",
                content.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["parties"][0]["name"] == "Asha"
    assert body["transactions"][0]["amount"] == 500
    assert body["transactions"][0]["date"].startswith("2026-04-01")


def test_import_endpoint_uses_okcredit_backup_parser_before_generic_text(monkeypatch):
    report = {
        "success": True,
        "parties": [{"name": "Mira", "phone": "", "type": "CUSTOMER", "openingBalance": 250}],
        "transactions": [],
        "warnings": ["Backup summary only."],
    }
    monkeypatch.setattr(server, "extract_okcredit_backup_pdf", lambda _: report)
    monkeypatch.setattr(server, "extract_text_from_pdf", lambda _: "generic text")
    monkeypatch.setattr(server, "extract_tables_from_pdf", lambda _: [])
    client = TestClient(server.app)

    response = client.post(
        "/api/import/parse",
        files={"file": ("backup.pdf", b"%PDF-placeholder", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == report


def test_import_endpoint_explains_scanned_pdf_limit(monkeypatch):
    monkeypatch.setattr(server, "extract_text_from_pdf", lambda _: "")
    monkeypatch.setattr(server, "extract_tables_from_pdf", lambda _: [])
    client = TestClient(server.app)

    response = client.post(
        "/api/import/parse",
        files={"file": ("scan.pdf", b"%PDF-placeholder", "application/pdf")},
    )

    assert response.status_code == 400
    assert "scanned/image-only" in response.json()["detail"]


def test_pdf_to_csv_endpoint_returns_csv_that_can_be_reparsed(monkeypatch):
    result = {
        "success": True,
        "parties": [{
            "name": "Asha Stores",
            "phone": "9876543210",
            "type": "CUSTOMER",
            "openingBalance": 2000.0,
        }],
        "transactions": [{
            "partyName": "Asha Stores",
            "date": "2026-04-01T00:00:00",
            "amount": 1250.5,
            "type": "DEBIT",
            "note": "Stock, shelves",
        }],
        "warnings": ["Review extracted rows."],
    }
    monkeypatch.setattr(server, "extract_okcredit_backup_pdf", lambda _: None)
    monkeypatch.setattr(server, "extract_text_from_pdf", lambda _: "ledger text")
    monkeypatch.setattr(server, "extract_tables_from_pdf", lambda _: [])
    monkeypatch.setattr(server, "parse_ledger_text", lambda _: result)

    response = TestClient(server.app).post(
        "/api/import/pdf-to-csv",
        files={"file": ("ledger.pdf", b"%PDF-placeholder", "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["warnings"] == result["warnings"]
    reparsed = server.parse_ledger_tables(server.parse_csv_tables(body["csv"].encode("utf-8")))
    assert reparsed is not None
    assert reparsed["parties"] == result["parties"]
    assert [(tx["amount"], tx["type"], tx["note"]) for tx in reparsed["transactions"]] == [
        (1250.5, "DEBIT", "Stock, shelves"),
    ]
    assert reparsed["transactions"][0]["date"].startswith("2026-04-01")


def test_import_endpoint_rejects_docx_files():
    response = TestClient(server.app).post(
        "/api/import/parse",
        files={"file": ("ledger.docx", b"not supported", "application/octet-stream")},
    )

    assert response.status_code == 415
