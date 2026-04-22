# -*- coding: utf-8 -*-
# Fuel Customer Ledger – Dagaar Fuel Station
# Path: dagaar_fuel_station/dagaar_fuel_station/report/fuel_customer_ledger/
#
# Based on DagaarSoft Party Statement with beautiful PDF output
# matching the Night Report styling.

import json
from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import cstr, getdate, flt, nowdate, now_datetime

from erpnext import get_company_currency, get_default_company
from erpnext.accounts.report.utils import convert_to_presentation_currency, get_currency
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children


# ══════════════════════════════════════════════════════════
#  GRID EXECUTE
# ══════════════════════════════════════════════════════════

def execute(filters=None):
    if not filters:
        return [], []

    validate_filters(filters)

    if filters.get("party"):
        filters.party = frappe.parse_json(filters.get("party"))
    if filters.get("cost_center"):
        filters.cost_center = frappe.parse_json(filters.get("cost_center"))

    filters = set_account_currency(filters)
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data


# ══════════════════════════════════════════════════════════
#  PDF
# ══════════════════════════════════════════════════════════

@frappe.whitelist()
def generate_pdf(filters=None):
    if isinstance(filters, str):
        filters = json.loads(filters)
    if not filters:
        frappe.throw(_("Filters are required"))

    validate_filters(filters)
    if filters.get("party"):
        filters["party"] = frappe.parse_json(filters.get("party"))
    if filters.get("cost_center"):
        filters["cost_center"] = frappe.parse_json(filters.get("cost_center"))

    filters = set_account_currency(filters)
    data = get_data(filters)
    html = _render_pdf_html(filters, data)

    from frappe.utils.pdf import get_pdf
    pdf_bytes = get_pdf(html, {
        "page-size": "A4",
        "orientation": "Landscape",
        "margin-top": "10mm",
        "margin-bottom": "12mm",
        "margin-left": "8mm",
        "margin-right": "8mm",
        "footer-font-size": "7",
        "footer-center": "Page [page] of [topage]",
        "no-outline": "",
    })

    token = frappe.generate_hash(length=20)
    frappe.cache.set_value(f"fuel_ledger_pdf_{token}", pdf_bytes, expires_in_sec=300)
    return token


@frappe.whitelist()
def download_pdf(token=None):
    if not token:
        frappe.throw(_("Missing token"))
    pdf_bytes = frappe.cache.get_value(f"fuel_ledger_pdf_{token}")
    if not pdf_bytes:
        frappe.throw(_("Report expired. Please regenerate."))
    frappe.local.response.filename = "Fuel_Customer_Ledger.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"


# ══════════════════════════════════════════════════════════
#  HTML RENDERER (Night Report style)
# ══════════════════════════════════════════════════════════

