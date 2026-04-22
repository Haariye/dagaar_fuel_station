# -*- coding: utf-8 -*-
# Fuel Station Night Report v3 – Board of Directors
# Path: dagaar_fuel_station/dagaar_fuel_station/report/fuel_station_night_report/
#
# Uses frappe.utils.pdf.get_pdf (wkhtmltopdf) – NO reportlab needed.
#
# Sections (10):
#   1.  Cash Activity Summary
#   2.  Stock Balance by Warehouse (Ceelka Shidaalka)
#   3.  Nozzle Meter Readings
#   4.  Credit Sales (paid_amount = 0)
#   5.  Sales by Fuel Type / Item
#   6.  Shift Performance Breakdown
#   7.  Accounts Receivable Aging Snapshot
#   8.  Cash Over / Short Analysis
#   9.  Payment Entries Received
#   10. Cash-Type Accounts Trial Balance
# ─────────────────────────────────────────────────────────

import json

import frappe
from frappe import _
from frappe.utils import flt, nowdate, cstr, now_datetime


# ══════════════════════════════════════════════════════════
#  GRID VIEW  –  each section gets its own header row with
#  proper column labels, then data, then a blank gap row.
# ══════════════════════════════════════════════════════════

def execute(filters=None):
    filters = _normalise_filters(filters)
    ctx = _build_report_context(filters)

    columns = [
        {"label": "Col A", "fieldname": "col_a", "fieldtype": "Data", "width": 170},
        {"label": "Col B", "fieldname": "col_b", "fieldtype": "Data", "width": 160},
        {"label": "Col C", "fieldname": "col_c", "fieldtype": "Data", "width": 130},
        {"label": "Col D", "fieldname": "col_d", "fieldtype": "Data", "width": 120},
        {"label": "Col E", "fieldname": "col_e", "fieldtype": "Data", "width": 120},
        {"label": "Col F", "fieldname": "col_f", "fieldtype": "Data", "width": 120},
        {"label": "Col G", "fieldname": "col_g", "fieldtype": "Data", "width": 120},
        {"label": "Col H", "fieldname": "col_h", "fieldtype": "Data", "width": 120},
    ]

    data = []
    BLANK = {"col_a": "", "col_b": "", "col_c": "", "col_d": "",
             "col_e": "", "col_f": "", "col_g": "", "col_h": ""}

    def heading(title, col_labels):
        # section title row
        data.append(dict(BLANK, col_a=f"<b>{title}</b>"))
        # column header row
        row = dict(BLANK)
        keys = list(BLANK.keys())
        for i, lbl in enumerate(col_labels):
            if i < len(keys):
                row[keys[i]] = f"<b>{lbl}</b>"
        data.append(row)

    def add_row(vals):
        row = dict(BLANK)
        keys = list(BLANK.keys())
        for i, v in enumerate(vals):
            if i < len(keys):
                row[keys[i]] = v if v is not None else ""
        data.append(row)

    def gap():
        data.append(dict(BLANK))
        data.append(dict(BLANK))

    f2 = lambda v: f"{flt(v):,.2f}"
    f3 = lambda v: f"{flt(v):,.3f}"

    # ── 1. Cash Activity ──
    heading("1. Cash Activity Summary", ["Description", "Amount"])
    for r in ctx["cash_activity"]:
        add_row([r["label"], r["formatted"]])
    gap()

    # ── 2. Stock Balance ──
    heading("2. Stock Balance by Warehouse", ["Item", "Warehouse", "Qty", "UOM", "Val. Rate", "Stock Value"])
    for r in ctx["stock_balance"]:
        add_row([r["item_code"], r["warehouse"], f3(r["actual_qty"]),
                 r.get("stock_uom", ""), f2(r.get("valuation_rate", 0)), f2(r.get("stock_value", 0))])
    gap()

    # ── 3. Nozzle Readings (pivoted) ──
    heading("3. Nozzle Meter Readings",
            ["Pump", "Nozzle", "Item", "Morn Open", "Morn Close", "Eve Open", "Eve Close", "Tot Metered"])
    for r in ctx["nozzle_readings"]:
        add_row([r.get("fuel_pump", ""), r.get("fuel_nozzle", ""), r.get("item", ""),
                 f3(r.get("morning_open", 0)), f3(r.get("morning_close", 0)),
                 f3(r.get("evening_open", 0)), f3(r.get("evening_close", 0)),
                 f3(r.get("total_metered", 0))])
    gap()

    # ── 4. Credit Sales ──
    heading("4. Credit Sales (Unpaid)", ["Invoice", "Customer", "Pump", "Nozzle",
                                          "Grand Total", "Outstanding", "Status"])
    for r in ctx["credit_sales"]:
        add_row([r.get("invoice", ""), r.get("customer", ""), r.get("fuel_pump", ""),
                 r.get("fuel_nozzle", ""), f2(r.get("grand_total", 0)),
                 f2(r.get("outstanding_amount", 0)), r.get("status", "")])
    gap()

    # ── 5. Sales by Item ──
    heading("5. Sales by Fuel Type", ["Item", "Name", "UOM", "Qty", "Avg Rate", "Amount"])
    for r in ctx["sales_by_item"]:
        add_row([r.get("item_code", ""), r.get("item_name", ""), r.get("uom", ""),
                 f3(r.get("qty", 0)), f2(r.get("avg_rate", 0)), f2(r.get("amount", 0))])
    gap()

    # ── 6. Shift Performance ──
    heading("6. Shift Performance",
            ["Shift", "Attendant", "Billable", "Credit Amt", "Cash Amt", "Total", "Received", "Over/Short"])
    for r in ctx["shift_performance"]:
        add_row([r.get("shift", ""), r.get("attendant", ""), f3(r.get("billable_qty", 0)),
                 f2(r.get("credit_amount", 0)), f2(r.get("cash_amount", 0)),
                 f2(r.get("total_amount", 0)), f2(r.get("actual_cash_received", 0)),
                 f2(r.get("cash_over_short", 0))])
    gap()

    # ── 7. AR Aging ──
    heading("7. Accounts Receivable Aging",
            ["Customer", "Current", "1-30", "31-60", "61-90", ">90", "Total"])
    for r in ctx["ar_aging"]:
        add_row([r.get("customer", ""), f2(r.get("current_amt", 0)),
                 f2(r.get("days_1_30", 0)), f2(r.get("days_31_60", 0)),
                 f2(r.get("days_61_90", 0)), f2(r.get("over_90", 0)),
                 f2(r.get("total_outstanding", 0))])
    gap()

    # ── 8. Cash Over/Short ──
    heading("8. Cash Over/Short Analysis",
            ["Shift", "Attendant", "Name", "Expected", "Received", "Over/Short", "Discount"])
    for r in ctx["cash_analysis"]:
        add_row([r.get("shift", ""), r.get("attendant", ""), r.get("attendant_name", ""),
                 f2(r.get("expected_cash", 0)), f2(r.get("actual_cash_received", 0)),
                 f2(r.get("cash_over_short", 0)), f2(r.get("additional_discount_amount", 0))])
    gap()

    # ── 9. Payment Entries ──
    heading("9. Payment Entries Received",
            ["Entry", "Party", "Mode", "Paid Amount", "Date", "Reference"])
    for r in ctx["payment_entries"]:
        add_row([r.get("name", ""), r.get("party", ""), r.get("mode_of_payment", ""),
                 f2(r.get("paid_amount", 0)), cstr(r.get("posting_date", "")),
                 cstr(r.get("reference_no", ""))])
    gap()

    # ── 10. Trial Balance ──
    heading("10. Cash Accounts Trial Balance",
            ["Account", "Opening Dr", "Opening Cr", "Debit", "Credit", "Closing Dr", "Closing Cr"])
    for r in ctx["trial_balance"]:
        add_row([r.get("account", ""), f2(r.get("opening_debit", 0)), f2(r.get("opening_credit", 0)),
                 f2(r.get("debit", 0)), f2(r.get("credit", 0)),
                 f2(r.get("closing_debit", 0)), f2(r.get("closing_credit", 0))])

    return columns, data


