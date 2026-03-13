import frappe

def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label":"Date","fieldname":"date","fieldtype":"Date","width":95},
        {"label":"Shift","fieldname":"shift","fieldtype":"Data","width":90},
        {"label":"Station","fieldname":"pos_profile","fieldtype":"Link","options":"POS Profile","width":140},
        {"label":"Attendant","fieldname":"attendant","fieldtype":"Link","options":"Employee","width":140},
        {"label":"Nozzle","fieldname":"fuel_nozzle","fieldtype":"Link","options":"Fuel Nozzle","width":120},
        {"label":"Item","fieldname":"item","fieldtype":"Link","options":"Item","width":120},
        {"label":"Metered Qty","fieldname":"metered_qty","fieldtype":"Float","width":110},
        {"label":"Net Billable Qty","fieldname":"net_billable_qty","fieldtype":"Float","width":120},
        {"label":"Rate","fieldname":"rate","fieldtype":"Currency","width":100},
        {"label":"Net Billable Amount","fieldname":"net_billable_amount","fieldtype":"Currency","width":140},
    ]
    conditions = ["sce.docstatus = 1"]
    values = {}
    if filters.get('from_date'):
        conditions.append('sce.date >= %(from_date)s')
        values['from_date'] = filters.get('from_date')
    if filters.get('to_date'):
        conditions.append('sce.date <= %(to_date)s')
        values['to_date'] = filters.get('to_date')
    if filters.get('company'):
        conditions.append('sce.company = %(company)s')
        values['company'] = filters.get('company')
    if filters.get('pos_profile'):
        conditions.append('sce.pos_profile = %(pos_profile)s')
        values['pos_profile'] = filters.get('pos_profile')
    if filters.get('fuel_nozzle'):
        conditions.append('scl.fuel_nozzle = %(fuel_nozzle)s')
        values['fuel_nozzle'] = filters.get('fuel_nozzle')
    data = frappe.db.sql(f"""
        select sce.date, sce.shift, sce.pos_profile, sce.attendant,
               scl.fuel_nozzle, scl.item, scl.metered_qty, scl.net_billable_qty,
               scl.rate, scl.net_billable_amount
        from `tabShift Closing Line` scl
        inner join `tabShift Closing Entry` sce on sce.name = scl.parent
        where {' and '.join(conditions)}
        order by sce.date desc, sce.posting_time desc, scl.idx asc
    """, values, as_dict=True)
    return columns, data
