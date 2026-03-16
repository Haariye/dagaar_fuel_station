import frappe
from frappe.utils import add_days, flt, getdate, today


def _date_range(from_date=None, to_date=None):
    to_date = getdate(to_date or today())
    from_date = getdate(from_date or add_days(to_date, -6))
    if from_date > to_date:
        from_date, to_date = to_date, from_date
    return from_date, to_date


def _conditions(company=None, pos_profile=None, from_date=None, to_date=None, alias="pre"):
    conditions = [f"{alias}.docstatus = 1"]
    values = {"from_date": from_date, "to_date": to_date}
    if alias == "pre":
        conditions.append(f"{alias}.date between %(from_date)s and %(to_date)s")
    else:
        conditions.append(f"{alias}.date between %(from_date)s and %(to_date)s")
    if company:
        conditions.append(f"{alias}.company = %(company)s")
        values["company"] = company
    if pos_profile:
        conditions.append(f"{alias}.pos_profile = %(pos_profile)s")
        values["pos_profile"] = pos_profile
    return conditions, values


@frappe.whitelist()
def get_dashboard_data(company=None, pos_profile=None, from_date=None, to_date=None):
    from_date, to_date = _date_range(from_date, to_date)
    pre_conditions, values = _conditions(company, pos_profile, from_date, to_date, alias="pre")
    where_pre = " and ".join(pre_conditions)

    summary = frappe.db.sql(
        f"""
        select
            count(distinct pre.name) as pump_entries,
            ifnull(sum(pre.total_metered_qty), 0) as total_metered_qty,
            ifnull(sum(pre.total_billable_qty), 0) as total_billable_qty,
            ifnull(sum(pre.total_credit_qty), 0) as total_credit_qty,
            ifnull(sum(pre.total_cash_qty), 0) as total_cash_qty,
            ifnull(sum(pre.total_credit_amount), 0) as total_credit_amount,
            ifnull(sum(pre.total_cash_amount), 0) as total_cash_amount,
            ifnull(sum(pre.total_amount), 0) as total_amount,
            ifnull(sum(pre.cash_over_short), 0) as cash_over_short
        from `tabPump Reading Entry` pre
        where {where_pre}
        """,
        values,
        as_dict=True,
    )[0]

    sce_conditions, sce_values = _conditions(company, pos_profile, from_date, to_date, alias="sce")
    where_sce = " and ".join(sce_conditions)
    shift_stats = frappe.db.sql(
        f"""
        select
            count(distinct sce.name) as shift_closings,
            count(distinct sce.attendant) as attendants,
            count(distinct scl.fuel_nozzle) as active_nozzles
        from `tabShift Closing Entry` sce
        left join `tabShift Closing Line` scl on scl.parent = sce.name
        where {where_sce}
        """,
        sce_values,
        as_dict=True,
    )[0]

    daily_trend = frappe.db.sql(
        f"""
        select
            pre.date,
            ifnull(sum(pre.total_amount), 0) as amount,
            ifnull(sum(pre.total_billable_qty), 0) as billable_qty,
            ifnull(sum(pre.total_credit_amount), 0) as credit_amount,
            ifnull(sum(pre.total_cash_amount), 0) as cash_amount
        from `tabPump Reading Entry` pre
        where {where_pre}
        group by pre.date
        order by pre.date asc
        """,
        values,
        as_dict=True,
    )

    top_nozzles = frappe.db.sql(
        f"""
        select
            ms.fuel_nozzle,
            ifnull(sum(ms.billable_qty), 0) as liters,
            ifnull(sum(ms.amount), 0) as amount
        from `tabPump Reading Meter Snapshot` ms
        inner join `tabPump Reading Entry` pre on pre.name = ms.parent
        where {where_pre}
        group by ms.fuel_nozzle
        order by liters desc, amount desc
        limit 8
        """,
        values,
        as_dict=True,
    )

    top_customers = frappe.db.sql(
        f"""
        select
            ca.customer,
            ifnull(sum(ca.qty), 0) as liters,
            ifnull(sum(ca.amount), 0) as amount
        from `tabPump Reading Credit Allocation` ca
        inner join `tabPump Reading Entry` pre on pre.name = ca.parent
        where {where_pre}
        group by ca.customer
        order by amount desc, liters desc
        limit 8
        """,
        values,
        as_dict=True,
    )

    station_rows = frappe.db.sql(
        f"""
        select
            pre.pos_profile,
            ifnull(sum(pre.total_billable_qty), 0) as liters,
            ifnull(sum(pre.total_amount), 0) as amount,
            ifnull(sum(pre.total_credit_amount), 0) as credit_amount,
            ifnull(sum(pre.total_cash_amount), 0) as cash_amount
        from `tabPump Reading Entry` pre
        where {where_pre}
        group by pre.pos_profile
        order by amount desc
        limit 10
        """,
        values,
        as_dict=True,
    )

    shift_rows = frappe.db.sql(
        f"""
        select
            pre.shift,
            count(*) as entries,
            ifnull(sum(pre.total_billable_qty), 0) as liters,
            ifnull(sum(pre.total_amount), 0) as amount
        from `tabPump Reading Entry` pre
        where {where_pre}
        group by pre.shift
        order by amount desc
        """,
        values,
        as_dict=True,
    )

    return {
        "filters": {
            "from_date": str(from_date),
            "to_date": str(to_date),
            "company": company,
            "pos_profile": pos_profile,
        },
        "summary": {k: flt(v) if k not in {"pump_entries"} else int(v or 0) for k, v in summary.items()},
        "shift_stats": {k: int(v or 0) for k, v in shift_stats.items()},
        "daily_trend": daily_trend,
        "top_nozzles": top_nozzles,
        "top_customers": top_customers,
        "station_rows": station_rows,
        "shift_rows": shift_rows,
    }