# ══════════════════════════════════════════════════════════
#  PDF — HTML rendered via frappe.utils.pdf.get_pdf
#  (uses wkhtmltopdf, always installed with ERPNext)
# ══════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_pdf(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    filters = _normalise_filters(filters)
    ctx = _build_report_context(filters)
    html = _render_html(ctx, filters)

    from frappe.utils.pdf import get_pdf
    pdf_bytes = get_pdf(html, {
        "page-size": "A4",
        "orientation": "Portrait",
        "margin-top": "12mm",
        "margin-bottom": "14mm",
        "margin-left": "10mm",
        "margin-right": "10mm",
        "header-spacing": "3",
        "footer-font-size": "7",
        "footer-center": "Page [page] of [topage]",
        "footer-line": "",
        "no-outline": "",
    })

    token = frappe.generate_hash(length=20)
    frappe.cache.set_value(f"night_report_pdf_{token}", pdf_bytes, expires_in_sec=300)
    return token


@frappe.whitelist()
def download_pdf(token=None):
    if not token:
        frappe.throw(_("Missing token"))
    pdf_bytes = frappe.cache.get_value(f"night_report_pdf_{token}")
    if not pdf_bytes:
        frappe.throw(_("Report expired. Please regenerate."))
    frappe.local.response.filename = "Fuel_Station_Night_Report.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"


# ══════════════════════════════════════════════════════════
#  FILTER HELPERS
# ══════════════════════════════════════════════════════════

def _normalise_filters(filters):
    filters = filters or {}
    if not filters.get("from_date"):
        filters["from_date"] = nowdate()
    if not filters.get("to_date"):
        filters["to_date"] = filters["from_date"]
    if not filters.get("from_time"):
        filters["from_time"] = "00:00:00"
    if not filters.get("to_time"):
        filters["to_time"] = "23:59:59"
    if not filters.get("owner"):
        filters["owner"] = "All"
    return filters


def _dt_between(alias, date_f="posting_date", time_f=None):
    if time_f:
        return (
            f"CONCAT({alias}.{date_f}, ' ', IFNULL({alias}.{time_f}, '00:00:00')) "
            f"BETWEEN CONCAT(%(from_date)s, ' ', %(from_time)s) "
            f"AND CONCAT(%(to_date)s, ' ', %(to_time)s)"
        )
    return f"{alias}.{date_f} BETWEEN %(from_date)s AND %(to_date)s"


def _owner_cond(alias):
    return f"AND (%(owner)s = 'All' OR {alias}.owner = %(owner)s)"


# ══════════════════════════════════════════════════════════
#  DATA COLLECTION
# ══════════════════════════════════════════════════════════