def _render_pdf_html(filters, data):
    company = filters.get("company", "")
    party_name = filters.get("party_name", "")
    parties = filters.get("party", [])
    party_label = party_name or (", ".join(parties) if isinstance(parties, list) else cstr(parties)) or "All"
    party_type = filters.get("party_type", "Customer")
    from_date = filters.get("from_date", "")
    to_date = filters.get("to_date", "")
    currency = filters.get("presentation_currency") or filters.get("company_currency") or get_company_currency(company)
    show_notes = filters.get("show_notes", 1)
    generated = now_datetime().strftime("%d/%m/%Y %H:%M")

    f2 = lambda v: f"{flt(v):,.2f}"

    # Column widths
    if show_notes:
        w = {"num": "3%", "date": "8%", "tid": "11%", "items": "22%",
             "notes": "22%", "debit": "11%", "credit": "11%", "bal": "12%"}
    else:
        w = {"num": "3%", "date": "9%", "tid": "13%", "items": "35%",
             "notes": "0%", "debit": "13%", "credit": "13%", "bal": "14%"}

    css = f"""<style>
    @page {{ size: A4 landscape; margin: 12mm 10mm 14mm 10mm; }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: "Segoe UI", Helvetica, Arial, sans-serif; font-size:10pt; color:#111; line-height:1.35; }}

    /* ── Header ── */
    .stmt-header {{ text-align:center; padding-bottom:10px; margin-bottom:0; }}
    .stmt-header .company {{ font-size:16pt; font-weight:700; color:#1a237e; letter-spacing:0.5px; margin-bottom:1px; }}
    .stmt-header .title {{ font-size:11pt; color:#444; font-weight:400; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px; }}
    .stmt-header .party {{ font-size:11pt; font-weight:600; color:#111; margin-bottom:4px; }}
    .stmt-header .details {{ font-size:9pt; color:#555; }}
    .stmt-header .details b {{ color:#222; }}
    .divider {{ border:none; height:2px; background:linear-gradient(90deg, #1a237e, #42a5f5, #1a237e); margin:0 0 10px; }}

    /* ── Table ── */
    table.ledger {{ width:100%; border-collapse:collapse; border:1px solid #bbb; }}
    table.ledger th {{ background:#1a237e; color:#fff; font-size:9pt; font-weight:600;
         padding:6px 6px; text-align:left; border:1px solid #1a237e; }}
    table.ledger th.r {{ text-align:right; }}
    table.ledger th.sm {{ font-size:8pt; }}
    table.ledger td {{ padding:5px 6px; font-size:9.5pt; color:#111; border-bottom:1px solid #ddd;
         border-left:1px solid #eee; vertical-align:top; }}
    table.ledger td.r {{ text-align:right; font-variant-numeric:tabular-nums; }}
    table.ledger td.rb {{ text-align:right; font-weight:600; }}

    /* ── Transaction ID cell: smaller font ── */
    table.ledger td.tid {{ font-size:7.5pt; color:#111; }}

    /* ── Row styles ── */
    table.ledger tr.alt {{ background:#f6f7fb; }}
    table.ledger tr.opening td {{ font-weight:600; font-style:italic; border-bottom:1.5px solid #999; background:#f0f0f0; }}
    table.ledger tr.summary td {{ font-weight:700; border-top:2.5px double #1a237e; border-bottom:2.5px double #1a237e; }}
    table.ledger tr.closing td {{ font-weight:700; border-top:2.5px double #1a237e; }}
    table.ledger tr.litres-row td {{ font-size:9pt; color:#222; border-bottom:1px solid #ddd; }}
    table.ledger tr.litres-total td {{ font-size:9pt; font-weight:700; border-top:2px solid #1a237e; border-bottom:2.5px double #1a237e; }}

    /* ── Items Details ── */
    .items-cell {{ font-size:8.5pt; color:#222; line-height:1.3; overflow:hidden; word-wrap:break-word; }}

    /* ── Notes: smaller font, truncated in Python ── */
    .notes-cell {{ font-size:7.5pt; color:#333; line-height:1.3; overflow:hidden; word-wrap:break-word; }}

    /* ── Footer ── */
    .stmt-footer {{ text-align:center; margin-top:14px; padding-top:8px; }}
    .stmt-footer .line {{ height:2px; background:linear-gradient(90deg, #1a237e, #42a5f5, #1a237e); margin-bottom:8px; }}
    .stmt-footer .end {{ font-size:9pt; color:#555; font-weight:600; margin-bottom:3px; }}
    .stmt-footer .sub {{ font-size:7.5pt; color:#999; }}

    {"table.ledger th.notes-col, table.ledger td.notes-col {{ display:none; }}" if not show_notes else ""}
    </style>"""

    parts = [css]

    # Header
    parts.append(f"""
    <div class="stmt-header">
        <div class="company">{company}</div>
        <div class="title">{party_type} Statement of Account</div>
        <div class="party">{party_label}</div>
        <div class="details">
            <b>From:</b> {from_date} &nbsp;&nbsp; <b>To:</b> {to_date} &nbsp;&nbsp;
            <b>Currency:</b> {currency} &nbsp;&nbsp;
            <b>Printed:</b> {generated}
        </div>
    </div>
    <hr class="divider">
    """)

    # Table header
    notes_th = f'<th class="notes-col sm" style="width:{w["notes"]}">Notes / Remarks</th>' if show_notes else ''
    parts.append(f"""<table class="ledger">
    <thead><tr>
        <th style="width:{w['num']}">#</th>
        <th style="width:{w['date']}">Date</th>
        <th class="sm" style="width:{w['tid']}">Transaction</th>
        <th style="width:{w['items']}">Items Details</th>
        {notes_th}
        <th class="r" style="width:{w['debit']}">Debit ({currency})</th>
        <th class="r" style="width:{w['credit']}">Credit ({currency})</th>
        <th class="r" style="width:{w['bal']}">Balance ({currency})</th>
    </tr></thead><tbody>""")

    # Collect litres per item from invoice vouchers shown
    item_qty_map = {}  # {item_name: total_qty}
    shown_invoices = set()

    # Rows
    alt_idx = 0
    for row in data:
        voucher = cstr(row.get("voucher_no", ""))
        vt = row.get("voucher_type", "")
        is_opening = voucher == _("Opening Balance")
        is_total = voucher == _("Total")
        is_closing = voucher == _("Closing Balance")
        is_summary = is_opening or is_total or is_closing

        # Track invoices for litres summary
        if vt in ("Sales Invoice", "Purchase Invoice") and voucher not in shown_invoices:
            shown_invoices.add(voucher)
            _collect_item_qty(voucher, vt, item_qty_map)

        if is_opening:
            tr_cls = ' class="opening"'
        elif is_total:
            tr_cls = ' class="summary"'
        elif is_closing:
            tr_cls = ' class="closing"'
        else:
            alt_idx += 1
            tr_cls = ' class="alt"' if alt_idx % 2 == 0 else ""

        pd_val = row.get("posting_date")
        date_str = cstr(pd_val) if pd_val else ""
        tid = f"<b>{voucher}</b>" if is_summary else voucher

        # Items details — join with " | "
        raw_items = cstr(row.get("items_details", ""))
        items = raw_items.replace("\n", " &nbsp;| &nbsp;")

        # Notes — truncate in Python for wkhtmltopdf compatibility
        raw_notes = cstr(row.get("notes_remarks", "")).replace("\n", " ").strip()
        if len(raw_notes) > 90:
            notes = raw_notes[:87] + "..."
        else:
            notes = raw_notes

        debit = flt(row.get("debit", 0))
        credit = flt(row.get("credit", 0))
        balance = row.get("balance")
        debit_str = f2(debit) if debit else ""
        credit_str = f2(credit) if credit else ""
        bal_str = f2(balance) if balance is not None else ""

        notes_td = f'<td class="notes-cell notes-col">{notes}</td>' if show_notes else ''

        parts.append(f"""<tr{tr_cls}>
            <td>{row.get("row_num", "")}</td>
            <td>{date_str}</td>
            <td class="tid">{tid}</td>
            <td class="items-cell">{items}</td>
            {notes_td}
            <td class="r">{debit_str}</td>
            <td class="r">{credit_str}</td>
            <td class="rb">{bal_str}</td>
        </tr>""")

    # Litres summary rows — inline in the same table, directly under closing
    if item_qty_map:
        ncols = 8 if show_notes else 7
        # Empty spacer cells for columns before Debit
        empty_start = '<td></td>' * (ncols - 3)  # all cols except last 3 (item name goes in items col)

        for item_name in sorted(item_qty_map.keys()):
            qty = flt(item_qty_map[item_name], 3)
            notes_td_empty = '<td class="notes-col"></td>' if show_notes else ''
            parts.append(f"""<tr class="litres-row">
                <td></td><td></td><td></td>
                <td class="items-cell">{item_name}</td>
                {notes_td_empty}
                <td class="r" colspan="2">Qty / Litres</td>
                <td class="rb">{qty:,.3f}</td>
            </tr>""")

        grand_qty = sum(flt(v) for v in item_qty_map.values())
        notes_td_empty = '<td class="notes-col"></td>' if show_notes else ''
        parts.append(f"""<tr class="litres-total">
            <td></td><td></td><td></td>
            <td><b>TOTAL LITRES</b></td>
            {notes_td_empty}
            <td class="r" colspan="2"></td>
            <td class="rb">{flt(grand_qty, 3):,.3f}</td>
        </tr>""")

    parts.append("</tbody></table>")

    # Footer
    parts.append(f"""
    <div class="stmt-footer">
        <div class="line"></div>
        <div class="end">&mdash; End of Statement &mdash;</div>
        <div class="sub">{company} &nbsp;|&nbsp; {party_type}: {party_label} &nbsp;|&nbsp;
        Period: {from_date} to {to_date} &nbsp;|&nbsp; Generated {generated}</div>
    </div>
    """)

    return "\n".join(parts)


