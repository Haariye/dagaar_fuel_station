## .gitignore

```
*.pyc
__pycache__/
*.swp
*.log
node_modules/
```

## FULL_SOURCE_LISTING.md

```

```

## MANIFEST.in

```
include *.md
include *.txt
include *.json
recursive-include dagaar_fuel_station *.json *.js *.py *.css *.html *.csv *.txt
recursive-include dagaar_fuel_station/public *
recursive-include dagaar_fuel_station/fixtures *.json
```

## README.md

```
# Dagaar Fuel Station

Advanced ERPNext / Frappe fuel station app with nozzle-based shift closing, billing, dashboard, and reports.
```

## dagaar_fuel_station/INSTALL.md

```
# Install

```bash
cd /opt/frappe-bench
bench get-app /path/to/dagaar_fuel_station
bench --site yoursite.local install-app dagaar_fuel_station
bench --site yoursite.local migrate
bench --site yoursite.local clear-cache
bench restart
```
```

## dagaar_fuel_station/__init__.py

```
__version__ = "0.0.1"
```

## dagaar_fuel_station/config/__init__.py

```

```

## dagaar_fuel_station/config/desktop.py

```
from frappe import _

def get_data():
    return [{
        "module_name": "Dagaar Fuel Station",
        "category": "Modules",
        "label": _("Dagaar Fuel Station"),
        "color": "orange",
        "icon": "octicon octicon-dashboard",
        "type": "module",
        "description": "Advanced fuel station operations"
    }]
```

## dagaar_fuel_station/dagaar_fuel_station/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/dashboard.py

```
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
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_nozzle/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_nozzle/fuel_nozzle.json

```
{
  "doctype": "DocType",
  "name": "Fuel Nozzle",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "nozzle_code",
      "label": "Nozzle Code",
      "fieldtype": "Data",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_pump",
      "label": "Fuel Pump",
      "fieldtype": "Link",
      "options": "Fuel Pump",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "company",
      "label": "Company",
      "fieldtype": "Link",
      "options": "Company",
      "reqd": 1
    },
    {
      "fieldname": "pos_profile",
      "label": "POS Profile",
      "fieldtype": "Link",
      "options": "POS Profile",
      "reqd": 1
    },
    {
      "fieldname": "item",
      "label": "Fuel Item",
      "fieldtype": "Link",
      "options": "Item",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "uom",
      "label": "UOM",
      "fieldtype": "Link",
      "options": "UOM"
    },
    {
      "fieldname": "warehouse",
      "label": "Warehouse",
      "fieldtype": "Link",
      "options": "Warehouse"
    },
    {
      "fieldname": "cost_center",
      "label": "Cost Center",
      "fieldtype": "Link",
      "options": "Cost Center"
    },
    {
      "fieldname": "sequence_no",
      "label": "Sequence No",
      "fieldtype": "Int"
    },
    {
      "fieldname": "active",
      "label": "Active",
      "fieldtype": "Check",
      "default": "1",
      "in_list_view": 1
    },
    {
      "fieldname": "remarks",
      "label": "Remarks",
      "fieldtype": "Small Text"
    }
  ],
  "field_order": [
    "nozzle_code",
    "fuel_pump",
    "company",
    "pos_profile",
    "item",
    "uom",
    "warehouse",
    "cost_center",
    "sequence_no",
    "active",
    "remarks"
  ],
  "permissions": [
    {
      "role": "System Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "delete": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "export": 1,
      "print": 1
    },
    {
      "role": "Sales Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Sales User",
      "read": 1,
      "write": 1,
      "create": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Accounts User",
      "read": 1,
      "report": 1,
      "print": 1
    }
  ],
  "sort_field": "modified",
  "sort_order": "DESC",
  "istable": 0,
  "issingle": 0,
  "editable_grid": 1,
  "is_submittable": 0,
  "quick_entry": 0,
  "title_field": "nozzle_code",
  "search_fields": "nozzle_code,fuel_pump,item"
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_nozzle/fuel_nozzle.py

```
from frappe.model.document import Document

class FuelNozzle(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_pump/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_pump/fuel_pump.json

```
{
  "doctype": "DocType",
  "name": "Fuel Pump",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "pump_code",
      "label": "Pump Code",
      "fieldtype": "Data",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "pump_name",
      "label": "Pump Name",
      "fieldtype": "Data",
      "in_list_view": 1
    },
    {
      "fieldname": "company",
      "label": "Company",
      "fieldtype": "Link",
      "options": "Company",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "pos_profile",
      "label": "POS Profile",
      "fieldtype": "Link",
      "options": "POS Profile",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "warehouse",
      "label": "Default Warehouse",
      "fieldtype": "Link",
      "options": "Warehouse"
    },
    {
      "fieldname": "cost_center",
      "label": "Default Cost Center",
      "fieldtype": "Link",
      "options": "Cost Center"
    },
    {
      "fieldname": "active",
      "label": "Active",
      "fieldtype": "Check",
      "default": "1",
      "in_list_view": 1
    },
    {
      "fieldname": "remarks",
      "label": "Remarks",
      "fieldtype": "Small Text"
    }
  ],
  "field_order": [
    "pump_code",
    "pump_name",
    "company",
    "pos_profile",
    "warehouse",
    "cost_center",
    "active",
    "remarks"
  ],
  "permissions": [
    {
      "role": "System Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "delete": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "export": 1,
      "print": 1
    },
    {
      "role": "Sales Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Sales User",
      "read": 1,
      "write": 1,
      "create": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Accounts User",
      "read": 1,
      "report": 1,
      "print": 1
    }
  ],
  "sort_field": "modified",
  "sort_order": "DESC",
  "istable": 0,
  "issingle": 0,
  "editable_grid": 1,
  "is_submittable": 0,
  "quick_entry": 0,
  "title_field": "pump_code",
  "search_fields": "pump_code,pump_name"
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_pump/fuel_pump.py

```
from frappe.model.document import Document

class FuelPump(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_station_settings/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_station_settings/fuel_station_settings.json

```
{
  "doctype": "DocType",
  "name": "Fuel Station Settings",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "cash_customer",
      "label": "Default Cash Customer",
      "fieldtype": "Link",
      "options": "Customer",
      "reqd": 1
    },
    {
      "fieldname": "default_cash_mode_of_payment",
      "label": "Default Cash Mode of Payment",
      "fieldtype": "Link",
      "options": "Mode of Payment"
    },
    {
      "fieldname": "auto_submit_sales_invoices",
      "label": "Auto Submit Sales Invoices",
      "fieldtype": "Check",
      "default": "1"
    },
    {
      "fieldname": "default_update_stock",
      "label": "Update Stock on Sales Invoice",
      "fieldtype": "Check",
      "default": "1"
    },
    {
      "fieldname": "allow_cash_row_manual_customer",
      "label": "Allow Manual Customer on Cash Rows",
      "fieldtype": "Check"
    },
    {
      "fieldname": "default_shift_options",
      "label": "Shift Options",
      "fieldtype": "Small Text",
      "default": "Morning\nEvening\nNight"
    },
    {
      "fieldname": "dashboard_refresh_minutes",
      "label": "Dashboard Refresh Minutes",
      "fieldtype": "Int",
      "default": "5"
    }
  ],
  "field_order": [
    "cash_customer",
    "default_cash_mode_of_payment",
    "auto_submit_sales_invoices",
    "default_update_stock",
    "allow_cash_row_manual_customer",
    "default_shift_options",
    "dashboard_refresh_minutes"
  ],
  "permissions": [
    {
      "role": "System Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "delete": 1,
      "print": 1
    }
  ],
  "sort_field": "modified",
  "sort_order": "DESC",
  "istable": 0,
  "issingle": 1,
  "editable_grid": 0,
  "is_submittable": 0,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/fuel_station_settings/fuel_station_settings.py

