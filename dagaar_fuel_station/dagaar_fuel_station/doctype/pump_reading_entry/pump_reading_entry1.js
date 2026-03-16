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
    setup(frm) {
        frm.set_query('shift_closing_entry', function(doc) {
            const filters = { docstatus: 1, status: ['!=', 'Closed'] };
            if (doc.company) filters.company = doc.company;
            if (doc.pos_profile) filters.pos_profile = doc.pos_profile;
            return { filters };
        });

        frm.set_query('source_shift_closing_line', 'credit_allocations', function(doc) {
            return {
                query: 'dagaar_fuel_station.dagaar_fuel_station.doctype.pump_reading_entry.pump_reading_entry.get_shift_closing_line_query',
                filters: {
                    shift_closing_entry: doc.shift_closing_entry
                }
            };
        });
    },
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