def _collect_item_qty(voucher_no, voucher_type, item_qty_map):
    """Collect qty per item from invoice child table for the litres summary."""
    if voucher_type == "Sales Invoice":
        child_table = "Sales Invoice Item"
    elif voucher_type == "Purchase Invoice":
        child_table = "Purchase Invoice Item"
    else:
        return
    items = frappe.db.sql("""
        SELECT item_name, qty FROM `tab{child_table}`
        WHERE parent = %s AND parenttype = %s ORDER BY idx
    """.format(child_table=child_table), (voucher_no, voucher_type), as_dict=1)
    for item in items:
        name = cstr(item.get("item_name", ""))
        item_qty_map[name] = flt(item_qty_map.get(name, 0)) + flt(item.get("qty", 0))


# ══════════════════════════════════════════════════════════
#  DATA LOGIC (from DagaarSoft Party Statement)
# ══════════════════════════════════════════════════════════

def validate_filters(filters):
    if not filters.get("company"):
        frappe.throw(_("{0} is mandatory").format(_("Company")))
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw(_("From Date and To Date are mandatory"))
    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw(_("From Date must be before To Date"))
    if not filters.get("party_type"):
        frappe.throw(_("Party Type is mandatory"))


def set_account_currency(filters):
    filters["company_currency"] = frappe.get_cached_value(
        "Company", filters.get("company"), "default_currency"
    )
    if filters.get("party") and len(filters.get("party")) == 1 and filters.get("party_type"):
        gle_currency = frappe.db.get_value(
            "GL Entry",
            {"party_type": filters.get("party_type"), "party": filters.get("party")[0],
             "company": filters.get("company")},
            "account_currency",
        )
        account_currency = gle_currency or filters.get("company_currency")
    else:
        account_currency = filters.get("company_currency")
    filters["account_currency"] = account_currency
    if filters.get("presentation_currency"):
        filters["account_currency"] = filters.get("presentation_currency")
    return filters


