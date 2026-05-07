import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate

from dagaar_fuel_station.dagaar_fuel_station.nozzle_meter_state import (
    record_fuel_transfer,
    reverse_fuel_transfer,
)
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
def get_nozzle_transfer_defaults(nozzle=None, pos_profile=None, currency=None, company=None, posting_date=None):
    if not nozzle:
        return {}
    nozzle_doc = frappe.get_cached_doc("Fuel Nozzle", nozzle)
    rate = get_item_rate(
        nozzle_doc.item,
        get_pos_price_list(pos_profile),
        nozzle_doc.uom,
        company=company,
        posting_date=posting_date,
        target_currency=currency,
    )
    home_currency = get_company_currency(company)
    conversion_rate = get_exchange_rate_safe(currency or home_currency, home_currency, posting_date or nowdate())
    opening = get_last_nozzle_closing(nozzle)
    return {
        "display_name": nozzle_doc.nozzle_code or nozzle_doc.name,
        "fuel_pump": nozzle_doc.fuel_pump,
        "item": nozzle_doc.item,
        "uom": nozzle_doc.uom,
        "source_warehouse": nozzle_doc.warehouse,
        "cost_center": nozzle_doc.cost_center,
        "opening_reading": opening,
        "rate": rate,
        "base_rate": flt(rate) * flt(conversion_rate),
    }


class FuelTransferEntry(Document):
    def before_validate(self):
        self.set_missing_header_values()
        self.set_currency_context()
        self.prepare_lines()
        self.calculate_totals()
        self.set_status()

    def validate(self):
        validate_company_for_pos_profile(self.company, self.pos_profile)
        if not self.lines:
            frappe.throw(_("Add at least one transfer line."))
        seen = set()
        for row in self.lines:
            if not row.fuel_nozzle:
                frappe.throw(_("Fuel Nozzle is required in all lines."))
            key = row.fuel_nozzle
            if key in seen:
                frappe.throw(_("Duplicate nozzle {0} is not allowed in the same transfer document.").format(row.fuel_nozzle))
            seen.add(key)
            if not row.target_warehouse:
                frappe.throw(_("Target Warehouse is required for nozzle {0}.").format(row.fuel_nozzle))
            if row.target_warehouse == row.source_warehouse:
                frappe.throw(_("Target Warehouse must be different from Source Warehouse for nozzle {0}.").format(row.fuel_nozzle))
            if flt(row.transfer_qty) <= 0:
                frappe.throw(_("Transfer Qty must be greater than zero for nozzle {0}.").format(row.fuel_nozzle))
            if flt(row.closing_reading) < flt(row.opening_reading):
                frappe.throw(_("Closing Reading cannot be less than Opening Reading for nozzle {0}.").format(row.fuel_nozzle))
        if self.stock_entry and frappe.db.exists("Stock Entry", self.stock_entry) and self.docstatus == 0:
            frappe.throw(_("Linked Stock Entry already exists. Cancel/amend instead of recreating."))

    def on_submit(self):
        if self.stock_entry:
            frappe.throw(_("Stock Entry already created for this document."))
        stock_entry = self.create_stock_entry()
        self.db_set("stock_entry", stock_entry.name, update_modified=False)
        self.db_set("status", "Transferred", update_modified=False)
        record_fuel_transfer(self)

    def on_cancel(self):
        if self.stock_entry and frappe.db.exists("Stock Entry", self.stock_entry):
            se = frappe.get_doc("Stock Entry", self.stock_entry)
            if se.docstatus == 1:
                se.cancel()
        reverse_fuel_transfer(self)
        self.db_set("status", "Cancelled", update_modified=False)

    def set_missing_header_values(self):
        self.date = self.date or nowdate()
        if not self.company and self.pos_profile:
            self.company = frappe.db.get_value("POS Profile", self.pos_profile, "company")
        if not self.currency and self.company:
            self.currency = get_company_currency(self.company)

    def set_currency_context(self):
        ctx = get_currency_context(self.company, self.currency, self.date)
        self.home_currency = ctx.get("home_currency")
        self.currency = ctx.get("currency")
        self.conversion_rate = flt(ctx.get("conversion_rate")) or 1

    def prepare_lines(self):
        prepared = []
        for row in self.lines:
            if not row.fuel_nozzle:
                continue
            nozzle_doc = frappe.get_cached_doc("Fuel Nozzle", row.fuel_nozzle)
            row.display_name = nozzle_doc.nozzle_code or nozzle_doc.name
            row.fuel_pump = nozzle_doc.fuel_pump
            row.item = nozzle_doc.item
            row.uom = nozzle_doc.uom
            row.source_warehouse = nozzle_doc.warehouse
            row.cost_center = nozzle_doc.cost_center
            row.opening_reading = get_last_nozzle_closing(row.fuel_nozzle)
            row.rate = get_item_rate(
                nozzle_doc.item,
                get_pos_price_list(self.pos_profile),
                nozzle_doc.uom,
                company=self.company,
                posting_date=self.date,
                target_currency=self.currency,
            )
            row.base_rate = flt(row.rate) * flt(self.conversion_rate)
            row.closing_reading = flt(row.opening_reading) + flt(row.transfer_qty)
            row.amount = flt(row.transfer_qty) * flt(row.rate)
            row.amount_home = flt(row.amount) * flt(self.conversion_rate)
            prepared.append(row)
        self.set("lines", [])
        for row in prepared:
            self.append("lines", row)

    def calculate_totals(self):
        self.total_transfer_qty = sum(flt(d.transfer_qty) for d in self.lines)
        self.total_amount = sum(flt(d.amount) for d in self.lines)
        self.total_amount_home = sum(flt(d.amount_home) for d in self.lines)

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
        elif self.docstatus == 1 and self.stock_entry:
            self.status = "Transferred"
        elif self.docstatus == 1:
            self.status = "Submitted"
        else:
            self.status = "Draft"

    def create_stock_entry(self):
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.purpose = "Material Transfer"
        se.company = self.company
        se.posting_date = self.date
        se.set_posting_time = 1
        if self.posting_time:
            se.posting_time = self.posting_time
        se.remarks = _("Auto-created from Fuel Transfer Entry {0}").format(self.name)
        for row in self.lines:
            se.append("items", {
                "item_code": row.item,
                "s_warehouse": row.source_warehouse,
                "t_warehouse": row.target_warehouse,
                "qty": row.transfer_qty,
                "uom": row.uom,
                "cost_center": row.cost_center,
                "basic_rate": row.base_rate if self.currency != self.home_currency else row.rate,
                "transfer_qty": row.transfer_qty,
                "description": _("Transfer through nozzle {0}").format(row.display_name or row.fuel_nozzle),
            })
        se.flags.ignore_permissions = True
        se.insert()
        se.submit()
        return se