```
from frappe.model.document import Document

class FuelStationSettings(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_cash_summary/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_cash_summary/pump_reading_cash_summary.json

```
{
  "doctype": "DocType",
  "name": "Pump Reading Cash Summary",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "source_shift_closing_line",
      "label": "Source Shift Closing Line",
      "fieldtype": "Data",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_pump",
      "label": "Fuel Pump",
      "fieldtype": "Link",
      "options": "Fuel Pump",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_nozzle",
      "label": "Fuel Nozzle",
      "fieldtype": "Link",
      "options": "Fuel Nozzle",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "item",
      "label": "Item",
      "fieldtype": "Link",
      "options": "Item",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "cash_customer",
      "label": "Cash Customer",
      "fieldtype": "Link",
      "options": "Customer",
      "read_only": 1
    },
    {
      "fieldname": "billable_qty",
      "label": "Billable Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "credit_qty",
      "label": "Credit Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "cash_qty",
      "label": "Cash Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "rate",
      "label": "Rate",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "cash_amount",
      "label": "Cash Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "adjustment_qty",
      "label": "Adjustment Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "adjustment_amount",
      "label": "Adjustment Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "net_balance_qty",
      "label": "Net Balance Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "net_balance_amount",
      "label": "Net Balance Amount",
      "fieldtype": "Currency",
      "read_only": 1
    }
  ],
  "field_order": [
    "source_shift_closing_line",
    "fuel_pump",
    "fuel_nozzle",
    "item",
    "cash_customer",
    "billable_qty",
    "credit_qty",
    "cash_qty",
    "rate",
    "cash_amount",
    "adjustment_qty",
    "adjustment_amount",
    "net_balance_qty",
    "net_balance_amount"
  ],
  "istable": 1,
  "issingle": 0,
  "editable_grid": 1,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_cash_summary/pump_reading_cash_summary.py

```
from frappe.model.document import Document


class PumpReadingCashSummary(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_credit_allocation/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_credit_allocation/pump_reading_credit_allocation.json

```
{
  "doctype": "DocType",
  "name": "Pump Reading Credit Allocation",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "source_shift_closing_line",
      "label": "Source Shift Closing Line",
      "fieldtype": "Data",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_pump",
      "label": "Fuel Pump",
      "fieldtype": "Link",
      "options": "Fuel Pump",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_nozzle",
      "label": "Fuel Nozzle",
      "fieldtype": "Link",
      "options": "Fuel Nozzle",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "item",
      "label": "Item",
      "fieldtype": "Link",
      "options": "Item",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "customer",
      "label": "Customer",
      "fieldtype": "Link",
      "options": "Customer",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "qty",
      "label": "Qty / Litres",
      "fieldtype": "Float",
      "precision": "3",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "uom",
      "label": "UOM",
      "fieldtype": "Link",
      "options": "UOM",
      "read_only": 1
    },
    {
      "fieldname": "rate",
      "label": "Rate",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "amount",
      "label": "Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "notes",
      "label": "Notes",
      "fieldtype": "Small Text"
    }
  ],
  "field_order": [
    "source_shift_closing_line",
    "fuel_pump",
    "fuel_nozzle",
    "item",
    "customer",
    "qty",
    "uom",
    "rate",
    "amount",
    "notes"
  ],
  "istable": 1,
  "issingle": 0,
  "editable_grid": 1,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_credit_allocation/pump_reading_credit_allocation.py

```
from frappe.model.document import Document


class PumpReadingCreditAllocation(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_entry/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_entry/pump_reading_entry.js

```
function recompute_cash_summary(frm) {
    const snapshots = frm.doc.meter_snapshots || [];
    const credits = frm.doc.credit_allocations || [];
    const creditMap = {};
    snapshots.forEach(s => creditMap[s.source_shift_closing_line] = 0);
    credits.forEach(r => {
        creditMap[r.source_shift_closing_line] = (creditMap[r.source_shift_closing_line] || 0) + flt(r.qty);
    });
    frm.clear_table('cash_summaries');
    snapshots.forEach(s => {
        const credit_qty = flt(creditMap[s.source_shift_closing_line]);
        const cash_qty = Math.max(flt(s.billable_qty) - credit_qty, 0);
        const row = frm.add_child('cash_summaries');
        row.source_shift_closing_line = s.source_shift_closing_line;
        row.fuel_pump = s.fuel_pump;
        row.fuel_nozzle = s.fuel_nozzle;
        row.item = s.item;
        row.billable_qty = s.billable_qty;
        row.credit_qty = credit_qty;
        row.cash_qty = cash_qty;
        row.rate = s.rate;
        row.cash_amount = cash_qty * flt(s.rate);
        row.adjustment_qty = s.adjustment_qty;
        row.adjustment_amount = flt(s.adjustment_qty) * flt(s.rate);
        row.net_balance_qty = cash_qty;
        row.net_balance_amount = cash_qty * flt(s.rate);
    });
    frm.refresh_field('cash_summaries');
    frm.trigger('recompute_totals');
}

function sync_credit_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const source = (frm.doc.meter_snapshots || []).find(d => d.source_shift_closing_line === row.source_shift_closing_line);
    if (source) {
        row.fuel_pump = source.fuel_pump;
        row.fuel_nozzle = source.fuel_nozzle;
        row.item = source.item;
        row.uom = source.uom;
        row.rate = source.rate;
        row.amount = flt(row.qty) * flt(row.rate);
        frm.refresh_field('credit_allocations');
    }
    recompute_cash_summary(frm);
}

frappe.ui.form.on('Pump Reading Entry', {
    refresh(frm) {
        frm.add_custom_button(__('Fetch Shift Closing'), () => {
            if (!frm.doc.shift_closing_entry) {
                frappe.msgprint(__('Select Shift Closing Entry first.'));
                return;
            }
            frappe.call({
                method: 'dagaar_fuel_station.dagaar_fuel_station.doctype.pump_reading_entry.pump_reading_entry.get_shift_closing_snapshots',
                args: { shift_closing_entry: frm.doc.shift_closing_entry },
                callback: function(r) {
                    frm.clear_table('meter_snapshots');
                    (r.message || []).forEach(d => {
                        const row = frm.add_child('meter_snapshots');
                        Object.assign(row, d);
                    });
                    frm.refresh_field('meter_snapshots');
                    recompute_cash_summary(frm);
                }
            });
        });
        if (frm.doc.docstatus === 1 && frm.doc.invoice_references && frm.doc.invoice_references.length) {
            frm.add_custom_button(__('View Invoices'), () => {
                frappe.set_route('List', 'Sales Invoice', { pump_reading_entry: frm.doc.name });
            });
        }
    },
    shift_closing_entry(frm) {
        if (!frm.doc.shift_closing_entry) return;
        frappe.db.get_doc('Shift Closing Entry', frm.doc.shift_closing_entry).then(doc => {
            frm.set_value('date', doc.date);
            frm.set_value('posting_time', doc.posting_time);
            frm.set_value('shift', doc.shift);
            frm.set_value('company', doc.company);
            frm.set_value('pos_profile', doc.pos_profile);
            frm.set_value('attendant', doc.attendant);
            frm.set_value('currency', doc.currency);
        });
    },
    recompute_totals(frm) {
        let total_metered_qty = 0, total_billable_qty = 0, total_credit_qty = 0, total_cash_qty = 0, total_credit_amount = 0, total_cash_amount = 0;
        (frm.doc.meter_snapshots || []).forEach(d => {
            total_metered_qty += flt(d.metered_qty);
            total_billable_qty += flt(d.billable_qty);
        });
        (frm.doc.credit_allocations || []).forEach(d => {
            total_credit_qty += flt(d.qty);
            total_credit_amount += flt(d.amount);
        });
        (frm.doc.cash_summaries || []).forEach(d => {
            total_cash_qty += flt(d.cash_qty);
            total_cash_amount += flt(d.cash_amount);
        });
        frm.set_value('total_metered_qty', total_metered_qty);
        frm.set_value('total_billable_qty', total_billable_qty);
        frm.set_value('total_credit_qty', total_credit_qty);
        frm.set_value('total_cash_qty', total_cash_qty);
        frm.set_value('total_credit_amount', total_credit_amount);
        frm.set_value('total_cash_amount', total_cash_amount);
        frm.set_value('total_amount', total_credit_amount + total_cash_amount);
        frm.set_value('cash_over_short', flt(frm.doc.actual_cash_received) - total_cash_amount);
    },
    actual_cash_received(frm) {
        frm.trigger('recompute_totals');
    }
});

