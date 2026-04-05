
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from dagaar_fuel_station.dagaar_fuel_station.utils import (
    get_company_currency,
    get_currency_context,
    get_exchange_rate_safe,
    get_item_rate,
    get_last_nozzle_closing,
    get_pos_price_list,
    validate_company_for_pos_profile,
)


@frappe.whitelist()
def get_station_nozzles(company=None, pos_profile=None, include_existing=False, existing_nozzles=None, currency=None, posting_date=None):
    if not company or not pos_profile:
        return []

    existing = set()
    if existing_nozzles:
        parsed = frappe.parse_json(existing_nozzles) if isinstance(existing_nozzles, str) else existing_nozzles
        existing = {d for d in (parsed or []) if d}

    nozzles = frappe.get_all(
        "Fuel Nozzle",
        filters={"company": company, "pos_profile": pos_profile, "active": 1},
        fields=["name", "nozzle_code", "fuel_pump", "item", "uom", "warehouse", "sequence_no"],
        order_by="fuel_pump asc, sequence_no asc, nozzle_code asc, name asc",
    )

    context = get_currency_context(company, currency, posting_date)
    out = []
    for nozzle in nozzles:
        if not include_existing and nozzle.name in existing:
            continue
        rate = get_item_rate(nozzle.item, get_pos_price_list(pos_profile), nozzle.uom, company=company, posting_date=posting_date, target_currency=context.get("currency"))
        out.append(
            {
                "fuel_pump": nozzle.fuel_pump,
                "fuel_nozzle": nozzle.name,
                "display_name": nozzle.nozzle_code or nozzle.name,
                "item": nozzle.item,
                "uom": nozzle.uom or frappe.get_cached_value("Item", nozzle.item, "stock_uom"),
                "warehouse": nozzle.warehouse,
                "opening_reading": get_last_nozzle_closing(nozzle.name),
                "rate": rate,
                "base_rate": flt(rate) * flt(context.get("conversion_rate")),
            }
        )
    return out


@frappe.whitelist()
def get_latest_opening_readings(nozzles=None, company=None, pos_profile=None):
    parsed = frappe.parse_json(nozzles) if isinstance(nozzles, str) else (nozzles or [])
    out = {}
    for nozzle in parsed:
        if not nozzle:
            continue
        out[nozzle] = get_last_nozzle_closing(nozzle)
    return out


