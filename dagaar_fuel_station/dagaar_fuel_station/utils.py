
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


def get_price_list_currency(price_list):
    if not price_list:
        return None
    return frappe.db.get_value("Price List", price_list, "currency")


def get_company_currency(company):
    return frappe.get_cached_value("Company", company, "default_currency") if company else None


def get_exchange_rate_safe(from_currency, to_currency, posting_date=None):
    from_currency = from_currency or to_currency
    to_currency = to_currency or from_currency
    if not from_currency or not to_currency or from_currency == to_currency:
        return 1.0
    posting_date = posting_date or nowdate()
    # ERPNext helper first
    try:
        from erpnext.setup.utils import get_exchange_rate  # type: ignore
        rate = get_exchange_rate(from_currency, to_currency, posting_date)
        if rate:
            return flt(rate)
    except Exception:
        pass
    # Currency Exchange fallback
    rows = frappe.db.sql(
        """
        select exchange_rate
        from `tabCurrency Exchange`
        where from_currency=%s and to_currency=%s
          and date <= %s
        order by date desc
        limit 1
        """,
        (from_currency, to_currency, posting_date),
        as_dict=True,
    )
    if rows:
        return flt(rows[0].exchange_rate)
    inverse = frappe.db.sql(
        """
        select exchange_rate
        from `tabCurrency Exchange`
        where from_currency=%s and to_currency=%s
          and date <= %s
        order by date desc
        limit 1
        """,
        (to_currency, from_currency, posting_date),
        as_dict=True,
    )
    if inverse and flt(inverse[0].exchange_rate):
        return 1 / flt(inverse[0].exchange_rate)
    return 1.0


def convert_amount(amount, from_currency, to_currency, posting_date=None):
    return flt(amount) * flt(get_exchange_rate_safe(from_currency, to_currency, posting_date))


def get_item_rate(item_code, price_list, uom=None, customer=None, company=None, posting_date=None, target_currency=None):
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
    rate = flt(rate)
    price_list_currency = get_price_list_currency(price_list)
    target_currency = target_currency or price_list_currency
    if price_list_currency and target_currency and price_list_currency != target_currency:
        rate = convert_amount(rate, price_list_currency, target_currency, posting_date)
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
    if rows:
        return flt(rows[0].closing_reading)
    initial = frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading")
    return flt(initial)


def validate_company_for_pos_profile(company, pos_profile):
    if not pos_profile or not company:
        return
    pos_company = frappe.db.get_value("POS Profile", pos_profile, "company")
    if pos_company and pos_company != company:
        frappe.throw(_("POS Profile {0} belongs to company {1}, not {2}.").format(pos_profile, pos_company, company))


@frappe.whitelist()
def get_currency_context(company=None, currency=None, posting_date=None):
    home_currency = get_company_currency(company) or currency
    currency = currency or home_currency
    return {
        "home_currency": home_currency,
        "currency": currency,
        "conversion_rate": flt(get_exchange_rate_safe(currency, home_currency, posting_date or nowdate())) if home_currency else 1,
    }