def get_columns(filters):
    currency = filters.get("presentation_currency") or get_company_currency(filters.get("company"))
    show_notes = filters.get("show_notes", 1)

    columns = [
        {"label": _("#"), "fieldname": "row_num", "fieldtype": "Data", "width": 40},
        {"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": _("Transaction ID"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link",
         "options": "voucher_type", "width": 150},
        {"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data",
         "width": 0, "hidden": 1},
        {"label": _("Items Details"), "fieldname": "items_details", "fieldtype": "Data",
         "width": 350 if not show_notes else 280},
    ]

    if show_notes:
        columns.append({
            "label": _("Notes / Remarks"), "fieldname": "notes_remarks",
            "fieldtype": "Data", "width": 280,
        })

    columns += [
        {"label": _("Debit ({0})").format(currency), "fieldname": "debit",
         "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Credit ({0})").format(currency), "fieldname": "credit",
         "fieldtype": "Currency", "options": "currency", "width": 130},
        {"label": _("Balance ({0})").format(currency), "fieldname": "balance",
         "fieldtype": "Currency", "options": "currency", "width": 150},
        {"label": _("Currency"), "fieldname": "currency", "fieldtype": "Data",
         "hidden": 1, "width": 0},
    ]
    return columns


def get_conditions(filters):
    conditions = [
        "company = %(company)s",
        "party_type = %(party_type)s",
        "is_cancelled = 0",
    ]
    if filters.get("party"):
        conditions.append("party in %(party)s")
    if filters.get("cost_center"):
        filters["cost_center"] = get_cost_centers_with_children(filters.get("cost_center"))
        conditions.append("cost_center in %(cost_center)s")
    if filters.get("include_default_book_entries"):
        company_fb = frappe.get_cached_value("Company", filters.get("company"), "default_finance_book")
        filters["company_fb"] = company_fb or ""
        if filters.get("finance_book"):
            conditions.append("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)")
        else:
            conditions.append("(finance_book in (%(company_fb)s, '') OR finance_book IS NULL)")
    else:
        if filters.get("finance_book"):
            conditions.append("(finance_book in (%(finance_book)s, '') OR finance_book IS NULL)")
        else:
            conditions.append("(finance_book in ('') OR finance_book IS NULL)")
    return " and ".join(conditions)