frappe.ui.form.on('Pump Reading Credit Allocation', {
    source_shift_closing_line(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); },
    qty(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); },
    customer(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); }
});
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_entry/pump_reading_entry.json

```
{
  "doctype": "DocType",
  "name": "Pump Reading Entry",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "is_submittable": 1,
  "fields": [
    {
      "fieldname": "naming_series",
      "label": "Naming Series",
      "fieldtype": "Select",
      "options": "PRE-.YYYY.-",
      "default": "PRE-.YYYY.-",
      "reqd": 1
    },
    {
      "fieldname": "date",
      "label": "Date",
      "fieldtype": "Date",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "posting_time",
      "label": "Posting Time",
      "fieldtype": "Time"
    },
    {
      "fieldname": "shift",
      "label": "Shift",
      "fieldtype": "Select",
      "options": "Morning\nEvening\nNight",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "company",
      "label": "Company",
      "fieldtype": "Link",
      "options": "Company",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "pos_profile",
      "label": "Station / POS Profile",
      "fieldtype": "Link",
      "options": "POS Profile",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "attendant",
      "label": "Attendant",
      "fieldtype": "Link",
      "options": "Employee",
      "reqd": 1
    },
    {
      "fieldname": "currency",
      "label": "Currency",
      "fieldtype": "Link",
      "options": "Currency"
    },
    {
      "fieldname": "shift_closing_entry",
      "label": "Shift Closing Entry",
      "fieldtype": "Link",
      "options": "Shift Closing Entry",
      "reqd": 1
    },
    {
      "fieldname": "status",
      "label": "Status",
      "fieldtype": "Data",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "invoices_created",
      "label": "Invoices Created",
      "fieldtype": "Check",
      "read_only": 1
    },
    {
      "fieldname": "section_totals",
      "label": "Totals",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "total_metered_qty",
      "label": "Total Metered Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "total_billable_qty",
      "label": "Total Billable Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "total_credit_qty",
      "label": "Total Credit Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "total_cash_qty",
      "label": "Total Cash Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "total_credit_amount",
      "label": "Total Credit Amount",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "total_cash_amount",
      "label": "Total Cash Amount",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "total_amount",
      "label": "Total Amount",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "actual_cash_received",
      "label": "Actual Cash Received",
      "fieldtype": "Currency",
      "options": "currency"
    },
    {
      "fieldname": "cash_over_short",
      "label": "Cash Over / Short",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "remarks",
      "label": "Remarks",
      "fieldtype": "Small Text"
    },
    {
      "fieldname": "section_meter",
      "label": "Meter Snapshot",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "meter_snapshots",
      "label": "Meter Snapshot",
      "fieldtype": "Table",
      "options": "Pump Reading Meter Snapshot",
      "read_only": 1
    },
    {
      "fieldname": "section_credit",
      "label": "Credit Allocation",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "credit_allocations",
      "label": "Credit Allocation",
      "fieldtype": "Table",
      "options": "Pump Reading Credit Allocation"
    },
    {
      "fieldname": "section_cash",
      "label": "Cash / Adjustment Summary",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "cash_summaries",
      "label": "Cash / Adjustment Summary",
      "fieldtype": "Table",
      "options": "Pump Reading Cash Summary",
      "read_only": 1
    },
    {
      "fieldname": "section_invoices",
      "label": "Invoice References",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "invoice_references",
      "label": "Invoice References",
      "fieldtype": "Table",
      "options": "Pump Reading Invoice Reference",
      "read_only": 1
    }
  ],
  "field_order": [
    "naming_series",
    "date",
    "posting_time",
    "shift",
    "company",
    "pos_profile",
    "attendant",
    "currency",
    "shift_closing_entry",
    "status",
    "invoices_created",
    "section_totals",
    "total_metered_qty",
    "total_billable_qty",
    "total_credit_qty",
    "total_cash_qty",
    "total_credit_amount",
    "total_cash_amount",
    "total_amount",
    "actual_cash_received",
    "cash_over_short",
    "remarks",
    "section_meter",
    "meter_snapshots",
    "section_credit",
    "credit_allocations",
    "section_cash",
    "cash_summaries",
    "section_invoices",
    "invoice_references"
  ],
  "permissions": [
    {
      "role": "System Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "delete": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "export": 1,
      "print": 1
    },
    {
      "role": "Sales Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Sales User",
      "read": 1,
      "write": 1,
      "create": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Accounts User",
      "read": 1,
      "write": 1,
      "report": 1,
      "print": 1
    }
  ],
  "autoname": "field:naming_series",
  "search_fields": "date,shift,pos_profile,attendant,shift_closing_entry",
  "title_field": "shift_closing_entry"
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_entry/pump_reading_entry.py

```
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from dagaar_fuel_station.dagaar_fuel_station.utils import (
    get_cash_customer,
    get_default_cash_mode_of_payment,
    get_item_rate,
    get_pos_price_list,
    validate_company_for_pos_profile,
)


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
            "amount": d.net_billable_amount,
            "pos_profile": doc.pos_profile,
        }
        for d in doc.lines
    ]


class PumpReadingEntry(Document):
    def before_validate(self):
        self.sync_header_from_shift_closing()
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

    def on_cancel(self):
        submitted = []
        for row in self.invoice_references:
            if row.sales_invoice and frappe.db.get_value("Sales Invoice", row.sales_invoice, "docstatus") == 1:
                submitted.append(row.sales_invoice)
        if submitted:
            frappe.throw(_("Cancel linked Sales Invoices first: {0}").format(", ".join(submitted)))

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
                "amount": line.net_billable_amount,
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
        source_map = {d.source_shift_closing_line: d for d in self.meter_snapshots}
        valid_sources = set(source_map.keys())
        cleaned = []
        for row in self.credit_allocations:
            if row.source_shift_closing_line in valid_sources:
                snap = source_map[row.source_shift_closing_line]
                row.fuel_pump = snap.fuel_pump
                row.fuel_nozzle = snap.fuel_nozzle
                row.item = snap.item
                row.uom = snap.uom
                row.rate = snap.rate
                row.amount = flt(row.qty) * flt(row.rate)
                cleaned.append(row)
        self.set("credit_allocations", [])
        for row in cleaned:
            self.append("credit_allocations", row)

    def validate_shift_closing_match(self):
        closing = frappe.get_doc("Shift Closing Entry", self.shift_closing_entry)
        if closing.docstatus != 1:
            frappe.throw(_("Shift Closing Entry must be submitted first."))
        for label in ["company", "pos_profile", "shift", "attendant"]:
            if (self.get(label) or "") != (closing.get(label) or ""):
                frappe.throw(_("{0} does not match linked Shift Closing Entry.").format(label.replace("_", " ").title()))

    def validate_credit_allocations(self):
        if not self.meter_snapshots:
            frappe.throw(_("No meter snapshot rows were loaded from Shift Closing Entry."))
        snapshot_map = {d.source_shift_closing_line: d for d in self.meter_snapshots}
        allocated = {}
        for row in self.credit_allocations:
            if not row.source_shift_closing_line:
                frappe.throw(_("Credit Allocation row is missing source shift closing line."))
            if row.source_shift_closing_line not in snapshot_map:
                frappe.throw(_("Invalid source shift closing line in Credit Allocation: {0}").format(row.source_shift_closing_line))
            if not row.customer:
                frappe.throw(_("Customer is required in Credit Allocation."))
            if flt(row.qty) <= 0:
                frappe.throw(_("Credit allocation qty must be greater than zero."))
            allocated.setdefault(row.source_shift_closing_line, 0)
            allocated[row.source_shift_closing_line] += flt(row.qty)
        for source, qty in allocated.items():
            billable = flt(snapshot_map[source].billable_qty)
            if qty - billable > 0.0001:
                frappe.throw(_("Credit qty for source line {0} cannot exceed billable qty {1}.").format(source, billable))

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
                "cash_amount": cash_qty * flt(snap.rate),
                "adjustment_qty": adjustment_qty,
                "adjustment_amount": adjustment_qty * flt(snap.rate),
                "net_balance_qty": cash_qty,
                "net_balance_amount": cash_qty * flt(snap.rate),
            })

    def validate_totals_against_snapshot(self):
        total_snapshot = sum(flt(d.billable_qty) for d in self.meter_snapshots)
        total_credit = sum(flt(d.qty) for d in self.credit_allocations)
        total_cash = sum(flt(d.cash_qty) for d in self.cash_summaries)
        if abs(total_snapshot - (total_credit + total_cash)) > 0.0001:
            frappe.throw(_("Snapshot qty must equal Credit Qty + Cash Qty."))

    def calculate_totals(self):
        self.total_metered_qty = sum(flt(d.metered_qty) for d in self.meter_snapshots)
        self.total_billable_qty = sum(flt(d.billable_qty) for d in self.meter_snapshots)
        self.total_credit_qty = sum(flt(d.qty) for d in self.credit_allocations)
        self.total_cash_qty = sum(flt(d.cash_qty) for d in self.cash_summaries)
        self.total_credit_amount = sum(flt(d.amount) for d in self.credit_allocations)
        self.total_cash_amount = sum(flt(d.cash_amount) for d in self.cash_summaries)
        self.total_amount = flt(self.total_credit_amount) + flt(self.total_cash_amount)
        self.cash_over_short = flt(self.actual_cash_received) - flt(self.total_cash_amount)

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
        # credit grouped by customer
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
        inv.customer = customer
        inv.company = self.company
        inv.posting_date = self.date
        inv.due_date = self.date
        inv.set_posting_time = 1
        if self.posting_time:
            inv.posting_time = self.posting_time
        inv.currency = self.currency
        inv.update_stock = frappe.get_single("Fuel Station Settings").default_update_stock or 0
        inv.pump_reading_entry = self.name
        inv.shift_closing_entry = self.shift_closing_entry
        inv.pos_profile_link = self.pos_profile
        inv.fuel_station_date = self.date
        inv.fuel_pump = ", ".join(sorted({(d.fuel_pump or "") for d in rows if d.fuel_pump}))
        inv.fuel_nozzle = ", ".join(sorted({(d.fuel_nozzle or "") for d in rows if d.fuel_nozzle}))

        for row in rows:
            is_credit = row.doctype == "Pump Reading Credit Allocation"
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
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_invoice_reference/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_invoice_reference/pump_reading_invoice_reference.json

