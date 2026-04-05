
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from dagaar_fuel_station.dagaar_fuel_station.utils import (
    get_cash_customer,
    get_company_currency,
    get_currency_context,
    get_default_cash_mode_of_payment,
    get_exchange_rate_safe,
    get_item_rate,
    get_last_nozzle_closing,
    get_pos_price_list,
    validate_company_for_pos_profile,
)


@frappe.whitelist()
def get_nozzle_defaults(nozzle=None, pos_profile=None, currency=None, company=None, posting_date=None):
    if not nozzle:
        return {}
    nozzle_doc = frappe.get_cached_doc("Fuel Nozzle", nozzle)
    rate = get_item_rate(nozzle_doc.item, get_pos_price_list(pos_profile), nozzle_doc.uom, company=company, posting_date=posting_date, target_currency=currency)
    home_currency = get_company_currency(company)
    conversion_rate = get_exchange_rate_safe(currency or home_currency, home_currency, posting_date or nowdate())
    return {
        "opening_reading": get_last_nozzle_closing(nozzle),
        "rate": rate,
        "base_rate": flt(rate) * flt(conversion_rate),
        "item": nozzle_doc.item,
        "warehouse": nozzle_doc.warehouse,
        "uom": nozzle_doc.uom,
        "fuel_pump": nozzle_doc.fuel_pump,
        "display_name": nozzle_doc.nozzle_code or nozzle_doc.name,
    }


@frappe.whitelist()
def get_shift_closing_snapshots(shift_closing_entry):
    doc = frappe.get_doc("Shift Closing Entry", shift_closing_entry)
    return [
        {
            "source_shift_closing_line": d.name,
            "fuel_pump": d.fuel_pump,
            "fuel_nozzle": d.fuel_nozzle,
            "item": d.item,
            "warehouse": d.warehouse,
            "uom": d.uom,
            "opening_reading": d.opening_reading,
            "current_reading": d.closing_reading,
            "metered_qty": d.metered_qty,
            "test_qty": d.test_qty,
            "calibration_qty": d.calibration_qty,
            "adjustment_qty": d.adjustment_qty,
            "billable_qty": d.net_billable_qty,
            "rate": d.rate,
            "base_rate": flt(d.rate) * flt(doc.conversion_rate or 1),
            "amount": d.net_billable_amount,
            "amount_home": flt(d.net_billable_amount) * flt(doc.conversion_rate or 1),
            "pos_profile": doc.pos_profile,
        }
        for d in doc.lines
    ]


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_shift_closing_nozzle_query(doctype, txt, searchfield, start, page_len, filters):
    shift_closing_entry = (filters or {}).get("shift_closing_entry")
    if not shift_closing_entry:
        return []

    txt = f"%{txt or ''}%"
    return frappe.db.sql(
        """
        select distinct
            scl.fuel_nozzle as name,
            coalesce(scl.display_name, scl.fuel_nozzle) as display_name,
            scl.fuel_pump,
            scl.item
        from `tabShift Closing Line` scl
        where scl.parent = %(shift_closing_entry)s
          and scl.parenttype = 'Shift Closing Entry'
          and ifnull(scl.fuel_nozzle, '') != ''
          and (
                scl.fuel_nozzle like %(txt)s
                or coalesce(scl.display_name, '') like %(txt)s
                or coalesce(scl.fuel_pump, '') like %(txt)s
                or coalesce(scl.item, '') like %(txt)s
          )
        order by scl.idx asc
        limit %(start)s, %(page_len)s
        """,
        {
            "shift_closing_entry": shift_closing_entry,
            "txt": txt,
            "start": start,
            "page_len": page_len,
        },
    )


