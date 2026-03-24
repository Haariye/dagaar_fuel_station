import frappe
from frappe import _
from frappe.utils import flt, nowdate


def get_settings():
    return frappe.get_single("Fuel Station Settings")


def get_cash_customer():
    settings = get_settings()
    if not settings.cash_customer:
        frappe.throw(_("Set Default Cash Customer in Fuel Station Settings."))
    return settings.cash_customer


def get_default_cash_mode_of_payment(pos_profile=None):
    settings = get_settings()
    if settings.default_cash_mode_of_payment:
        return settings.default_cash_mode_of_payment
    if pos_profile and frappe.db.exists("POS Profile", pos_profile):
        payments = frappe.get_all(
            "POS Payment Method",
            filters={"parent": pos_profile, "parenttype": "POS Profile"},
            fields=["mode_of_payment", "default"],
        )
        if payments:
            defaults = [d for d in payments if d.get("default")]
            return (defaults[0] if defaults else payments[0]).get("mode_of_payment")
    return None


def get_pos_price_list(pos_profile):
    if not pos_profile:
        return None
    return frappe.db.get_value("POS Profile", pos_profile, "selling_price_list")


def get_item_rate(item_code, price_list, uom=None, customer=None, company=None, posting_date=None):
    if not item_code or not price_list:
        return 0
    posting_date = posting_date or nowdate()
    filters = {"item_code": item_code, "price_list": price_list, "selling": 1}
    if uom:
        filters["uom"] = uom
    rate = frappe.db.get_value("Item Price", filters, "price_list_rate")
    if rate is None and uom:
        filters.pop("uom", None)
        rate = frappe.db.get_value("Item Price", filters, "price_list_rate")
    return flt(rate)


def get_last_nozzle_closing(nozzle):
    if not nozzle:
        return 0
    rows = frappe.db.sql(
        """
        select scl.closing_reading
        from `tabShift Closing Line` scl
        inner join `tabShift Closing Entry` sce on sce.name = scl.parent
        where sce.docstatus = 1 and scl.fuel_nozzle = %s
        order by sce.date desc, sce.posting_time desc, sce.modified desc
        limit 1
        """,
        nozzle,
        as_dict=True,
    )
    return flt(rows[0].closing_reading) if rows else 0


def validate_company_for_pos_profile(company, pos_profile):
    if not pos_profile or not company:
        return
    pos_company = frappe.db.get_value("POS Profile", pos_profile, "company")
    if pos_company and pos_company != company:
        frappe.throw(_("POS Profile {0} belongs to company {1}, not {2}.").format(pos_profile, pos_company, company))
