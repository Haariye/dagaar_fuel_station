import frappe


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label":"Date","fieldname":"date","fieldtype":"Date","width":95},
        {"label":"Entry","fieldname":"pump_reading_entry","fieldtype":"Link","options":"Pump Reading Entry","width":160},
        {"label":"Station","fieldname":"pos_profile","fieldtype":"Link","options":"POS Profile","width":130},
        {"label":"Attendant","fieldname":"attendant","fieldtype":"Link","options":"Employee","width":140},
        {"label":"Nozzle","fieldname":"fuel_nozzle","fieldtype":"Link","options":"Fuel Nozzle","width":120},
        {"label":"Item","fieldname":"item","fieldtype":"Link","options":"Item","width":120},
        {"label":"Sale Type","fieldname":"sale_type","fieldtype":"Data","width":90},
        {"label":"Customer","fieldname":"customer","fieldtype":"Link","options":"Customer","width":170},
        {"label":"Qty","fieldname":"qty","fieldtype":"Float","width":110},
        {"label":"Amount","fieldname":"amount","fieldtype":"Currency","width":120},
        {"label":"Sales Invoice","fieldname":"sales_invoice","fieldtype":"Link","options":"Sales Invoice","width":150},
    ]
    conditions = ["pre.docstatus = 1"]
    values = {}
    if filters.get('from_date'):
        conditions.append('pre.date >= %(from_date)s')
        values['from_date'] = filters.get('from_date')
    if filters.get('to_date'):
        conditions.append('pre.date <= %(to_date)s')
        values['to_date'] = filters.get('to_date')
    if filters.get('company'):
        conditions.append('pre.company = %(company)s')
        values['company'] = filters.get('company')
    query = f"""
        select pre.date, pre.name as pump_reading_entry, pre.pos_profile, pre.attendant,
               ca.fuel_nozzle, ca.item, 'Credit' as sale_type, ca.customer, ca.qty,
               ca.amount, pir.sales_invoice
        from `tabPump Reading Credit Allocation` ca
        inner join `tabPump Reading Entry` pre on pre.name = ca.parent
        left join `tabPump Reading Invoice Reference` pir on pir.parent = pre.name and pir.source_row = ca.name
        where {' and '.join(conditions)}
        union all
        select pre.date, pre.name as pump_reading_entry, pre.pos_profile, pre.attendant,
               cs.fuel_nozzle, cs.item, 'Cash' as sale_type, cs.cash_customer as customer, cs.cash_qty as qty,
               cs.cash_amount as amount, pir.sales_invoice
        from `tabPump Reading Cash Summary` cs
        inner join `tabPump Reading Entry` pre on pre.name = cs.parent
        left join `tabPump Reading Invoice Reference` pir on pir.parent = pre.name and pir.source_row = cs.name
        where {' and '.join(conditions)} and cs.cash_qty > 0
        order by date desc
    """
    data = frappe.db.sql(query, values, as_dict=True)
    return columns, data