def _build_report_context(filters):
    p = dict(filters)
    company = filters.get("company")
    pos_profile = filters.get("pos_profile")

    co_si = "AND si.company = %(company)s" if company else ""
    co_pe = "AND pe.company = %(company)s" if company else ""
    co_je = "AND je.company = %(company)s" if company else ""
    pos   = "AND si.pos_profile_link = %(pos_profile)s" if pos_profile else ""
    ow_si = _owner_cond("si")
    ow_pe = _owner_cond("pe")
    ow_je = _owner_cond("je")
    dt_si = _dt_between("si", "posting_date", "posting_time")
    dt_pe = _dt_between("pe", "posting_date", "posting_time")
    dt_je = _dt_between("je", "posting_date", "posting_time")

    currency = _get_currency(company)

    # ── 1. CASH ACTIVITY ─────────────────────
    total_sales = flt(_scalar(f"""
        SELECT IFNULL(SUM(si.base_grand_total),0) FROM `tabSales Invoice` si
        WHERE si.docstatus=1 AND si.status NOT IN ('Draft','Cancelled')
        AND si.is_return=0 AND {dt_si} {co_si} {pos} {ow_si}""", p))

    total_payments = flt(_scalar(f"""
        SELECT IFNULL(SUM(pe.base_paid_amount),0) FROM `tabPayment Entry` pe
        WHERE pe.docstatus=1 AND pe.payment_type='Receive'
        AND {dt_pe} {co_pe} {ow_pe}""", p))

    credit_sales_total = flt(_scalar(f"""
        SELECT IFNULL(SUM(si.base_grand_total),0) FROM `tabSales Invoice` si
        WHERE si.docstatus=1 AND si.status NOT IN ('Draft','Cancelled')
        AND si.is_return=0 AND IFNULL(si.outstanding_amount,0)>=IFNULL(si.grand_total,0)
        AND {dt_si} {co_si} {pos} {ow_si}""", p))

    partially_unpaid = flt(_scalar(f"""
        SELECT IFNULL(SUM(si.outstanding_amount),0) FROM `tabSales Invoice` si
        WHERE si.docstatus=1 AND si.status NOT IN ('Draft','Cancelled')
        AND si.is_return=0 AND IFNULL(si.outstanding_amount,0)>0
        AND IFNULL(si.outstanding_amount,0)<IFNULL(si.grand_total,0)
        AND {dt_si} {co_si} {pos} {ow_si}""", p))

    journal_debits = flt(_scalar(f"""
        SELECT IFNULL(SUM(jea.debit),0) FROM `tabJournal Entry` je
        INNER JOIN `tabJournal Entry Account` jea ON jea.parent=je.name
        WHERE je.docstatus=1 AND {dt_je} {co_je} {ow_je}""", p))

    total_litres = flt(_scalar(f"""
        SELECT IFNULL(SUM(sii.qty),0) FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name=sii.parent
        WHERE si.docstatus=1 AND si.status NOT IN ('Draft','Cancelled')
        AND si.is_return=0 AND {dt_si} {co_si} {pos} {ow_si}""", p))

    cash_over_short = flt(_scalar("""
        SELECT IFNULL(SUM(pre.cash_over_short),0) FROM `tabPump Reading Entry` pre
        WHERE pre.docstatus=1 AND pre.date BETWEEN %(from_date)s AND %(to_date)s""", p))

    total_activity = total_sales + total_payments - journal_debits
    available_for_deposit = total_sales - credit_sales_total - partially_unpaid + total_payments - journal_debits

    def _f(v):
        return _fmt(v, currency)

    cash_activity = [
        {"label": "Total Sales (Invoiced)",                 "formatted": _f(total_sales),            "amount": total_sales},
        {"label": "Total Payments Received",                "formatted": _f(total_payments),          "amount": total_payments},
        {"label": "Total Activity (Sales+Payments−JE)",     "formatted": _f(total_activity),          "amount": total_activity},
        {"label": "Credit Sales (Fully Unpaid)",            "formatted": _f(credit_sales_total),      "amount": credit_sales_total},
        {"label": "Partially Unpaid Amount",                "formatted": _f(partially_unpaid),        "amount": partially_unpaid},
        {"label": "Journal Entry Debits",                   "formatted": _f(-journal_debits),         "amount": -journal_debits},
        {"label": "Available for Deposit",                  "formatted": _f(available_for_deposit),   "amount": available_for_deposit, "highlight": True},
        {"label": "Total Litres Sold",                      "formatted": f"{total_litres:,.3f} L",    "amount": total_litres},
        {"label": "Cash Over/Short",                        "formatted": _f(cash_over_short),         "amount": cash_over_short},
    ]

    # ── 2. STOCK BALANCE ─────────────────────
    # Only show warehouses that are actually assigned to fuel nozzles
    stock_balance = frappe.db.sql("""
        SELECT bin.item_code, bin.warehouse, bin.actual_qty,
               bin.stock_uom, bin.valuation_rate, bin.stock_value
        FROM `tabBin` bin
        WHERE bin.actual_qty != 0
          AND bin.warehouse IN (
              SELECT DISTINCT fn.warehouse FROM `tabFuel Nozzle` fn
              WHERE IFNULL(fn.warehouse, '') != ''
          )
        ORDER BY bin.warehouse, bin.item_code
    """, as_dict=True)

    # ── 3. NOZZLE READINGS (pivoted: one row per nozzle, shifts horizontal) ──
    _raw_nozzle = frappe.db.sql("""
        SELECT scl.fuel_nozzle, scl.fuel_pump, scl.item,
               scl.opening_reading AS opening, scl.closing_reading AS closing,
               scl.metered_qty, sce.shift
        FROM `tabShift Closing Line` scl
        INNER JOIN `tabShift Closing Entry` sce ON sce.name=scl.parent
        WHERE sce.docstatus=1 AND sce.date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY scl.fuel_pump, scl.fuel_nozzle, FIELD(sce.shift, 'Morning', 'Evening', 'Night')
    """, p, as_dict=True)

    # Pivot: group by nozzle, spread shifts horizontally
    from collections import OrderedDict
    _nozzle_map = OrderedDict()
    for r in _raw_nozzle:
        key = r.get("fuel_nozzle", "")
        if key not in _nozzle_map:
            _nozzle_map[key] = {
                "fuel_nozzle": key,
                "fuel_pump": r.get("fuel_pump", ""),
                "item": r.get("item", ""),
                "morning_open": 0, "morning_close": 0, "morning_metered": 0,
                "evening_open": 0, "evening_close": 0, "evening_metered": 0,
                "night_open": 0, "night_close": 0, "night_metered": 0,
                "total_metered": 0,
            }
        shift = cstr(r.get("shift", "")).strip()
        metered = flt(r.get("metered_qty", 0))
        opening = flt(r.get("opening", 0))
        closing = flt(r.get("closing", 0))

        if shift == "Morning":
            _nozzle_map[key]["morning_open"] = opening
            _nozzle_map[key]["morning_close"] = closing
            _nozzle_map[key]["morning_metered"] = metered
        elif shift == "Evening":
            _nozzle_map[key]["evening_open"] = opening
            _nozzle_map[key]["evening_close"] = closing
            _nozzle_map[key]["evening_metered"] = metered
        elif shift == "Night":
            _nozzle_map[key]["night_open"] = opening
            _nozzle_map[key]["night_close"] = closing
            _nozzle_map[key]["night_metered"] = metered
        _nozzle_map[key]["total_metered"] += metered

    nozzle_readings = list(_nozzle_map.values())

    # ── 4. CREDIT SALES ──────────────────────
    credit_sales = frappe.db.sql(f"""
        SELECT si.name AS invoice, si.customer, si.posting_date,
               si.grand_total, si.outstanding_amount, si.currency,
               si.status, si.fuel_pump, si.fuel_nozzle, si.remarks
        FROM `tabSales Invoice` si
        WHERE si.docstatus=1 AND si.status NOT IN ('Draft','Cancelled')
          AND si.is_return=0 AND IFNULL(si.paid_amount,0)=0
          AND {dt_si} {co_si} {pos} {ow_si}
        ORDER BY si.customer, si.name
    """, p, as_dict=True)

    # ── 5. SALES BY ITEM ─────────────────────
    sales_by_item = frappe.db.sql(f"""
        SELECT sii.item_code, sii.item_name, sii.stock_uom AS uom,
               SUM(sii.qty) AS qty, AVG(sii.rate) AS avg_rate, SUM(sii.amount) AS amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si ON si.name=sii.parent
        WHERE si.docstatus=1 AND si.status NOT IN ('Draft','Cancelled')
          AND si.is_return=0 AND {dt_si} {co_si} {pos} {ow_si}
        GROUP BY sii.item_code, sii.item_name, sii.stock_uom
        ORDER BY SUM(sii.amount) DESC
    """, p, as_dict=True)

    # ── 6. SHIFT PERFORMANCE ─────────────────
    shift_performance = frappe.db.sql("""
        SELECT pre.shift, pre.attendant, pre.pos_profile,
               pre.total_metered_qty AS metered_qty, pre.total_billable_qty AS billable_qty,
               pre.total_credit_qty AS credit_qty, pre.total_cash_qty AS cash_qty,
               pre.total_credit_amount AS credit_amount, pre.total_cash_amount AS cash_amount,
               pre.total_amount, pre.actual_cash_received, pre.cash_over_short
        FROM `tabPump Reading Entry` pre
        WHERE pre.docstatus=1 AND pre.date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY pre.shift
    """, p, as_dict=True)

    # ── 7. AR AGING ──────────────────────────
    ar_aging = frappe.db.sql(f"""
        SELECT si.customer,
            SUM(CASE WHEN DATEDIFF(%(to_date)s,si.due_date)<=0 THEN si.outstanding_amount ELSE 0 END) AS current_amt,
            SUM(CASE WHEN DATEDIFF(%(to_date)s,si.due_date) BETWEEN 1 AND 30 THEN si.outstanding_amount ELSE 0 END) AS days_1_30,
            SUM(CASE WHEN DATEDIFF(%(to_date)s,si.due_date) BETWEEN 31 AND 60 THEN si.outstanding_amount ELSE 0 END) AS days_31_60,
            SUM(CASE WHEN DATEDIFF(%(to_date)s,si.due_date) BETWEEN 61 AND 90 THEN si.outstanding_amount ELSE 0 END) AS days_61_90,
            SUM(CASE WHEN DATEDIFF(%(to_date)s,si.due_date)>90 THEN si.outstanding_amount ELSE 0 END) AS over_90,
            SUM(si.outstanding_amount) AS total_outstanding
        FROM `tabSales Invoice` si
        WHERE si.docstatus=1 AND si.outstanding_amount>0 AND si.is_return=0 {co_si}
        GROUP BY si.customer ORDER BY SUM(si.outstanding_amount) DESC LIMIT 30
    """, p, as_dict=True)

    # ── 8. CASH OVER/SHORT ───────────────────
    cash_analysis = frappe.db.sql("""
        SELECT pre.shift, pre.attendant, emp.employee_name AS attendant_name,
               pre.total_cash_amount AS expected_cash,
               pre.actual_cash_received, pre.cash_over_short,
               pre.additional_discount_amount
        FROM `tabPump Reading Entry` pre
        LEFT JOIN `tabEmployee` emp ON emp.name=pre.attendant
        WHERE pre.docstatus=1 AND pre.date BETWEEN %(from_date)s AND %(to_date)s
        ORDER BY pre.shift
    """, p, as_dict=True)

    # ── 9. PAYMENT ENTRIES ───────────────────
    payment_entries = frappe.db.sql(f"""
        SELECT pe.name, pe.party, pe.party_name, pe.mode_of_payment,
               pe.paid_amount, pe.base_paid_amount, pe.posting_date,
               pe.reference_no, pe.reference_date
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus=1 AND pe.payment_type='Receive'
          AND {dt_pe} {co_pe} {ow_pe}
        ORDER BY pe.posting_date, pe.name
    """, p, as_dict=True)

    # ── 10. CASH-TYPE ACCOUNTS TRIAL BALANCE ─
    trial_balance = _get_cash_trial_balance(p, company)

    return {
        "currency": currency,
        "filters": filters,
        "cash_activity": cash_activity,
        "stock_balance": stock_balance,
        "nozzle_readings": nozzle_readings,
        "credit_sales": credit_sales,
        "sales_by_item": sales_by_item,
        "shift_performance": shift_performance,
        "ar_aging": ar_aging,
        "cash_analysis": cash_analysis,
        "payment_entries": payment_entries,
        "trial_balance": trial_balance,
    }