def get_gl_entries(filters):
    conditions = get_conditions(filters)
    gl_entries = frappe.db.sql("""
        SELECT name as gl_entry, posting_date, account, party_type, party,
               voucher_type, voucher_no, debit, credit,
               debit_in_account_currency, credit_in_account_currency,
               against_voucher_type, against_voucher, is_opening, remarks, creation
        FROM `tabGL Entry`
        WHERE {conditions}
            AND (posting_date <= %(to_date)s OR is_opening = 'Yes')
        ORDER BY posting_date, creation
    """.format(conditions=conditions), filters, as_dict=1)
    if filters.get("presentation_currency"):
        currency_map = get_currency(filters)
        return convert_to_presentation_currency(gl_entries, currency_map)
    return gl_entries


def is_credit_sale(voucher_no):
    si = frappe.db.get_value("Sales Invoice", {"name": voucher_no, "docstatus": 1},
                             ["outstanding_amount", "paid_amount", "grand_total", "is_return"], as_dict=1)
    if not si:
        return False
    if si.is_return:
        return True
    if flt(si.outstanding_amount) > 0:
        return True
    if flt(si.outstanding_amount) == 0 and flt(si.paid_amount) >= flt(si.grand_total):
        return False
    return True


def is_credit_purchase(voucher_no):
    pi = frappe.db.get_value("Purchase Invoice", {"name": voucher_no, "docstatus": 1},
                             ["outstanding_amount", "paid_amount", "grand_total", "is_return"], as_dict=1)
    if not pi:
        return False
    if pi.is_return:
        return True
    if flt(pi.outstanding_amount) > 0:
        return True
    if flt(pi.outstanding_amount) == 0 and flt(pi.paid_amount) >= flt(pi.grand_total):
        return False
    return True


def get_items_details_for_invoice(voucher_no, voucher_type):
    if voucher_type == "Sales Invoice":
        child_table = "Sales Invoice Item"
        parent_doctype = "Sales Invoice"
    elif voucher_type == "Purchase Invoice":
        child_table = "Purchase Invoice Item"
        parent_doctype = "Purchase Invoice"
    else:
        return ""
    docstatus = frappe.db.get_value(parent_doctype, voucher_no, "docstatus")
    if docstatus != 1:
        return ""
    items = frappe.db.sql("""
        SELECT item_name, qty, rate, amount
        FROM `tab{child_table}`
        WHERE parent = %s AND parenttype = %s ORDER BY idx
    """.format(child_table=child_table), (voucher_no, voucher_type), as_dict=1)
    if not items:
        return ""
    lines = []
    for item in items:
        qty_s = "{0:g}".format(flt(item.qty))
        rate_s = "{0:,.2f}".format(flt(item.rate))
        amt_s = "{0:,.2f}".format(flt(item.amount))
        lines.append(f"{cstr(item.item_name)} - {qty_s} x {rate_s} = {amt_s}")
    return "\n".join(lines)


def get_item_details_for_payment(voucher_no):
    val = frappe.db.get_value("Payment Entry", {"name": voucher_no, "docstatus": 1}, "reference_no")
    return cstr(val) if val else ""


def get_item_details_for_journal(voucher_no):
    val = frappe.db.get_value("Journal Entry", {"name": voucher_no, "docstatus": 1}, "user_remark")
    return cstr(val) if val else ""


def get_notes_remarks(voucher_no, voucher_type):
    if voucher_type == "Sales Invoice":
        try:
            val = frappe.db.get_value("Sales Invoice", {"name": voucher_no, "docstatus": 1}, "posa_notes")
            if val:
                return cstr(val)
        except Exception:
            pass
        try:
            val = frappe.db.get_value("Sales Invoice", {"name": voucher_no, "docstatus": 1}, "remarks")
            return cstr(val) if val else ""
        except Exception:
            return ""
    elif voucher_type == "Purchase Invoice":
        val = frappe.db.get_value("Purchase Invoice", {"name": voucher_no, "docstatus": 1}, "remarks")
        return cstr(val) if val else ""
    elif voucher_type == "Payment Entry":
        val = frappe.db.get_value("Payment Entry", {"name": voucher_no, "docstatus": 1}, "reference_no")
        return cstr(val) if val else ""
    return ""