```
{
  "doctype": "DocType",
  "name": "Pump Reading Invoice Reference",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "sale_type",
      "label": "Sale Type",
      "fieldtype": "Data",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "customer",
      "label": "Customer",
      "fieldtype": "Link",
      "options": "Customer",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "sales_invoice",
      "label": "Sales Invoice",
      "fieldtype": "Link",
      "options": "Sales Invoice",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "source_table",
      "label": "Source Table",
      "fieldtype": "Data",
      "read_only": 1
    },
    {
      "fieldname": "source_row",
      "label": "Source Row",
      "fieldtype": "Data",
      "read_only": 1
    },
    {
      "fieldname": "amount",
      "label": "Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "outstanding_amount",
      "label": "Outstanding Amount",
      "fieldtype": "Currency",
      "read_only": 1
    }
  ],
  "field_order": [
    "sale_type",
    "customer",
    "sales_invoice",
    "source_table",
    "source_row",
    "amount",
    "outstanding_amount"
  ],
  "istable": 1,
  "issingle": 0,
  "editable_grid": 1,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_invoice_reference/pump_reading_invoice_reference.py

```
from frappe.model.document import Document

class PumpReadingInvoiceReference(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_line/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_line/pump_reading_line.json

```
{
  "doctype": "DocType",
  "name": "Pump Reading Line",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "source_shift_closing_line",
      "label": "Source Shift Closing Line",
      "fieldtype": "Data",
      "read_only": 1
    },
    {
      "fieldname": "fuel_pump",
      "label": "Fuel Pump",
      "fieldtype": "Link",
      "options": "Fuel Pump",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_nozzle",
      "label": "Fuel Nozzle",
      "fieldtype": "Link",
      "options": "Fuel Nozzle",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "item",
      "label": "Item",
      "fieldtype": "Link",
      "options": "Item",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "warehouse",
      "label": "Warehouse",
      "fieldtype": "Link",
      "options": "Warehouse",
      "read_only": 1
    },
    {
      "fieldname": "uom",
      "label": "UOM",
      "fieldtype": "Link",
      "options": "UOM",
      "read_only": 1
    },
    {
      "fieldname": "opening_reading",
      "label": "Opening Reading",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "current_reading",
      "label": "Current Reading",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "metered_qty",
      "label": "Metered Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "test_qty",
      "label": "Test Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "calibration_qty",
      "label": "Calibration Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "adjustment_qty",
      "label": "Adjustment Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "billable_qty",
      "label": "Billable Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "allocated_qty",
      "label": "Allocated Qty",
      "fieldtype": "Float",
      "precision": "3",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "rate",
      "label": "Rate",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "amount",
      "label": "Amount",
      "fieldtype": "Currency",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "sale_type",
      "label": "Sale Type",
      "fieldtype": "Select",
      "options": "Cash\nCredit",
      "reqd": 1,
      "default": "Cash",
      "in_list_view": 1
    },
    {
      "fieldname": "customer",
      "label": "Customer",
      "fieldtype": "Link",
      "options": "Customer",
      "in_list_view": 1
    },
    {
      "fieldname": "vehicle_no",
      "label": "Vehicle No",
      "fieldtype": "Data"
    },
    {
      "fieldname": "driver_name",
      "label": "Driver Name",
      "fieldtype": "Data"
    },
    {
      "fieldname": "cost_center",
      "label": "Cost Center",
      "fieldtype": "Link",
      "options": "Cost Center"
    },
    {
      "fieldname": "remarks",
      "label": "Remarks",
      "fieldtype": "Small Text"
    }
  ],
  "field_order": [
    "source_shift_closing_line",
    "fuel_pump",
    "fuel_nozzle",
    "item",
    "warehouse",
    "uom",
    "opening_reading",
    "current_reading",
    "metered_qty",
    "test_qty",
    "calibration_qty",
    "adjustment_qty",
    "billable_qty",
    "allocated_qty",
    "rate",
    "amount",
    "sale_type",
    "customer",
    "vehicle_no",
    "driver_name",
    "cost_center",
    "remarks"
  ],
  "sort_field": "modified",
  "sort_order": "DESC",
  "istable": 1,
  "issingle": 0,
  "editable_grid": 1,
  "is_submittable": 0,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_line/pump_reading_line.py

```
from frappe.model.document import Document

class PumpReadingLine(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_meter_snapshot/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_meter_snapshot/pump_reading_meter_snapshot.json

```
{
  "doctype": "DocType",
  "name": "Pump Reading Meter Snapshot",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "source_shift_closing_line",
      "label": "Source Shift Closing Line",
      "fieldtype": "Data",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_pump",
      "label": "Fuel Pump",
      "fieldtype": "Link",
      "options": "Fuel Pump",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "fuel_nozzle",
      "label": "Fuel Nozzle",
      "fieldtype": "Link",
      "options": "Fuel Nozzle",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "item",
      "label": "Item",
      "fieldtype": "Link",
      "options": "Item",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "warehouse",
      "label": "Warehouse",
      "fieldtype": "Link",
      "options": "Warehouse",
      "read_only": 1
    },
    {
      "fieldname": "uom",
      "label": "UOM",
      "fieldtype": "Link",
      "options": "UOM",
      "read_only": 1
    },
    {
      "fieldname": "opening_reading",
      "label": "Previous Reading",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "current_reading",
      "label": "Current Reading",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "metered_qty",
      "label": "Metered Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "test_qty",
      "label": "Test Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "calibration_qty",
      "label": "Calibration Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "adjustment_qty",
      "label": "Adjustment Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "billable_qty",
      "label": "Billable Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "rate",
      "label": "Rate",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "amount",
      "label": "Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "pos_profile",
      "label": "POS Profile",
      "fieldtype": "Link",
      "options": "POS Profile",
      "read_only": 1
    }
  ],
  "field_order": [
    "source_shift_closing_line",
    "fuel_pump",
    "fuel_nozzle",
    "item",
    "warehouse",
    "uom",
    "opening_reading",
    "current_reading",
    "metered_qty",
    "test_qty",
    "calibration_qty",
    "adjustment_qty",
    "billable_qty",
    "rate",
    "amount",
    "pos_profile"
  ],
  "istable": 1,
  "issingle": 0,
  "editable_grid": 1,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/pump_reading_meter_snapshot/pump_reading_meter_snapshot.py

```
from frappe.model.document import Document


class PumpReadingMeterSnapshot(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_entry/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_entry/shift_closing_entry.js

```
frappe.ui.form.on('Shift Closing Entry', {
	refresh(frm) {
		frm.set_query('pos_profile', () => ({ filters: { company: frm.doc.company } }));
	},
	company(frm) {
		if (!frm.doc.currency && frm.doc.company) {
			frappe.db.get_value('Company', frm.doc.company, 'default_currency').then(r => {
				if (r.message) frm.set_value('currency', r.message.default_currency);
			});
		}
	}
});

function update_closing_line(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const opening = flt(row.opening_reading);
	const closing = flt(row.closing_reading);
	const metered = closing - opening;
	frappe.model.set_value(cdt, cdn, 'metered_qty', metered);
	const net = metered - flt(row.test_qty) - flt(row.calibration_qty) + flt(row.adjustment_qty);
	frappe.model.set_value(cdt, cdn, 'net_billable_qty', net);
	frappe.model.set_value(cdt, cdn, 'gross_amount', metered * flt(row.rate));
	frappe.model.set_value(cdt, cdn, 'net_billable_amount', net * flt(row.rate));
	frm.trigger('recompute_totals');
}

frappe.ui.form.on('Shift Closing Line', {
	fuel_nozzle(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.fuel_nozzle) return;
		frappe.db.get_doc('Fuel Nozzle', row.fuel_nozzle).then(nozzle => {
			frappe.model.set_value(cdt, cdn, 'fuel_pump', nozzle.fuel_pump);
			frappe.model.set_value(cdt, cdn, 'item', nozzle.item);
			frappe.model.set_value(cdt, cdn, 'uom', nozzle.uom);
			frappe.model.set_value(cdt, cdn, 'warehouse', nozzle.warehouse);
		});
		frappe.call({
			method: 'dagaar_fuel_station.dagaar_fuel_station.doctype.pump_reading_entry.pump_reading_entry.get_nozzle_defaults',
			args: { nozzle: row.fuel_nozzle, pos_profile: frm.doc.pos_profile },
			callback: function(r) {
				if (!r.message) return;
				frappe.model.set_value(cdt, cdn, 'opening_reading', r.message.opening_reading || 0);
				frappe.model.set_value(cdt, cdn, 'rate', r.message.rate || 0);
				update_closing_line(frm, cdt, cdn);
			}
		});
	},
	closing_reading: update_closing_line,
	test_qty: update_closing_line,
	calibration_qty: update_closing_line,
	adjustment_qty: update_closing_line
});

frappe.ui.form.on('Shift Closing Entry', {
	recompute_totals(frm) {
		let total_metered_qty = 0, total_net_billable_qty = 0, total_gross_amount = 0, total_net_billable_amount = 0;
		(frm.doc.lines || []).forEach(d => {
			total_metered_qty += flt(d.metered_qty);
			total_net_billable_qty += flt(d.net_billable_qty);
			total_gross_amount += flt(d.gross_amount);
			total_net_billable_amount += flt(d.net_billable_amount);
		});
		frm.set_value('total_metered_qty', total_metered_qty);
		frm.set_value('total_net_billable_qty', total_net_billable_qty);
		frm.set_value('total_gross_amount', total_gross_amount);
		frm.set_value('total_net_billable_amount', total_net_billable_amount);
		frm.set_value('expected_cash_amount', total_net_billable_amount);
		frm.set_value('cash_over_short', flt(frm.doc.actual_cash_on_hand) - total_net_billable_amount);
	},
	actual_cash_on_hand(frm) { frm.trigger('recompute_totals'); }
});
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_entry/shift_closing_entry.json

```
{
  "doctype": "DocType",
  "name": "Shift Closing Entry",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "naming_series",
      "label": "Naming Series",
      "fieldtype": "Select",
      "options": "SCE-.YYYY.-",
      "default": "SCE-.YYYY.-",
      "reqd": 1
    },
    {
      "fieldname": "date",
      "label": "Date",
      "fieldtype": "Date",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "posting_time",
      "label": "Posting Time",
      "fieldtype": "Time"
    },
    {
      "fieldname": "shift",
      "label": "Shift",
      "fieldtype": "Select",
      "options": "Morning\nEvening\nNight",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "company",
      "label": "Company",
      "fieldtype": "Link",
      "options": "Company",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "pos_profile",
      "label": "Station / POS Profile",
      "fieldtype": "Link",
      "options": "POS Profile",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "attendant",
      "label": "Attendant",
      "fieldtype": "Link",
      "options": "Employee",
      "reqd": 1
    },
    {
      "fieldname": "currency",
      "label": "Currency",
      "fieldtype": "Link",
      "options": "Currency"
    },
    {
      "fieldname": "opening_cash_float",
      "label": "Opening Cash Float",
      "fieldtype": "Currency",
      "options": "currency"
    },
    {
      "fieldname": "actual_cash_on_hand",
      "label": "Actual Cash On Hand",
      "fieldtype": "Currency",
      "options": "currency"
    },
    {
      "fieldname": "expected_cash_amount",
      "label": "Expected Cash Amount",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "cash_over_short",
      "label": "Cash Over / Short",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "remarks",
      "label": "Remarks",
      "fieldtype": "Small Text"
    },
    {
      "fieldname": "section_totals",
      "label": "Totals",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "total_metered_qty",
      "label": "Total Metered Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "total_net_billable_qty",
      "label": "Total Net Billable Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "total_gross_amount",
      "label": "Total Gross Amount",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "total_net_billable_amount",
      "label": "Total Net Billable Amount",
      "fieldtype": "Currency",
      "options": "currency",
      "read_only": 1
    },
    {
      "fieldname": "section_lines",
      "label": "Nozzle Closing Readings",
      "fieldtype": "Section Break"
    },
    {
      "fieldname": "lines",
      "label": "Lines",
      "fieldtype": "Table",
      "options": "Shift Closing Line",
      "reqd": 1
    }
  ],
  "field_order": [
    "naming_series",
    "date",
    "posting_time",
    "shift",
    "company",
    "pos_profile",
    "attendant",
    "currency",
    "opening_cash_float",
    "actual_cash_on_hand",
    "expected_cash_amount",
    "cash_over_short",
    "remarks",
    "section_totals",
    "total_metered_qty",
    "total_net_billable_qty",
    "total_gross_amount",
    "total_net_billable_amount",
    "section_lines",
    "lines"
  ],
  "permissions": [
    {
      "role": "System Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "delete": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "export": 1,
      "print": 1
    },
    {
      "role": "Sales Manager",
      "read": 1,
      "write": 1,
      "create": 1,
      "submit": 1,
      "cancel": 1,
      "amend": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Sales User",
      "read": 1,
      "write": 1,
      "create": 1,
      "report": 1,
      "print": 1
    },
    {
      "role": "Accounts User",
      "read": 1,
      "report": 1,
      "print": 1
    }
  ],
  "sort_field": "modified",
  "sort_order": "DESC",
  "istable": 0,
  "issingle": 0,
  "editable_grid": 1,
  "is_submittable": 1,
  "quick_entry": 0,
  "title_field": "date",
  "search_fields": "date,shift,attendant,pos_profile"
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_entry/shift_closing_entry.py

```
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from dagaar_fuel_station.dagaar_fuel_station.utils import get_last_nozzle_closing, get_item_rate, get_pos_price_list, validate_company_for_pos_profile


class ShiftClosingEntry(Document):
    def validate(self):
        validate_company_for_pos_profile(self.company, self.pos_profile)
        self.set_missing_values()
        self.calculate_lines()
        self.validate_lines()
        self.calculate_totals()

    def set_missing_values(self):
        if self.company and not self.currency:
            self.currency = frappe.get_cached_value("Company", self.company, "default_currency")
        seen = set()
        for row in self.lines:
            if row.fuel_nozzle in seen:
                frappe.throw(_("Duplicate nozzle {0} in lines.").format(row.fuel_nozzle))
            seen.add(row.fuel_nozzle)
            if row.fuel_nozzle:
                nozzle = frappe.get_cached_doc("Fuel Nozzle", row.fuel_nozzle)
                row.fuel_pump = nozzle.fuel_pump
                row.item = nozzle.item
                row.uom = nozzle.uom or frappe.get_cached_value("Item", nozzle.item, "stock_uom")
                row.warehouse = nozzle.warehouse
                if not row.opening_reading:
                    row.opening_reading = get_last_nozzle_closing(row.fuel_nozzle)
                price_list = get_pos_price_list(self.pos_profile)
                row.rate = get_item_rate(nozzle.item, price_list, row.uom, company=self.company, posting_date=self.date)

    def calculate_lines(self):
        for row in self.lines:
            row.metered_qty = flt(row.closing_reading) - flt(row.opening_reading)
            row.net_billable_qty = flt(row.metered_qty) - flt(row.test_qty) - flt(row.calibration_qty) + flt(row.adjustment_qty)
            row.gross_amount = flt(row.metered_qty) * flt(row.rate)
            row.net_billable_amount = flt(row.net_billable_qty) * flt(row.rate)

    def validate_lines(self):
        for row in self.lines:
            if flt(row.closing_reading) < flt(row.opening_reading):
                frappe.throw(_("Closing reading cannot be less than opening reading for nozzle {0}.").format(row.fuel_nozzle))
            if flt(row.net_billable_qty) < 0:
                frappe.throw(_("Net billable quantity cannot be negative for nozzle {0}.").format(row.fuel_nozzle))
            if row.warehouse:
                wh_company = frappe.db.get_value("Warehouse", row.warehouse, "company")
                if wh_company and wh_company != self.company:
                    frappe.throw(_("Warehouse {0} must belong to company {1}.").format(row.warehouse, self.company))

    def calculate_totals(self):
        self.total_metered_qty = sum(flt(d.metered_qty) for d in self.lines)
        self.total_net_billable_qty = sum(flt(d.net_billable_qty) for d in self.lines)
        self.total_gross_amount = sum(flt(d.gross_amount) for d in self.lines)
        self.total_net_billable_amount = sum(flt(d.net_billable_amount) for d in self.lines)
        self.expected_cash_amount = self.total_net_billable_amount
        self.cash_over_short = flt(self.actual_cash_on_hand) - flt(self.expected_cash_amount)
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_line/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_line/shift_closing_line.json

```
{
  "doctype": "DocType",
  "name": "Shift Closing Line",
  "module": "Dagaar Fuel Station",
  "custom": 0,
  "engine": "InnoDB",
  "track_changes": 1,
  "fields": [
    {
      "fieldname": "fuel_pump",
      "label": "Fuel Pump",
      "fieldtype": "Link",
      "options": "Fuel Pump",
      "in_list_view": 1,
      "read_only": 1
    },
    {
      "fieldname": "fuel_nozzle",
      "label": "Fuel Nozzle",
      "fieldtype": "Link",
      "options": "Fuel Nozzle",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "item",
      "label": "Item",
      "fieldtype": "Link",
      "options": "Item",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "uom",
      "label": "UOM",
      "fieldtype": "Link",
      "options": "UOM",
      "read_only": 1
    },
    {
      "fieldname": "warehouse",
      "label": "Warehouse",
      "fieldtype": "Link",
      "options": "Warehouse",
      "read_only": 1
    },
    {
      "fieldname": "opening_reading",
      "label": "Opening Reading",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "closing_reading",
      "label": "Closing Reading",
      "fieldtype": "Float",
      "precision": "3",
      "reqd": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "metered_qty",
      "label": "Metered Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1,
      "in_list_view": 1
    },
    {
      "fieldname": "test_qty",
      "label": "Test Qty",
      "fieldtype": "Float",
      "precision": "3",
      "default": "0"
    },
    {
      "fieldname": "calibration_qty",
      "label": "Calibration Qty",
      "fieldtype": "Float",
      "precision": "3",
      "default": "0"
    },
    {
      "fieldname": "adjustment_qty",
      "label": "Adjustment Qty",
      "fieldtype": "Float",
      "precision": "3",
      "default": "0"
    },
    {
      "fieldname": "net_billable_qty",
      "label": "Net Billable Qty",
      "fieldtype": "Float",
      "precision": "3",
      "read_only": 1
    },
    {
      "fieldname": "rate",
      "label": "Rate",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "gross_amount",
      "label": "Gross Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "net_billable_amount",
      "label": "Net Billable Amount",
      "fieldtype": "Currency",
      "read_only": 1
    },
    {
      "fieldname": "notes",
      "label": "Notes",
      "fieldtype": "Small Text"
    }
  ],
  "field_order": [
    "fuel_pump",
    "fuel_nozzle",
    "item",
    "uom",
    "warehouse",
    "opening_reading",
    "closing_reading",
    "metered_qty",
    "test_qty",
    "calibration_qty",
    "adjustment_qty",
    "net_billable_qty",
    "rate",
    "gross_amount",
    "net_billable_amount",
    "notes"
  ],
  "sort_field": "modified",
  "sort_order": "DESC",
  "istable": 1,
  "issingle": 0,
  "editable_grid": 1,
  "is_submittable": 0,
  "quick_entry": 0
}
```

## dagaar_fuel_station/dagaar_fuel_station/doctype/shift_closing_line/shift_closing_line.py

```
from frappe.model.document import Document

class ShiftClosingLine(Document):
    pass
```

## dagaar_fuel_station/dagaar_fuel_station/module.txt

```
Dagaar Fuel Station
```

## dagaar_fuel_station/dagaar_fuel_station/page/fuel_station_dashboard/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/page/fuel_station_dashboard/fuel_station_dashboard.css

```
.fuel-dashboard-root { padding: 12px; }
.fuel-dashboard-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.fuel-dashboard-grid.bottom { grid-template-columns: 2fr 1fr; margin-top: 16px; }
.fuel-card, .fuel-panel { border-radius: 14px; padding: 18px; box-shadow: 0 2px 8px rgba(0,0,0,.08); background: #fff; }
.fuel-card.orange { background: linear-gradient(135deg, #fff0d8, #ffe1a8); }
.fuel-card.blue { background: linear-gradient(135deg, #dff4ff, #b7e6ff); }
.fuel-card.red { background: linear-gradient(135deg, #ffe3e3, #ffc0c0); }
.fuel-card .big { font-size: 28px; font-weight: 700; }
.fuel-card .small { margin-top: 6px; color: #555; }
.fuel-bar-row { display: grid; grid-template-columns: 95px 1fr 120px; gap: 10px; align-items: center; margin: 10px 0; }
.fuel-bar-row .bar-wrap { background: #f0f0f0; border-radius: 999px; height: 16px; overflow: hidden; }
.fuel-bar-row .bar { background: linear-gradient(90deg, #7c3aed, #06b6d4); height: 100%; border-radius: 999px; }
```

## dagaar_fuel_station/dagaar_fuel_station/page/fuel_station_dashboard/fuel_station_dashboard.js

```
frappe.pages['fuel-station-dashboard'].on_page_load = function(wrapper) {
	new FuelStationDashboard(wrapper);
};

class FuelStationDashboard {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __('Fuel Station Dashboard'),
			single_column: true
		});
		this.make();
	}

	make() {
		this.page.add_field({
			label: __('Company'),
			fieldname: 'company',
			fieldtype: 'Link',
			options: 'Company',
			change: () => this.refresh()
		});
		this.page.add_field({
			label: __('Date'),
			fieldname: 'date',
			fieldtype: 'Date',
			default: frappe.datetime.get_today(),
			change: () => this.refresh()
		});
		this.body = $('<div class="fuel-dashboard-root"></div>').appendTo(this.page.main);
		this.refresh();
	}

	refresh() {
		const company = this.page.fields_dict.company.get_value();
		const date = this.page.fields_dict.date.get_value();
		frappe.call({
			method: 'dagaar_fuel_station.dagaar_fuel_station.dashboard.get_dashboard_data',
			args: { company, date },
			callback: (r) => this.render(r.message || {})
		});
	}

	render(data) {
		const dailyBars = (data.daily || []).map(d => {
			const width = Math.max(8, Math.min(100, (d.amount || 0) / Math.max(1, ...((data.daily || []).map(x => x.amount || 0))) * 100));
			return `
				<div class="fuel-bar-row">
					<div class="label">${frappe.datetime.str_to_user(d.date)}</div>
					<div class="bar-wrap"><div class="bar" style="width:${width}%"></div></div>
					<div class="value">${format_currency(d.amount || 0)}</div>
				</div>`;
		}).join('');

		const nozzleRows = (data.top_nozzles || []).map(d => `
			<tr><td>${frappe.utils.escape_html(d.fuel_nozzle || '')}</td><td class="text-right">${format_number(d.liters || 0, null, 3)}</td></tr>
		`).join('');

		this.body.html(`
			<div class="fuel-dashboard-grid">
				<div class="fuel-card orange"><div class="big">${data.shift_closing_count || 0}</div><div class="small">Submitted Shift Closings</div></div>
				<div class="fuel-card blue"><div class="big">${format_currency(data.billed_amount || 0)}</div><div class="small">Billed Amount</div></div>
				<div class="fuel-card red"><div class="big">${format_currency(data.unpaid_credit || 0)}</div><div class="small">Unpaid Credit</div></div>
			</div>
			<div class="fuel-dashboard-grid bottom">
				<div class="fuel-panel">
					<h4>${__('7-Day Billing Trend')}</h4>
					${dailyBars || `<div class="text-muted">${__('No data')}</div>`}
				</div>
				<div class="fuel-panel">
					<h4>${__('Top Nozzles')}</h4>
					<table class="table table-bordered"><thead><tr><th>${__('Nozzle')}</th><th class="text-right">${__('Liters')}</th></tr></thead><tbody>${nozzleRows || `<tr><td colspan="2" class="text-muted">${__('No data')}</td></tr>`}</tbody></table>
				</div>
			</div>
		`);
	}
}
```

## dagaar_fuel_station/dagaar_fuel_station/page/fuel_station_dashboard/fuel_station_dashboard.json

```
{
  "doctype": "Page",
  "name": "fuel-station-dashboard",
  "module": "Dagaar Fuel Station",
  "title": "Fuel Station Dashboard",
  "standard": "Yes",
  "roles": [
    {
      "role": "System Manager"
    },
    {
      "role": "Accounts Manager"
    },
    {
      "role": "Sales Manager"
    },
    {
      "role": "Sales User"
    }
  ]
}
```

## dagaar_fuel_station/dagaar_fuel_station/page/fuel_station_dashboard/fuel_station_dashboard.py

```
import frappe
```

## dagaar_fuel_station/dagaar_fuel_station/report/customer_credit_fuel_sales/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/report/customer_credit_fuel_sales/customer_credit_fuel_sales.js

```
frappe.query_reports["Customer Credit Fuel Sales"] = {
	filters: [
		{fieldname: 'from_date', label: __('From Date'), fieldtype: 'Date'},
		{fieldname: 'to_date', label: __('To Date'), fieldtype: 'Date'},
		{fieldname: 'company', label: __('Company'), fieldtype: 'Link', options: 'Company'},
		{fieldname: 'pos_profile', label: __('POS Profile'), fieldtype: 'Link', options: 'POS Profile'},
		{fieldname: 'sale_type', label: __('Sale Type'), fieldtype: 'Select', options: '
Cash
Credit'},
		{fieldname: 'customer', label: __('Customer'), fieldtype: 'Link', options: 'Customer'},
		{fieldname: 'fuel_nozzle', label: __('Fuel Nozzle'), fieldtype: 'Link', options: 'Fuel Nozzle'}
	]
};
```

## dagaar_fuel_station/dagaar_fuel_station/report/customer_credit_fuel_sales/customer_credit_fuel_sales.json

```
{
  "doctype": "Report",
  "name": "Customer Credit Fuel Sales",
  "report_name": "Customer Credit Fuel Sales",
  "ref_doctype": "Sales Invoice",
  "report_type": "Script Report",
  "module": "Dagaar Fuel Station",
  "is_standard": "Yes",
  "roles": [
    {
      "role": "System Manager"
    },
    {
      "role": "Accounts Manager"
    },
    {
      "role": "Accounts User"
    },
    {
      "role": "Sales Manager"
    },
    {
      "role": "Sales User"
    }
  ]
}
```

## dagaar_fuel_station/dagaar_fuel_station/report/customer_credit_fuel_sales/customer_credit_fuel_sales.py

```
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
```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_billing_summary/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_billing_summary/fuel_billing_summary.js

```
frappe.query_reports["Fuel Billing Summary"] = {
	filters: [
		{fieldname: 'from_date', label: __('From Date'), fieldtype: 'Date'},
		{fieldname: 'to_date', label: __('To Date'), fieldtype: 'Date'},
		{fieldname: 'company', label: __('Company'), fieldtype: 'Link', options: 'Company'},
		{fieldname: 'pos_profile', label: __('POS Profile'), fieldtype: 'Link', options: 'POS Profile'},
		{fieldname: 'sale_type', label: __('Sale Type'), fieldtype: 'Select', options: '
Cash
Credit'},
		{fieldname: 'customer', label: __('Customer'), fieldtype: 'Link', options: 'Customer'},
		{fieldname: 'fuel_nozzle', label: __('Fuel Nozzle'), fieldtype: 'Link', options: 'Fuel Nozzle'}
	]
};
```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_billing_summary/fuel_billing_summary.json

```
{
  "doctype": "Report",
  "name": "Fuel Billing Summary",
  "report_name": "Fuel Billing Summary",
  "ref_doctype": "Pump Reading Entry",
  "report_type": "Script Report",
  "module": "Dagaar Fuel Station",
  "is_standard": "Yes",
  "roles": [
    {
      "role": "System Manager"
    },
    {
      "role": "Accounts Manager"
    },
    {
      "role": "Accounts User"
    },
    {
      "role": "Sales Manager"
    },
    {
      "role": "Sales User"
    }
  ]
}
```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_billing_summary/fuel_billing_summary.py

```
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
```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_station_daily_summary/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_station_daily_summary/fuel_station_daily_summary.js

```
frappe.query_reports['Fuel Station Daily Summary'] = {filters:[{fieldname:'from_date',label:'From Date',fieldtype:'Date'},{fieldname:'to_date',label:'To Date',fieldtype:'Date'}]};
```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_station_daily_summary/fuel_station_daily_summary.json

```
{
  "doctype": "Report",
  "name": "Fuel Station Daily Summary",
  "module": "Dagaar Fuel Station",
  "report_name": "Fuel Station Daily Summary",
  "ref_doctype": "Pump Reading Entry",
  "report_type": "Script Report",
  "is_standard": "Yes",
  "json": "{}"
}
```

## dagaar_fuel_station/dagaar_fuel_station/report/fuel_station_daily_summary/fuel_station_daily_summary.py

```
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
```

## dagaar_fuel_station/dagaar_fuel_station/report/shift_closing_summary/__init__.py

```

```

## dagaar_fuel_station/dagaar_fuel_station/report/shift_closing_summary/shift_closing_summary.js

```
frappe.query_reports["Shift Closing Summary"] = {
	filters: [
		{fieldname: 'from_date', label: __('From Date'), fieldtype: 'Date'},
		{fieldname: 'to_date', label: __('To Date'), fieldtype: 'Date'},
		{fieldname: 'company', label: __('Company'), fieldtype: 'Link', options: 'Company'},
		{fieldname: 'pos_profile', label: __('POS Profile'), fieldtype: 'Link', options: 'POS Profile'},
		{fieldname: 'sale_type', label: __('Sale Type'), fieldtype: 'Select', options: '
Cash
Credit'},
		{fieldname: 'customer', label: __('Customer'), fieldtype: 'Link', options: 'Customer'},
		{fieldname: 'fuel_nozzle', label: __('Fuel Nozzle'), fieldtype: 'Link', options: 'Fuel Nozzle'}
	]
};
```

## dagaar_fuel_station/dagaar_fuel_station/report/shift_closing_summary/shift_closing_summary.json

```
{
  "doctype": "Report",
  "name": "Shift Closing Summary",
  "report_name": "Shift Closing Summary",
  "ref_doctype": "Shift Closing Entry",
  "report_type": "Script Report",
  "module": "Dagaar Fuel Station",
  "is_standard": "Yes",
  "roles": [
    {
      "role": "System Manager"
    },
    {
      "role": "Accounts Manager"
    },
    {
      "role": "Accounts User"
    },
    {
      "role": "Sales Manager"
    },
    {
      "role": "Sales User"
    }
  ]
}
```

## dagaar_fuel_station/dagaar_fuel_station/report/shift_closing_summary/shift_closing_summary.py

```
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
```

## dagaar_fuel_station/dagaar_fuel_station/utils.py

```
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
```

## dagaar_fuel_station/fixtures/custom_field.json

```
[
  {
    "name": "Sales Invoice-pump_reading_entry",
    "doctype": "Custom Field",
    "dt": "Sales Invoice",
    "fieldname": "pump_reading_entry",
    "label": "Pump Reading Entry",
    "fieldtype": "Link",
    "options": "Pump Reading Entry",
    "insert_after": "remarks",
    "read_only": 1
  },
  {
    "name": "Sales Invoice-shift_closing_entry",
    "doctype": "Custom Field",
    "dt": "Sales Invoice",
    "fieldname": "shift_closing_entry",
    "label": "Shift Closing Entry",
    "fieldtype": "Link",
    "options": "Shift Closing Entry",
    "insert_after": "pump_reading_entry",
    "read_only": 1
  },
  {
    "name": "Sales Invoice-fuel_pump",
    "doctype": "Custom Field",
    "dt": "Sales Invoice",
    "fieldname": "fuel_pump",
    "label": "Fuel Pump",
    "fieldtype": "Data",
    "insert_after": "shift_closing_entry",
    "read_only": 1
  },
  {
    "name": "Sales Invoice-fuel_nozzle",
    "doctype": "Custom Field",
    "dt": "Sales Invoice",
    "fieldname": "fuel_nozzle",
    "label": "Fuel Nozzle",
    "fieldtype": "Data",
    "insert_after": "fuel_pump",
    "read_only": 1
  },
  {
    "name": "Sales Invoice-pos_profile_link",
    "doctype": "Custom Field",
    "dt": "Sales Invoice",
    "fieldname": "pos_profile_link",
    "label": "POS Profile",
    "fieldtype": "Link",
    "options": "POS Profile",
    "insert_after": "fuel_nozzle",
    "read_only": 1
  },
  {
    "name": "Sales Invoice-fuel_station_date",
    "doctype": "Custom Field",
    "dt": "Sales Invoice",
    "fieldname": "fuel_station_date",
    "label": "Fuel Station Date",
    "fieldtype": "Date",
    "insert_after": "pos_profile_link",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-source_pump_reading_line",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "source_pump_reading_line",
    "label": "Source Pump Reading Line",
    "fieldtype": "Data",
    "insert_after": "description",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-source_shift_closing_line",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "source_shift_closing_line",
    "label": "Source Shift Closing Line",
    "fieldtype": "Data",
    "insert_after": "source_pump_reading_line",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-opening_meter_reading",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "opening_meter_reading",
    "label": "Opening Meter Reading",
    "fieldtype": "Float",
    "insert_after": "source_shift_closing_line",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-closing_meter_reading",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "closing_meter_reading",
    "label": "Closing Meter Reading",
    "fieldtype": "Float",
    "insert_after": "opening_meter_reading",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-metered_qty",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "metered_qty",
    "label": "Metered Qty",
    "fieldtype": "Float",
    "insert_after": "closing_meter_reading",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-allocated_qty",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "allocated_qty",
    "label": "Allocated Qty",
    "fieldtype": "Float",
    "insert_after": "metered_qty",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-fuel_pump",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "fuel_pump",
    "label": "Fuel Pump",
    "fieldtype": "Data",
    "insert_after": "allocated_qty",
    "read_only": 1
  },
  {
    "name": "Sales Invoice Item-fuel_nozzle",
    "doctype": "Custom Field",
    "dt": "Sales Invoice Item",
    "fieldname": "fuel_nozzle",
    "label": "Fuel Nozzle",
    "fieldtype": "Data",
    "insert_after": "fuel_pump",
    "read_only": 1
  }
]
```

## dagaar_fuel_station/hooks.py

```
app_name = "dagaar_fuel_station"
app_title = "Dagaar Fuel Station"
app_publisher = "OpenAI"
app_description = "Advanced nozzle, shift, billing, dashboard, and reports for ERPNext fuel stations"
app_email = "support@example.com"
app_license = "MIT"

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [[
            "name",
            "in",
            [
                "Sales Invoice-pump_reading_entry",
                "Sales Invoice-shift_closing_entry",
                "Sales Invoice-fuel_pump",
                "Sales Invoice-fuel_nozzle",
                "Sales Invoice-pos_profile_link",
                "Sales Invoice-fuel_station_date",
                "Sales Invoice Item-source_pump_reading_line",
                "Sales Invoice Item-source_shift_closing_line",
                "Sales Invoice Item-opening_meter_reading",
                "Sales Invoice Item-closing_meter_reading",
                "Sales Invoice Item-metered_qty",
                "Sales Invoice Item-allocated_qty",
                "Sales Invoice Item-fuel_pump",
                "Sales Invoice Item-fuel_nozzle"
            ]
        ]]
    }
]
```

## dagaar_fuel_station/modules.txt

```
Dagaar Fuel Station
```

## dagaar_fuel_station/patches.txt

```

```

## dagaar_fuel_station/public/js/dagaar_fuel_station.bundle.js

```
// build-safe empty bundle
```

## dagaar_fuel_station/sample_test_data.md

```
- Company: FuelCo
- POS Profile: Main Station
- Customer: Cash Customer
- Item: Petrol, Diesel
- Fuel Pump: P-01, P-02
- Fuel Nozzle: P-01-A, P-01-B, P-02-A
- Employee: ATT-0001

Workflow:
1. Submit Shift Closing Entry with nozzle closing readings.
2. Create Pump Reading Entry linked to Shift Closing Entry.
3. Click Fetch From Shift Closing.
4. Split rows by customer and sale type if needed.
5. Submit Pump Reading Entry to auto-create Sales Invoices.
```

## license.txt

```
MIT
```

## package.json

```
{
  "name": "dagaar_fuel_station",
  "version": "0.0.2",
  "private": true,
  "description": "Dagaar Fuel Station assets",
  "dependencies": {}
}
```

## pyproject.toml

```
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

## requirements.txt

```

```

## setup.py

```
from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().strip().splitlines()

setup(
    name='dagaar_fuel_station',
    version='0.0.1',
    description='Advanced fuel station operations and billing for ERPNext',
    author='OpenAI',
    author_email='support@example.com',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
)
```

