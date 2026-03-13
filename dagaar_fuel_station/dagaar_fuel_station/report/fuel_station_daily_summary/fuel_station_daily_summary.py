import frappe


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label":"Date","fieldname":"date","fieldtype":"Date","width":100},
        {"label":"Station","fieldname":"pos_profile","fieldtype":"Link","options":"POS Profile","width":140},
        {"label":"Shift","fieldname":"shift","fieldtype":"Data","width":90},
        {"label":"Metered Qty","fieldname":"metered_qty","fieldtype":"Float","width":110},
        {"label":"Billable Qty","fieldname":"billable_qty","fieldtype":"Float","width":110},
        {"label":"Credit Qty","fieldname":"credit_qty","fieldtype":"Float","width":110},
        {"label":"Cash Qty","fieldname":"cash_qty","fieldtype":"Float","width":110},
        {"label":"Credit Amount","fieldname":"credit_amount","fieldtype":"Currency","width":120},
        {"label":"Cash Amount","fieldname":"cash_amount","fieldtype":"Currency","width":120},
        {"label":"Total Amount","fieldname":"total_amount","fieldtype":"Currency","width":120},
        {"label":"Cash Over Short","fieldname":"cash_over_short","fieldtype":"Currency","width":120},
    ]
    conditions = ["docstatus = 1"]
    values = {}
    if filters.get('from_date'):
        conditions.append('date >= %(from_date)s')
        values['from_date'] = filters.get('from_date')
    if filters.get('to_date'):
        conditions.append('date <= %(to_date)s')
        values['to_date'] = filters.get('to_date')
    data = frappe.db.sql(f"""
        select date, pos_profile, shift, total_metered_qty as metered_qty, total_billable_qty as billable_qty,
               total_credit_qty as credit_qty, total_cash_qty as cash_qty,
               total_credit_amount as credit_amount, total_cash_amount as cash_amount,
               total_amount, cash_over_short
        from `tabPump Reading Entry`
        where {' and '.join(conditions)}
        order by date desc, modified desc
    """, values, as_dict=True)
    return columns, data