class ShiftClosingEntry(Document):
    def validate(self):
        validate_company_for_pos_profile(self.company, self.pos_profile)
        self.set_currency_context()
        self.auto_add_station_nozzles()
        self.set_missing_values()
        self.calculate_lines()
        self.validate_lines()
        self.calculate_totals()
        self.set_status()

    def on_submit(self):
        self.db_set("status", "Open", update_modified=False)

    def on_cancel(self):
        self.db_set("status", "Cancelled", update_modified=False)

    def set_currency_context(self):
        ctx = get_currency_context(self.company, self.currency, self.date)
        self.home_currency = ctx.get("home_currency")
        self.currency = ctx.get("currency")
        self.conversion_rate = flt(ctx.get("conversion_rate")) or 1

    def auto_add_station_nozzles(self):
        if not self.company or not self.pos_profile:
            return
        existing = {d.fuel_nozzle for d in self.lines if d.fuel_nozzle}
        for nozzle in get_station_nozzles(self.company, self.pos_profile, include_existing=False, existing_nozzles=list(existing), currency=self.currency, posting_date=self.date):
            self.append("lines", nozzle)

    def set_missing_values(self):
        if self.company and not self.currency:
            self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
        if self.company and not self.home_currency:
            self.home_currency = get_company_currency(self.company)
        if not self.conversion_rate:
            self.conversion_rate = get_exchange_rate_safe(self.currency, self.home_currency, self.date)

        seen = set()
        price_list = get_pos_price_list(self.pos_profile)

        for row in self.lines:
            if not row.fuel_nozzle:
                continue
            if row.fuel_nozzle in seen:
                frappe.throw(_("Duplicate nozzle {0} is not allowed in the same Shift Closing Entry.").format(row.fuel_nozzle))
            seen.add(row.fuel_nozzle)

            nozzle = frappe.get_cached_doc("Fuel Nozzle", row.fuel_nozzle)
            row.display_name = nozzle.nozzle_code or nozzle.name
            row.fuel_pump = row.fuel_pump or nozzle.fuel_pump
            row.item = nozzle.item
            row.uom = nozzle.uom or frappe.get_cached_value("Item", nozzle.item, "stock_uom")
            row.warehouse = nozzle.warehouse
            row.opening_reading = get_last_nozzle_closing(row.fuel_nozzle)
            row.rate = get_item_rate(nozzle.item, price_list, row.uom, company=self.company, posting_date=self.date, target_currency=self.currency)
            row.base_rate = flt(row.rate) * flt(self.conversion_rate)

        self.lines = sorted(
            self.lines,
            key=lambda d: (
                d.fuel_pump or "",
                frappe.get_cached_value("Fuel Nozzle", d.fuel_nozzle, "sequence_no") if d.fuel_nozzle else 0,
                frappe.get_cached_value("Fuel Nozzle", d.fuel_nozzle, "nozzle_code") if d.fuel_nozzle else "",
                d.fuel_nozzle or "",
            ),
        )

    def calculate_lines(self):
        for row in self.lines:
            row.metered_qty = flt(row.closing_reading) - flt(row.opening_reading)
            row.net_billable_qty = flt(row.metered_qty) - flt(row.test_qty) - flt(row.calibration_qty) + flt(row.adjustment_qty)
            row.gross_amount = flt(row.metered_qty) * flt(row.rate)
            row.net_billable_amount = flt(row.net_billable_qty) * flt(row.rate)
            row.gross_amount_home = flt(row.gross_amount) * flt(self.conversion_rate)
            row.net_billable_amount_home = flt(row.net_billable_amount) * flt(self.conversion_rate)
            row.base_rate = flt(row.rate) * flt(self.conversion_rate)

    def validate_lines(self):
        for row in self.lines:
            if not row.fuel_pump:
                frappe.throw(_("Fuel Pump is required for nozzle row {0}.").format(row.idx))
            if flt(row.closing_reading) < flt(row.opening_reading):
                frappe.throw(_("Closing reading cannot be less than opening reading for nozzle {0}.").format(row.display_name or row.fuel_nozzle))
            if flt(row.net_billable_qty) < 0:
                frappe.throw(_("Net billable quantity cannot be negative for nozzle {0}.").format(row.display_name or row.fuel_nozzle))
            if row.warehouse:
                wh_company = frappe.db.get_value("Warehouse", row.warehouse, "company")
                if wh_company and wh_company != self.company:
                    frappe.throw(_("Warehouse {0} must belong to company {1}.").format(row.warehouse, self.company))

    def calculate_totals(self):
        self.total_metered_qty = sum(flt(d.metered_qty) for d in self.lines)
        self.total_net_billable_qty = sum(flt(d.net_billable_qty) for d in self.lines)
        self.total_gross_amount = sum(flt(d.gross_amount) for d in self.lines)
        self.total_net_billable_amount = sum(flt(d.net_billable_amount) for d in self.lines)
        self.total_gross_amount_home = sum(flt(d.gross_amount_home) for d in self.lines)
        self.total_net_billable_amount_home = sum(flt(d.net_billable_amount_home) for d in self.lines)
        self.expected_cash_amount = self.total_net_billable_amount
        self.expected_cash_amount_home = flt(self.expected_cash_amount) * flt(self.conversion_rate)
        self.opening_cash_float_home = flt(self.opening_cash_float) * flt(self.conversion_rate)
        self.actual_cash_on_hand_home = flt(self.actual_cash_on_hand) * flt(self.conversion_rate)
        self.cash_over_short = flt(self.actual_cash_on_hand) - flt(self.expected_cash_amount)
        self.cash_over_short_home = flt(self.cash_over_short) * flt(self.conversion_rate)

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
        elif self.pump_reading_entry:
            self.status = "Closed"
        elif self.docstatus == 1:
            self.status = "Open"
        else:
            self.status = "Draft"