def get_data(filters):
    gl_entries = get_gl_entries(filters)
    currency = filters.get("presentation_currency") or get_company_currency(filters.get("company"))
    from_date = getdate(filters.get("from_date"))

    opening_debit = 0.0
    opening_credit = 0.0
    total_debit = 0.0
    total_credit = 0.0
    period_entries = []

    for gle in gl_entries:
        posting_date = getdate(gle.posting_date)
        if posting_date < from_date or cstr(gle.is_opening) == "Yes":
            opening_debit += flt(gle.debit)
            opening_credit += flt(gle.credit)
        else:
            period_entries.append(gle)

    opening_balance = flt(opening_debit) - flt(opening_credit)
    data = []
    row_num = 1

    data.append({
        "row_num": row_num, "posting_date": None,
        "voucher_no": _("Opening Balance"), "voucher_type": None,
        "items_details": "", "notes_remarks": "",
        "debit": flt(opening_debit), "credit": flt(opening_credit),
        "balance": flt(opening_balance), "currency": currency,
    })
    row_num += 1
    running_balance = flt(opening_balance)

    voucher_map = OrderedDict()
    for gle in period_entries:
        key = (gle.voucher_type, gle.voucher_no)
        if key not in voucher_map:
            voucher_map[key] = {
                "posting_date": gle.posting_date, "voucher_type": gle.voucher_type,
                "voucher_no": gle.voucher_no, "debit": 0.0, "credit": 0.0,
            }
        voucher_map[key]["debit"] += flt(gle.debit)
        voucher_map[key]["credit"] += flt(gle.credit)

    show_net = filters.get("show_net_values_in_party_account")
    items_cache = {}
    notes_cache = {}
    credit_check_cache = {}

    for key, entry in voucher_map.items():
        vt = entry["voucher_type"]
        vn = entry["voucher_no"]

        if vt == "Sales Invoice":
            if vn not in credit_check_cache:
                credit_check_cache[vn] = is_credit_sale(vn)
            if not credit_check_cache[vn]:
                continue
        elif vt == "Purchase Invoice":
            if vn not in credit_check_cache:
                credit_check_cache[vn] = is_credit_purchase(vn)
            if not credit_check_cache[vn]:
                continue

        debit = flt(entry["debit"])
        credit = flt(entry["credit"])

        if show_net:
            net = debit - credit
            if net > 0:
                debit, credit = net, 0.0
            else:
                debit, credit = 0.0, abs(net)

        if debit == 0 and credit == 0:
            continue

        running_balance += debit - credit
        total_debit += debit
        total_credit += credit

        if vn not in items_cache:
            if vt in ("Sales Invoice", "Purchase Invoice"):
                items_cache[vn] = get_items_details_for_invoice(vn, vt)
            elif vt == "Payment Entry":
                items_cache[vn] = get_item_details_for_payment(vn)
            elif vt == "Journal Entry":
                items_cache[vn] = get_item_details_for_journal(vn)
            else:
                items_cache[vn] = ""

        if vn not in notes_cache:
            notes_cache[vn] = get_notes_remarks(vn, vt)

        data.append({
            "row_num": row_num, "posting_date": entry["posting_date"],
            "voucher_no": vn, "voucher_type": vt,
            "items_details": items_cache.get(vn, ""),
            "notes_remarks": notes_cache.get(vn, ""),
            "debit": debit, "credit": credit,
            "balance": flt(running_balance), "currency": currency,
        })
        row_num += 1

    data.append({
        "row_num": row_num, "posting_date": None,
        "voucher_no": _("Total"), "voucher_type": None,
        "items_details": "", "notes_remarks": "",
        "debit": flt(total_debit), "credit": flt(total_credit),
        "balance": None, "currency": currency,
    })
    row_num += 1

    closing_balance = flt(opening_balance) + flt(total_debit) - flt(total_credit)
    data.append({
        "row_num": row_num, "posting_date": None,
        "voucher_no": _("Closing Balance"), "voucher_type": None,
        "items_details": "", "notes_remarks": "",
        "debit": 0.0, "credit": 0.0,
        "balance": flt(closing_balance), "currency": currency,
    })

    return data