def _get_cash_trial_balance(params, company):
    """Trial balance for accounts with account_type = 'Cash' or root_type in Cash-like."""
    co = "AND gl.company = %(company)s" if company else ""
    # Opening balance: everything before from_date
    # Period: between from_date and to_date
    rows = frappe.db.sql(f"""
        SELECT
            gl.account,
            SUM(CASE WHEN gl.posting_date < %(from_date)s THEN gl.debit ELSE 0 END) AS opening_debit,
            SUM(CASE WHEN gl.posting_date < %(from_date)s THEN gl.credit ELSE 0 END) AS opening_credit,
            SUM(CASE WHEN gl.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN gl.debit ELSE 0 END) AS debit,
            SUM(CASE WHEN gl.posting_date BETWEEN %(from_date)s AND %(to_date)s THEN gl.credit ELSE 0 END) AS credit
        FROM `tabGL Entry` gl
        INNER JOIN `tabAccount` acc ON acc.name = gl.account
        WHERE gl.is_cancelled = 0
          AND acc.account_type = 'Cash'
          {co}
        GROUP BY gl.account
        ORDER BY gl.account
    """, params, as_dict=True)

    for r in rows:
        r["closing_debit"] = flt(r["opening_debit"]) + flt(r["debit"])
        r["closing_credit"] = flt(r["opening_credit"]) + flt(r["credit"])

    return rows


