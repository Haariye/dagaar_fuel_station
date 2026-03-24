
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FuelNozzle(Document):
    def validate(self):
        old_initial = None
        old_locked = 0
        if not self.is_new():
            old_initial, old_locked = frappe.db.get_value(
                "Fuel Nozzle", self.name, ["initial_opening_reading", "opening_reading_locked"]
            ) or (0, 0)

        if self.opening_reading_locked and flt(self.initial_opening_reading) != flt(old_initial):
            frappe.throw(_("Initial Opening Reading is locked and cannot be changed."))

        if flt(self.initial_opening_reading) and not cint_like(self.opening_reading_locked):
            if "System Manager" not in frappe.get_roles():
                frappe.throw(_("Only System Manager can set the first opening reading."))
            self.opening_reading_locked = 1

        if flt(old_initial) and flt(self.initial_opening_reading) != flt(old_initial):
            frappe.throw(_("Initial Opening Reading can only be set one time."))


def cint_like(v):
    try:
        return int(v or 0)
    except Exception:
        return 0
