import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from dagaar_fuel_station.dagaar_fuel_station.utils import get_last_nozzle_closing, get_item_rate, get_pos_price_list, validate_company_for_pos_profile


class ShiftClosingEntry(Document):
    def validate(self):
        validate_company_for_pos_profile(self.company, self.pos_profile)
        self.set_missing_values()
        self.calculate_lines()
        self.validate_lines()
        self.calculate_totals()

    def set_missing_values(self):
        if self.company and not self.currency:
            self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
        seen = set()
        for row in self.lines:
            if row.fuel_nozzle in seen:
                frappe.throw(_("Duplicate nozzle {0} in lines.").format(row.fuel_nozzle))
            seen.add(row.fuel_nozzle)
            if row.fuel_nozzle:
                nozzle = frappe.get_cached_doc("Fuel Nozzle", row.fuel_nozzle)
                row.fuel_pump = nozzle.fuel_pump
                row.item = nozzle.item
                row.uom = nozzle.uom or frappe.get_cached_value("Item", nozzle.item, "stock_uom")
                row.warehouse = nozzle.warehouse
                if not row.opening_reading:
                    row.opening_reading = get_last_nozzle_closing(row.fuel_nozzle)
                price_list = get_pos_price_list(self.pos_profile)
                row.rate = get_item_rate(nozzle.item, price_list, row.uom, company=self.company, posting_date=self.date)

    def calculate_lines(self):
        for row in self.lines:
            row.metered_qty = flt(row.closing_reading) - flt(row.opening_reading)
            row.net_billable_qty = flt(row.metered_qty) - flt(row.test_qty) - flt(row.calibration_qty) + flt(row.adjustment_qty)
            row.gross_amount = flt(row.metered_qty) * flt(row.rate)
            row.net_billable_amount = flt(row.net_billable_qty) * flt(row.rate)

    def validate_lines(self):
        for row in self.lines:
            if flt(row.closing_reading) < flt(row.opening_reading):
                frappe.throw(_("Closing reading cannot be less than opening reading for nozzle {0}.").format(row.fuel_nozzle))
            if flt(row.net_billable_qty) < 0:
                frappe.throw(_("Net billable quantity cannot be negative for nozzle {0}.").format(row.fuel_nozzle))
            if row.warehouse:
                wh_company = frappe.db.get_value("Warehouse", row.warehouse, "company")
                if wh_company and wh_company != self.company:
                    frappe.throw(_("Warehouse {0} must belong to company {1}.").format(row.warehouse, self.company))

    def calculate_totals(self):
        self.total_metered_qty = sum(flt(d.metered_qty) for d in self.lines)
        self.total_net_billable_qty = sum(flt(d.net_billable_qty) for d in self.lines)
        self.total_gross_amount = sum(flt(d.gross_amount) for d in self.lines)
        self.total_net_billable_amount = sum(flt(d.net_billable_amount) for d in self.lines)
        self.expected_cash_amount = self.total_net_billable_amount
        self.cash_over_short = flt(self.actual_cash_on_hand) - flt(self.expected_cash_amount)