# ══════════════════════════════════════════════════════════
#  HTML TEMPLATE for PDF
# ══════════════════════════════════════════════════════════

def _render_html(ctx, filters):
    """Build the full HTML page for wkhtmltopdf."""
    currency = ctx["currency"]
    company = filters.get("company") or \
        frappe.db.get_single_value("Global Defaults", "default_company") or "Fuel Station"
    station = filters.get("pos_profile") or "All Stations"
    from_d = filters.get("from_date", "")
    to_d = filters.get("to_date", "")
    from_t = filters.get("from_time", "00:00:00")
    to_t = filters.get("to_time", "23:59:59")
    owner = filters.get("owner", "All")
    generated = now_datetime().strftime("%d/%m/%Y %H:%M")

    f2 = lambda v: f"{flt(v):,.2f}"
    f3 = lambda v: f"{flt(v):,.3f}"

    css = """
    <style>
        @page { size: A4 portrait; margin: 12mm 10mm 14mm 10mm; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Helvetica, Arial, sans-serif; font-size: 8.5pt; color: #222; line-height: 1.3; }
        .header { text-align: center; margin-bottom: 10px; }
        .header h1 { font-size: 15pt; color: #0d47a1; margin: 0 0 2px; }
        .header h2 { font-size: 9pt; color: #555; font-weight: normal; margin: 0 0 3px; }
        .header .meta { font-size: 7.5pt; color: #777; margin-bottom: 6px; }
        .header-line { border: none; border-top: 2px solid #0d47a1; margin: 0 0 12px; }
        .section { margin-bottom: 14px; page-break-inside: avoid; }
        .section-title { font-size: 10pt; font-weight: bold; color: #0d47a1;
                         border-bottom: 1.5px solid #0d47a1; padding-bottom: 3px; margin-bottom: 6px; }
        .section-footer { font-size: 6.5pt; color: #999; text-align: right; margin-top: 3px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 2px; }
        th { background: #0d47a1; color: #fff; font-size: 7.5pt; font-weight: bold;
             padding: 4px 5px; text-align: left; white-space: nowrap; }
        th.r { text-align: right; }
        td { padding: 3px 5px; font-size: 7.5pt; border-bottom: 0.5px solid #e0e0e0; vertical-align: middle; }
        td.r { text-align: right; font-variant-numeric: tabular-nums; }
        td.b { font-weight: bold; }
        td.rb { text-align: right; font-weight: bold; }
        td.neg { text-align: right; color: #c62828; }
        td.pos { text-align: right; color: #2e7d32; }
        tr.alt { background: #f7f8fa; }
        tr.total { background: #e3f2fd; font-weight: bold; }
        tr.total td { border-top: 1.5px solid #0d47a1; padding-top: 4px; }
        .report-end { text-align: center; margin-top: 18px; padding-top: 8px;
                       border-top: 2px solid #0d47a1; }
        .report-end p { font-size: 7pt; color: #aaa; }
        .report-end .end-title { font-size: 9pt; color: #555; font-weight: bold; margin-bottom: 3px; }
        .page-break { page-break-before: always; }
    </style>
    """

    parts = [css]

    # ── HEADER ──
    parts.append(f"""
    <div class="header">
        <h1>{company}</h1>
        <h2>DAILY NIGHT REPORT &ndash; BOARD OF DIRECTORS</h2>
        <div class="meta">
            Period: {from_d} {from_t} &rarr; {to_d} {to_t} &nbsp;|&nbsp;
            Station: {station} &nbsp;|&nbsp;
            User: {owner} &nbsp;|&nbsp;
            Generated: {generated}
        </div>
    </div>
    <hr class="header-line">
    """)

    # ── HELPER: build table html ──
    def tbl(headers, rows, aligns=None, total_row=None, footer=None):
        """headers: list of (label, align).  rows: list of list.  aligns: list of 'l'|'r'."""
        if not aligns:
            aligns = ["l"] * len(headers)
        h = "<table><thead><tr>"
        for lbl, al in zip(headers, aligns):
            cls = ' class="r"' if al == "r" else ""
            h += f"<th{cls}>{lbl}</th>"
        h += "</tr></thead><tbody>"
        for i, row in enumerate(rows):
            cls = ' class="alt"' if i % 2 == 1 else ""
            h += f"<tr{cls}>"
            for j, cell in enumerate(row):
                al = aligns[j] if j < len(aligns) else "l"
                td_cls = ' class="r"' if al == "r" else ""
                h += f"<td{td_cls}>{cell}</td>"
            h += "</tr>"
        if total_row:
            h += '<tr class="total">'
            for j, cell in enumerate(total_row):
                al = aligns[j] if j < len(aligns) else "l"
                td_cls = ' class="rb"' if al == "r" else ' class="b"'
                h += f"<td{td_cls}>{cell}</td>"
            h += "</tr>"
        h += "</tbody></table>"
        if footer:
            h += f'<div class="section-footer">{footer}</div>'
        return h

    def neg_or_pos(v):
        v = flt(v)
        if v < 0: return f'<span style="color:#c62828">{f2(v)}</span>'
        if v > 0: return f'<span style="color:#2e7d32">{f2(v)}</span>'
        return f2(v)

    # ═══════════════════════════════════════════
    #  1. CASH ACTIVITY
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">1. Cash Activity Summary</div>')
    ca_rows = []
    for r in ctx["cash_activity"]:
        val = r["amount"]
        styled = f'<b>{r["formatted"]}</b>' if r.get("highlight") else r["formatted"]
        if val < 0:
            styled = f'<span style="color:#c62828">{r["formatted"]}</span>'
        ca_rows.append([r["label"], styled])
    parts.append(tbl(
        ["Description", "Amount"], ca_rows, ["l", "r"],
        footer="Source: Sales Invoices, Payment Entries (Receive), Journal Entry Debits"
    ))
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  2. STOCK BALANCE
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">2. Stock Balance by Warehouse (Ceelka Shidaalka)</div>')
    sb = ctx["stock_balance"]
    if sb:
        sb_rows = []
        t_q = t_v = 0
        for r in sb:
            q = flt(r["actual_qty"]); v = flt(r.get("stock_value", 0))
            t_q += q; t_v += v
            sb_rows.append([r["item_code"], r["warehouse"], f3(q),
                            r.get("stock_uom", ""), f2(r.get("valuation_rate", 0)), f2(v)])
        parts.append(tbl(
            ["Item", "Warehouse", "Qty", "UOM", "Val. Rate", "Stock Value"],
            sb_rows, ["l", "l", "r", "l", "r", "r"],
            total_row=["TOTAL", "", f3(t_q), "", "", f2(t_v)],
            footer="Source: Bin (Stock Ledger) – Fuel station and nozzle warehouses"
        ))
    else:
        parts.append("<p><i>No stock found in fuel warehouses.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  3. NOZZLE READINGS (pivoted – one row per nozzle)
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">3. Nozzle Meter Readings</div>')
    nr = ctx["nozzle_readings"]
    if nr:
        # Build a custom table with two-level header (shift groups)
        nr_html = """<table>
        <thead>
            <tr>
                <th rowspan="2">Pump</th>
                <th rowspan="2">Nozzle</th>
                <th rowspan="2">Item</th>
                <th colspan="3" style="text-align:center;border-left:1.5px solid #fff">Morning</th>
                <th colspan="3" style="text-align:center;border-left:1.5px solid #fff">Evening</th>
                <th colspan="3" style="text-align:center;border-left:1.5px solid #fff">Night</th>
                <th rowspan="2" class="r" style="border-left:1.5px solid #fff">Total Metered</th>
            </tr>
            <tr>
                <th class="r" style="border-left:1.5px solid #fff">Open</th>
                <th class="r">Close</th>
                <th class="r">Metered</th>
                <th class="r" style="border-left:1.5px solid #fff">Open</th>
                <th class="r">Close</th>
                <th class="r">Metered</th>
                <th class="r" style="border-left:1.5px solid #fff">Open</th>
                <th class="r">Close</th>
                <th class="r">Metered</th>
            </tr>
        </thead><tbody>"""
        total_metered = 0
        for i, r in enumerate(nr):
            cls = ' class="alt"' if i % 2 == 1 else ""
            tm = flt(r.get("total_metered", 0))
            total_metered += tm
            bdr = 'style="border-left:1.5px solid #e0e0e0"'
            nr_html += f"""<tr{cls}>
                <td>{r.get("fuel_pump","")}</td>
                <td>{r.get("fuel_nozzle","")}</td>
                <td>{r.get("item","")}</td>
                <td class="r" {bdr}>{f3(r.get("morning_open",0))}</td>
                <td class="r">{f3(r.get("morning_close",0))}</td>
                <td class="r">{f3(r.get("morning_metered",0))}</td>
                <td class="r" {bdr}>{f3(r.get("evening_open",0))}</td>
                <td class="r">{f3(r.get("evening_close",0))}</td>
                <td class="r">{f3(r.get("evening_metered",0))}</td>
                <td class="r" {bdr}>{f3(r.get("night_open",0))}</td>
                <td class="r">{f3(r.get("night_close",0))}</td>
                <td class="r">{f3(r.get("night_metered",0))}</td>
                <td class="rb" {bdr}>{f3(tm)}</td>
            </tr>"""
        nr_html += f"""<tr class="total">
            <td class="b">TOTAL</td><td></td><td></td>
            <td></td><td></td><td></td>
            <td></td><td></td><td></td>
            <td></td><td></td><td></td>
            <td class="rb">{f3(total_metered)}</td>
        </tr>"""
        nr_html += "</tbody></table>"
        nr_html += '<div class="section-footer">Source: Shift Closing Entry &rarr; Shift Closing Line (pivoted by nozzle)</div>'
        parts.append(nr_html)
    else:
        parts.append("<p><i>No shift closing entries found.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  4. CREDIT SALES
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">4. Credit Sales (Unpaid Invoices &ndash; paid_amount = 0)</div>')
    cs = ctx["credit_sales"]
    if cs:
        cs_rows = []
        t_gt = t_os = 0
        for r in cs:
            gt = flt(r.get("grand_total", 0)); oa = flt(r.get("outstanding_amount", 0))
            t_gt += gt; t_os += oa
            rmk = cstr(r.get("remarks", ""))[:55]
            cs_rows.append([
                r.get("invoice", ""), r.get("customer", ""), r.get("fuel_pump", ""),
                r.get("fuel_nozzle", ""), f2(gt), f2(oa), r.get("status", ""), rmk,
            ])
        parts.append(tbl(
            ["Invoice", "Customer", "Pump", "Nozzle", "Grand Total", "Outstanding", "Status", "Remarks"],
            cs_rows, ["l", "l", "l", "l", "r", "r", "l", "l"],
            total_row=["TOTAL", f"{len(cs)} invoices", "", "", f2(t_gt), f2(t_os), "", ""],
            footer="Filter: Sales Invoices where paid_amount = 0"
        ))
    else:
        parts.append("<p><i>No credit sales found.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  5. SALES BY FUEL TYPE
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">5. Sales by Fuel Type / Item</div>')
    si = ctx["sales_by_item"]
    if si:
        si_rows = []
        t_q = t_a = 0
        for r in si:
            q = flt(r.get("qty", 0)); a = flt(r.get("amount", 0))
            t_q += q; t_a += a
            si_rows.append([r.get("item_code", ""), r.get("item_name", ""),
                            r.get("uom", ""), f3(q), f2(r.get("avg_rate", 0)), f2(a)])
        parts.append(tbl(
            ["Item Code", "Item Name", "UOM", "Qty Sold", "Avg Rate", "Total Amount"],
            si_rows, ["l", "l", "l", "r", "r", "r"],
            total_row=["TOTAL", "", "", f3(t_q), "", f2(t_a)],
            footer="Source: Sales Invoice Item grouped by item_code"
        ))
    else:
        parts.append("<p><i>No sales found.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  6. SHIFT PERFORMANCE
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">6. Shift Performance Breakdown</div>')
    sp = ctx["shift_performance"]
    if sp:
        sp_rows = []
        for r in sp:
            os_v = neg_or_pos(r.get("cash_over_short", 0))
            sp_rows.append([
                r.get("shift", ""), r.get("attendant", ""), r.get("pos_profile", ""),
                f3(r.get("metered_qty", 0)), f3(r.get("billable_qty", 0)),
                f3(r.get("credit_qty", 0)), f3(r.get("cash_qty", 0)),
                f2(r.get("credit_amount", 0)), f2(r.get("cash_amount", 0)),
                f2(r.get("total_amount", 0)), f2(r.get("actual_cash_received", 0)), os_v,
            ])
        parts.append(tbl(
            ["Shift", "Attendant", "Station", "Metered", "Billable", "Credit Qty",
             "Cash Qty", "Credit Amt", "Cash Amt", "Total", "Received", "Over/Short"],
            sp_rows, ["l", "l", "l", "r", "r", "r", "r", "r", "r", "r", "r", "r"],
            footer="Source: Pump Reading Entry (submitted)"
        ))
    else:
        parts.append("<p><i>No pump reading entries found.</i></p>")
    parts.append('</div>')

    # page break before aging + remaining
    parts.append('<div class="page-break"></div>')

    # ═══════════════════════════════════════════
    #  7. AR AGING
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">7. Accounts Receivable Aging Snapshot</div>')
    ar = ctx["ar_aging"]
    if ar:
        ar_rows = []
        g = {"c": 0, "d30": 0, "d60": 0, "d90": 0, "o90": 0, "t": 0}
        for r in ar:
            c = flt(r.get("current_amt",0)); d30 = flt(r.get("days_1_30",0))
            d60 = flt(r.get("days_31_60",0)); d90 = flt(r.get("days_61_90",0))
            o90 = flt(r.get("over_90",0)); t = flt(r.get("total_outstanding",0))
            g["c"]+=c; g["d30"]+=d30; g["d60"]+=d60; g["d90"]+=d90; g["o90"]+=o90; g["t"]+=t
            ar_rows.append([r.get("customer",""), f2(c), f2(d30), f2(d60), f2(d90), f2(o90), f2(t)])
        parts.append(tbl(
            ["Customer", "Current", "1-30 Days", "31-60 Days", "61-90 Days", ">90 Days", "Total"],
            ar_rows, ["l", "r", "r", "r", "r", "r", "r"],
            total_row=["GRAND TOTAL", f2(g["c"]), f2(g["d30"]), f2(g["d60"]),
                        f2(g["d90"]), f2(g["o90"]), f2(g["t"])],
            footer="Top 30 customers by outstanding &ndash; all dates up to report end date"
        ))
    else:
        parts.append("<p><i>No outstanding receivables.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  8. CASH OVER/SHORT
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">8. Cash Over / Short Analysis</div>')
    co = ctx["cash_analysis"]
    if co:
        co_rows = []
        for r in co:
            os_v = neg_or_pos(r.get("cash_over_short", 0))
            co_rows.append([
                r.get("shift", ""), r.get("attendant", ""), r.get("attendant_name", ""),
                f2(r.get("expected_cash", 0)), f2(r.get("actual_cash_received", 0)),
                os_v, f2(r.get("additional_discount_amount", 0)),
            ])
        parts.append(tbl(
            ["Shift", "Attendant ID", "Attendant Name", "Expected Cash",
             "Cash Received", "Over/Short", "Discount Given"],
            co_rows, ["l", "l", "l", "r", "r", "r", "r"],
            footer="Source: Pump Reading Entry &ndash; actual_cash_received vs total_cash_amount"
        ))
    else:
        parts.append("<p><i>No cash analysis data.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  9. PAYMENT ENTRIES
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">9. Payment Entries Received</div>')
    pe = ctx["payment_entries"]
    if pe:
        pe_rows = []
        t_paid = 0
        for r in pe:
            pa = flt(r.get("paid_amount", 0)); t_paid += pa
            pe_rows.append([
                r.get("name", ""), r.get("party", ""), r.get("party_name", ""),
                r.get("mode_of_payment", ""), f2(pa),
                cstr(r.get("posting_date", "")), cstr(r.get("reference_no", "")),
            ])
        parts.append(tbl(
            ["Payment Entry", "Party", "Party Name", "Mode", "Paid Amount", "Date", "Reference"],
            pe_rows, ["l", "l", "l", "l", "r", "l", "l"],
            total_row=["TOTAL", f"{len(pe)} entries", "", "", f2(t_paid), "", ""],
            footer="Source: Payment Entry (Receive, docstatus=1)"
        ))
    else:
        parts.append("<p><i>No payment entries received.</i></p>")
    parts.append('</div>')

    # ═══════════════════════════════════════════
    #  10. CASH ACCOUNTS TRIAL BALANCE
    # ═══════════════════════════════════════════
    parts.append('<div class="section">')
    parts.append('<div class="section-title">10. Cash-Type Accounts Trial Balance</div>')
    tb = ctx["trial_balance"]
    if tb:
        tb_rows = []
        totals = {"od": 0, "oc": 0, "d": 0, "c": 0, "cd": 0, "cc": 0}
        for r in tb:
            od = flt(r.get("opening_debit",0)); oc = flt(r.get("opening_credit",0))
            d = flt(r.get("debit",0)); c = flt(r.get("credit",0))
            cd = flt(r.get("closing_debit",0)); cc = flt(r.get("closing_credit",0))
            totals["od"]+=od; totals["oc"]+=oc; totals["d"]+=d
            totals["c"]+=c; totals["cd"]+=cd; totals["cc"]+=cc
            tb_rows.append([r.get("account",""), f2(od), f2(oc), f2(d), f2(c), f2(cd), f2(cc)])
        parts.append(tbl(
            ["Account", "Opening Dr", "Opening Cr", "Debit", "Credit", "Closing Dr", "Closing Cr"],
            tb_rows, ["l", "r", "r", "r", "r", "r", "r"],
            total_row=["TOTAL", f2(totals["od"]), f2(totals["oc"]),
                        f2(totals["d"]), f2(totals["c"]),
                        f2(totals["cd"]), f2(totals["cc"])],
            footer="Source: GL Entry for accounts where account_type = 'Cash'"
        ))
    else:
        parts.append("<p><i>No cash-type accounts found.</i></p>")
    parts.append('</div>')

    # ── END OF REPORT ──
    parts.append(f"""
    <div class="report-end">
        <p class="end-title">&mdash; END OF REPORT &mdash;</p>
        <p>{company} &nbsp;|&nbsp; Confidential &ndash; Board of Directors Only
        &nbsp;|&nbsp; Generated {generated}</p>
    </div>
    """)

    return "\n".join(parts)


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def _scalar(sql, params):
    result = frappe.db.sql(sql, params)
    return result[0][0] if result else 0


def _get_currency(company):
    if company:
        return frappe.get_cached_value("Company", company, "default_currency") or "USD"
    dc = frappe.db.get_single_value("Global Defaults", "default_company")
    if dc:
        return frappe.get_cached_value("Company", dc, "default_currency") or "USD"
    return "USD"


def _fmt(amount, currency="USD"):
    from frappe.utils import fmt_money
    try:
        return fmt_money(amount, currency=currency)
    except Exception:
        return f"{currency} {flt(amount):,.2f}"