class PumpReadingEntry(Document):
    def before_validate(self):
        self.sync_header_from_shift_closing()
        self.set_currency_context()
        self.load_meter_snapshots(force=False)
        self.prepare_credit_allocation_rows()
        self.calculate_cash_summaries()
        self.calculate_totals()
        self.set_status()

    def validate(self):
        if not self.shift_closing_entry:
            frappe.throw(_("Shift Closing Entry is required."))
        validate_company_for_pos_profile(self.company, self.pos_profile)
        self.validate_shift_closing_match()
        self.validate_credit_allocations()
        self.validate_totals_against_snapshot()
        if self.invoices_created or any(d.sales_invoice for d in self.invoice_references):
            frappe.throw(_("Invoices already created for this Pump Reading Entry."))

    def on_submit(self):
        self.create_sales_invoices()
        self.db_set("invoices_created", 1, update_modified=False)
        self.db_set("status", "Invoiced", update_modified=False)
        frappe.db.set_value(
            "Shift Closing Entry",
            self.shift_closing_entry,
            {"status": "Closed", "pump_reading_entry": self.name},
            update_modified=False,
        )

    def on_cancel(self):
        submitted = []
        for row in self.invoice_references:
            if row.sales_invoice and frappe.db.get_value("Sales Invoice", row.sales_invoice, "docstatus") == 1:
                submitted.append(row.sales_invoice)
        if submitted:
            frappe.throw(_("Cancel linked Sales Invoices first: {0}").format(", ".join(submitted)))
        if self.shift_closing_entry and frappe.db.get_value("Shift Closing Entry", self.shift_closing_entry, "pump_reading_entry") == self.name:
            frappe.db.set_value(
                "Shift Closing Entry",
                self.shift_closing_entry,
                {"status": "Open", "pump_reading_entry": ""},
                update_modified=False,
            )

    def set_currency_context(self):
        ctx = get_currency_context(self.company, self.currency, self.date)
        self.home_currency = ctx.get("home_currency")
        self.currency = ctx.get("currency")
        self.conversion_rate = flt(ctx.get("conversion_rate")) or 1

    def sync_header_from_shift_closing(self):
        if not self.shift_closing_entry:
            return
        closing = frappe.get_doc("Shift Closing Entry", self.shift_closing_entry)
        self.date = self.date or closing.date or nowdate()
        self.posting_time = self.posting_time or closing.posting_time
        self.shift = self.shift or closing.shift
        self.company = self.company or closing.company
        self.pos_profile = self.pos_profile or closing.pos_profile
        self.attendant = self.attendant or closing.attendant
        self.currency = self.currency or closing.currency
        self.home_currency = self.home_currency or closing.home_currency
        self.conversion_rate = self.conversion_rate or closing.conversion_rate

    def get_snapshot_by_source(self, source_shift_closing_line):
        return next((d for d in self.meter_snapshots if d.source_shift_closing_line == source_shift_closing_line), None)

    def get_snapshot_by_nozzle(self, fuel_nozzle):
        return next((d for d in self.meter_snapshots if d.fuel_nozzle == fuel_nozzle), None)

    def resolve_credit_allocation_source(self, row):
        if row.source_shift_closing_line:
            snap = self.get_snapshot_by_source(row.source_shift_closing_line)
            if snap:
                return snap
        if row.fuel_nozzle:
            snap = self.get_snapshot_by_nozzle(row.fuel_nozzle)
            if snap:
                row.source_shift_closing_line = snap.source_shift_closing_line
                return snap
        return None

    def load_meter_snapshots(self, force=False):
        if not self.shift_closing_entry:
            return
        closing = frappe.get_doc("Shift Closing Entry", self.shift_closing_entry)
        existing = {d.source_shift_closing_line: d for d in self.meter_snapshots}
        if force:
            self.set("meter_snapshots", [])
            existing = {}
        fresh_rows = []
        for line in closing.lines:
            row = existing.get(line.name) if not force else None
            data = {
                "source_shift_closing_line": line.name,
                "fuel_pump": line.fuel_pump,
                "fuel_nozzle": line.fuel_nozzle,
                "item": line.item,
                "warehouse": line.warehouse,
                "uom": line.uom,
                "opening_reading": line.opening_reading,
                "current_reading": line.closing_reading,
                "metered_qty": line.metered_qty,
                "test_qty": line.test_qty,
                "calibration_qty": line.calibration_qty,
                "adjustment_qty": line.adjustment_qty,
                "billable_qty": line.net_billable_qty,
                "rate": line.rate,
                "base_rate": flt(line.rate) * flt(self.conversion_rate),
                "amount": line.net_billable_amount,
                "amount_home": flt(line.net_billable_amount) * flt(self.conversion_rate),
                "pos_profile": closing.pos_profile,
            }
            if row:
                for k, v in data.items():
                    row.set(k, v)
                fresh_rows.append(row)
            else:
                fresh_rows.append(frappe._dict(data))
        self.set("meter_snapshots", [])
        for row in fresh_rows:
            self.append("meter_snapshots", row)

    def prepare_credit_allocation_rows(self):
        cleaned = []
        for row in self.credit_allocations:
            snap = self.resolve_credit_allocation_source(row)
            if not snap:
                continue
            row.fuel_pump = snap.fuel_pump
            row.fuel_nozzle = snap.fuel_nozzle
            row.item = snap.item
            row.uom = snap.uom
            row.rate = snap.rate
            row.base_rate = snap.base_rate
            gross_amount = flt(row.qty) * flt(row.rate)
            row.discount_amount = flt(row.discount_amount)
            if row.discount_amount < 0:
                frappe.throw(_("Credit allocation discount cannot be negative for nozzle {0}.").format(row.fuel_nozzle))
            if row.discount_amount - gross_amount > 0.0001:
                frappe.throw(_("Credit allocation discount cannot exceed amount for nozzle {0}.").format(row.fuel_nozzle))
            row.amount = gross_amount - row.discount_amount
            row.amount_home = flt(row.amount) * flt(self.conversion_rate)
            cleaned.append(row)
        self.set("credit_allocations", [])
        for row in cleaned:
            self.append("credit_allocations", row)

    def validate_shift_closing_match(self):
        closing = frappe.get_doc("Shift Closing Entry", self.shift_closing_entry)
        if closing.docstatus != 1:
            frappe.throw(_("Shift Closing Entry must be submitted first."))
        if closing.status == "Closed" and (closing.pump_reading_entry or "") != (self.name or ""):
            frappe.throw(_("Shift Closing Entry {0} is already closed in Pump Reading Entry {1}.").format(closing.name, closing.pump_reading_entry))
        for label in ["company", "pos_profile", "shift", "attendant"]:
            if (self.get(label) or "") != (closing.get(label) or ""):
                frappe.throw(_("{0} does not match linked Shift Closing Entry.").format(label.replace("_", " ").title()))

    def validate_credit_allocations(self):
        if not self.meter_snapshots:
            frappe.throw(_("No meter snapshot rows were loaded from Shift Closing Entry."))
        snapshot_map = {d.source_shift_closing_line: d for d in self.meter_snapshots}
        allocated = {}
        for row in self.credit_allocations:
            snap = self.resolve_credit_allocation_source(row)
            if not snap:
                frappe.throw(_("Select a valid nozzle from the linked Shift Closing Entry in Credit Allocation."))
            if not row.customer:
                frappe.throw(_("Customer is required in Credit Allocation."))
            if flt(row.qty) <= 0:
                frappe.throw(_("Credit allocation qty must be greater than zero."))
            allocated.setdefault(row.source_shift_closing_line, 0)
            allocated[row.source_shift_closing_line] += flt(row.qty)
        for source, qty in allocated.items():
            billable = flt(snapshot_map[source].billable_qty)
            if qty - billable > 0.0001:
                label = snapshot_map[source].fuel_nozzle or source
                frappe.throw(_("Credit qty for source nozzle {0} cannot exceed billable qty {1}.").format(label, billable))

    def calculate_cash_summaries(self):
        self.set("cash_summaries", [])
        cash_customer = get_cash_customer()
        credit_map = {}
        for row in self.credit_allocations:
            credit_map.setdefault(row.source_shift_closing_line, 0)
            credit_map[row.source_shift_closing_line] += flt(row.qty)
        for snap in self.meter_snapshots:
            credit_qty = flt(credit_map.get(snap.source_shift_closing_line))
            billable_qty = flt(snap.billable_qty)
            cash_qty = billable_qty - credit_qty
            if cash_qty < -0.0001:
                frappe.throw(_("Cash qty became negative for nozzle {0}. Check allocations.").format(snap.fuel_nozzle))
            cash_qty = max(cash_qty, 0)
            adjustment_qty = flt(snap.adjustment_qty)
            self.append("cash_summaries", {
                "source_shift_closing_line": snap.source_shift_closing_line,
                "fuel_pump": snap.fuel_pump,
                "fuel_nozzle": snap.fuel_nozzle,
                "item": snap.item,
                "cash_customer": cash_customer,
                "billable_qty": billable_qty,
                "credit_qty": credit_qty,
                "cash_qty": cash_qty,
                "rate": snap.rate,
                "base_rate": snap.base_rate,
                "cash_amount": cash_qty * flt(snap.rate),
                "cash_amount_home": cash_qty * flt(snap.rate) * flt(self.conversion_rate),
                "adjustment_qty": adjustment_qty,
                "adjustment_amount": adjustment_qty * flt(snap.rate),
                "adjustment_amount_home": adjustment_qty * flt(snap.rate) * flt(self.conversion_rate),
                "net_balance_qty": cash_qty,
                "net_balance_amount": cash_qty * flt(snap.rate),
                "net_balance_amount_home": cash_qty * flt(snap.rate) * flt(self.conversion_rate),
            })

    def validate_totals_against_snapshot(self):
        total_snapshot = sum(flt(d.billable_qty) for d in self.meter_snapshots)
        total_credit = sum(flt(d.qty) for d in self.credit_allocations)
        total_cash = sum(flt(d.cash_qty) for d in self.cash_summaries)
        if abs(total_snapshot - (total_credit + total_cash)) > 0.0001:
            frappe.throw(_("Snapshot qty must equal Credit Qty + Cash Qty."))

    def calculate_totals(self):
        self.additional_discount_amount = flt(self.additional_discount_amount)
        self.total_metered_qty = sum(flt(d.metered_qty) for d in self.meter_snapshots)
        self.total_billable_qty = sum(flt(d.billable_qty) for d in self.meter_snapshots)
        self.total_credit_qty = sum(flt(d.qty) for d in self.credit_allocations)
        self.total_cash_qty = sum(flt(d.cash_qty) for d in self.cash_summaries)
        self.total_credit_amount = sum(flt(d.amount) for d in self.credit_allocations)
        self.total_cash_amount = sum(flt(d.cash_amount) for d in self.cash_summaries)
        if self.additional_discount_amount < 0:
            frappe.throw(_("Additional discount amount cannot be negative."))
        if self.additional_discount_amount - flt(self.total_cash_amount) > 0.0001:
            frappe.throw(_("Additional discount amount cannot exceed total cash amount."))
        self.total_amount = flt(self.total_credit_amount) + flt(self.total_cash_amount) - flt(self.additional_discount_amount)
        self.total_credit_amount_home = flt(self.total_credit_amount) * flt(self.conversion_rate)
        self.total_cash_amount_home = flt(self.total_cash_amount) * flt(self.conversion_rate)
        self.total_amount_home = flt(self.total_amount) * flt(self.conversion_rate)
        self.actual_cash_received_home = flt(self.actual_cash_received) * flt(self.conversion_rate)
        expected_cash = flt(self.total_cash_amount) - flt(self.additional_discount_amount)
        self.cash_over_short = flt(self.actual_cash_received) - expected_cash
        self.cash_over_short_home = flt(self.cash_over_short) * flt(self.conversion_rate)

    def set_status(self):
        if self.docstatus == 2:
            self.status = "Cancelled"
        elif self.docstatus == 1 and self.invoices_created:
            self.status = "Invoiced"
        elif self.docstatus == 1:
            self.status = "Submitted"
        else:
            self.status = "Draft"

    def create_sales_invoices(self):
        if self.invoice_references:
            frappe.throw(_("Invoices already created for this Pump Reading Entry."))
        created = []
        grouped = {}
        for row in self.credit_allocations:
            grouped.setdefault(row.customer, []).append(row)
        for customer, rows in grouped.items():
            inv = self._build_sales_invoice(customer, "Credit", rows)
            created.append((inv, "Credit", customer, rows))
        cash_rows = [d for d in self.cash_summaries if flt(d.cash_qty) > 0]
        if cash_rows:
            inv = self._build_sales_invoice(get_cash_customer(), "Cash", cash_rows)
            created.append((inv, "Cash", inv.customer, cash_rows))
        for inv, sale_type, customer, rows in created:
            if frappe.get_single("Fuel Station Settings").auto_submit_sales_invoices:
                inv.submit()
            for row in rows:
                self.append("invoice_references", {
                    "sale_type": sale_type,
                    "customer": customer,
                    "sales_invoice": inv.name,
                    "source_table": row.doctype,
                    "source_row": row.name,
                    "amount": inv.grand_total,
                    "outstanding_amount": inv.outstanding_amount,
                })
        self.save(ignore_permissions=True)

    def _build_sales_invoice(self, customer, sale_type, rows):
        inv = frappe.new_doc("Sales Invoice")
        discount_amount = 0
        inv.customer = customer
        inv.company = self.company
        inv.posting_date = self.date
        inv.due_date = self.date
        inv.set_posting_time = 1
        if self.posting_time:
            inv.posting_time = self.posting_time
        inv.currency = self.currency
        inv.conversion_rate = self.conversion_rate or 1
        inv.update_stock = frappe.get_single("Fuel Station Settings").default_update_stock or 0
        inv.pump_reading_entry = self.name
        inv.shift_closing_entry = self.shift_closing_entry
        inv.pos_profile_link = self.pos_profile
        inv.fuel_station_date = self.date
        inv.fuel_pump = ", ".join(sorted({(d.fuel_pump or "") for d in rows if d.fuel_pump}))
        inv.fuel_nozzle = ", ".join(sorted({(d.fuel_nozzle or "") for d in rows if d.fuel_nozzle}))

        for row in rows:
            is_credit = row.doctype == "Pump Reading Credit Allocation"
            if is_credit:
                discount_amount += flt(row.discount_amount)
            qty = flt(row.qty if is_credit else row.cash_qty)
            rate = flt(row.rate)
            snap = None
            if row.source_shift_closing_line:
                snap = next((d for d in self.meter_snapshots if d.source_shift_closing_line == row.source_shift_closing_line), None)
            item_row = {
                "item_code": row.item,
                "qty": qty,
                "uom": getattr(row, "uom", None) or (snap.uom if snap else None),
                "rate": rate,
                "warehouse": snap.warehouse if snap else None,
                "description": f"{sale_type} sale from nozzle {row.fuel_nozzle or ''}".strip(),
                "source_shift_closing_line": row.source_shift_closing_line,
                "opening_meter_reading": snap.opening_reading if snap else None,
                "closing_meter_reading": snap.current_reading if snap else None,
                "metered_qty": snap.metered_qty if snap else qty,
                "allocated_qty": qty,
                "fuel_pump": row.fuel_pump,
                "fuel_nozzle": row.fuel_nozzle,
            }
            inv.append("items", item_row)

        if sale_type == "Cash":
            discount_amount = flt(self.additional_discount_amount)
        if discount_amount:
            inv.apply_discount_on = "Grand Total"
            inv.discount_amount = flt(discount_amount)
            inv.base_discount_amount = flt(discount_amount) * flt(inv.conversion_rate or self.conversion_rate or 1)

        inv.flags.ignore_permissions = True
        inv.insert()

        if sale_type == "Cash":
            mode = get_default_cash_mode_of_payment(self.pos_profile)
            if mode:
                inv.append("payments", {"mode_of_payment": mode, "amount": inv.rounded_total or inv.grand_total})
                inv.is_pos = 1
                inv.paid_amount = inv.rounded_total or inv.grand_total
                inv.outstanding_amount = 0
                inv.save(ignore_permissions=True)
        return inv
