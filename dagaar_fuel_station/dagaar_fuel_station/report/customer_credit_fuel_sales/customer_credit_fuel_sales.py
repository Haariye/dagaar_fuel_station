import frappe

def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label":"Date","fieldname":"posting_date","fieldtype":"Date","width":95},
        {"label":"Customer","fieldname":"customer","fieldtype":"Link","options":"Customer","width":170},
        {"label":"Invoice","fieldname":"name","fieldtype":"Link","options":"Sales Invoice","width":150},
        {"label":"Station","fieldname":"pos_profile_link","fieldtype":"Link","options":"POS Profile","width":130},
        {"label":"Pump","fieldname":"fuel_pump","fieldtype":"Data","width":100},
        {"label":"Nozzle","fieldname":"fuel_nozzle","fieldtype":"Data","width":100},
        {"label":"Grand Total","fieldname":"grand_total","fieldtype":"Currency","width":120},
        {"label":"Outstanding","fieldname":"outstanding_amount","fieldtype":"Currency","width":120},
        {"label":"Status","fieldname":"status","fieldtype":"Data","width":110},
    ]
    conditions = ["docstatus = 1", "outstanding_amount > 0", "pump_reading_entry is not null"]
    values = {}
    if filters.get('from_date'):
        conditions.append('posting_date >= %(from_date)s')
        values['from_date'] = filters.get('from_date')
    if filters.get('to_date'):
        conditions.append('posting_date <= %(to_date)s')
        values['to_date'] = filters.get('to_date')
    if filters.get('company'):
        conditions.append('company = %(company)s')
        values['company'] = filters.get('company')
    if filters.get('customer'):
        conditions.append('customer = %(customer)s')
        values['customer'] = filters.get('customer')
    data = frappe.db.sql(f"""
        select posting_date, customer, name, pos_profile_link, fuel_pump, fuel_nozzle,
               grand_total, outstanding_amount, status
        from `tabSales Invoice`
        where {' and '.join(conditions)}
        order by posting_date desc, modified desc
    """, values, as_dict=True)
    return columns, data
