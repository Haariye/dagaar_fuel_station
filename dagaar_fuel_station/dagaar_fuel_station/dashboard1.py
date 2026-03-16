import frappe
from frappe.utils import today, add_days
from frappe.utils.data import flt


def _company_condition(company):
    return (" and company = %(company)s", {"company": company}) if company else ("", {})


@frappe.whitelist()
def get_dashboard_data(company=None, date=None):
    date = date or today()
    filters = {"date": date}
    company_sql, company_params = _company_condition(company)
    filters.update(company_params)

    shift_count = frappe.db.sql(
        f"select count(*) from `tabShift Closing Entry` where docstatus=1 and date=%(date)s {company_sql}",
        filters,
    )[0][0]

    billed = frappe.db.sql(
        f"select ifnull(sum(total_amount),0) from `tabPump Reading Entry` where docstatus=1 and date=%(date)s {company_sql}",
        filters,
    )[0][0]

    unpaid_credit = frappe.db.sql(
        f"""
        select ifnull(sum(outstanding_amount),0)
        from `tabSales Invoice`
        where docstatus=1 and outstanding_amount > 0 and fuel_station_date=%(date)s {company_sql}
        """,
        filters,
    )[0][0]

    top_nozzles = frappe.db.sql(
        f"""
        select scl.fuel_nozzle, ifnull(sum(scl.net_billable_qty),0) as liters
        from `tabShift Closing Line` scl
        inner join `tabShift Closing Entry` sce on sce.name = scl.parent
        where sce.docstatus=1 and sce.date=%(date)s {company_sql.replace('company', 'sce.company')}
        group by scl.fuel_nozzle
        order by liters desc
        limit 5
        """,
        filters,
        as_dict=True,
    )

    daily = frappe.db.sql(
        f"""
        select date, ifnull(sum(total_amount),0) as amount, ifnull(sum(total_billable_qty),0) as qty
        from `tabPump Reading Entry`
        where docstatus=1 and date between %(from_date)s and %(date)s {company_sql}
        group by date
        order by date asc
        """,
        {**filters, "from_date": add_days(date, -6)},
        as_dict=True,
    )

    return {
        "date": date,
        "shift_closing_count": shift_count,
        "billed_amount": flt(billed),
        "unpaid_credit": flt(unpaid_credit),
        "top_nozzles": top_nozzles,
        "daily": daily,
    }
