
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
        row.base_rate = s.base_rate;
        row.cash_amount = cash_qty * flt(s.rate);
        row.cash_amount_home = row.cash_amount * flt(frm.doc.conversion_rate || 1);
        row.adjustment_qty = s.adjustment_qty;
        row.adjustment_amount = flt(s.adjustment_qty) * flt(s.rate);
        row.adjustment_amount_home = row.adjustment_amount * flt(frm.doc.conversion_rate || 1);
        row.net_balance_qty = cash_qty;
        row.net_balance_amount = cash_qty * flt(s.rate);
        row.net_balance_amount_home = row.net_balance_amount * flt(frm.doc.conversion_rate || 1);
    });
    frm.refresh_field('cash_summaries');
    frm.trigger('recompute_totals');
}

function sync_credit_row(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    let source = null;
    if (row.source_shift_closing_line) {
        source = (frm.doc.meter_snapshots || []).find(d => d.source_shift_closing_line === row.source_shift_closing_line);
    }
    if (!source && row.fuel_nozzle) {
        source = (frm.doc.meter_snapshots || []).find(d => d.fuel_nozzle === row.fuel_nozzle);
        if (source) {
            row.source_shift_closing_line = source.source_shift_closing_line;
        }
    }
    if (source) {
        row.fuel_pump = source.fuel_pump;
        row.fuel_nozzle = source.fuel_nozzle;
        row.item = source.item;
        row.uom = source.uom;
        row.rate = source.rate;
        row.base_rate = source.base_rate;
        const gross_amount = flt(row.qty) * flt(row.rate);
        row.discount_amount = flt(row.discount_amount);
        if (row.discount_amount < 0) row.discount_amount = 0;
        if (row.discount_amount > gross_amount) row.discount_amount = gross_amount;
        row.amount = gross_amount - row.discount_amount;
        row.amount_home = flt(row.amount) * flt(frm.doc.conversion_rate || 1);
        frm.refresh_field('credit_allocations');
    }
    recompute_cash_summary(frm);
}

function set_currency_context(frm, callback) {
    if (!frm.doc.company) return;
    frappe.call({
        method: 'dagaar_fuel_station.dagaar_fuel_station.utils.get_currency_context',
        args: { company: frm.doc.company, currency: frm.doc.currency, posting_date: frm.doc.date },
        callback: function(r) {
            if (!r.message) return;
            frm.set_value('home_currency', r.message.home_currency);
            frm.set_value('currency', r.message.currency);
            frm.set_value('conversion_rate', r.message.conversion_rate || 1);
            if (callback) callback();
        }
    });
}

frappe.ui.form.on('Pump Reading Entry', {
    setup(frm) {
        frm.set_query('shift_closing_entry', function(doc) {
            const filters = { docstatus: 1, status: ['!=', 'Closed'] };
            if (doc.company) filters.company = doc.company;
            if (doc.pos_profile) filters.pos_profile = doc.pos_profile;
            return { filters };
        });

        frm.set_query('fuel_nozzle', 'credit_allocations', function(doc) {
            return {
                query: 'dagaar_fuel_station.dagaar_fuel_station.doctype.pump_reading_entry.pump_reading_entry.get_shift_closing_nozzle_query',
                filters: {
                    shift_closing_entry: doc.shift_closing_entry
                }
            };
        });
    },
    onload(frm) { set_currency_context(frm); },
    company(frm) { set_currency_context(frm); },
    date(frm) { set_currency_context(frm); },
    currency(frm) { set_currency_context(frm, () => frm.trigger('recompute_totals')); },
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
            frm.set_value('home_currency', doc.home_currency);
            frm.set_value('conversion_rate', doc.conversion_rate || 1);
        });
    },
    recompute_totals(frm) {
        let total_metered_qty = 0, total_billable_qty = 0, total_credit_qty = 0, total_cash_qty = 0, total_credit_amount = 0, total_cash_amount = 0;
        const additional_discount_amount = flt(frm.doc.additional_discount_amount);
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
        frm.set_value('total_amount', total_credit_amount + total_cash_amount - additional_discount_amount);
        frm.set_value('total_credit_amount_home', total_credit_amount * flt(frm.doc.conversion_rate || 1));
        frm.set_value('total_cash_amount_home', total_cash_amount * flt(frm.doc.conversion_rate || 1));
        frm.set_value('total_amount_home', flt(frm.doc.total_amount) * flt(frm.doc.conversion_rate || 1));
        frm.set_value('actual_cash_received_home', flt(frm.doc.actual_cash_received) * flt(frm.doc.conversion_rate || 1));
        frm.set_value('cash_over_short', flt(frm.doc.actual_cash_received) - (total_cash_amount - additional_discount_amount));
        frm.set_value('cash_over_short_home', flt(frm.doc.cash_over_short) * flt(frm.doc.conversion_rate || 1));
    },
    actual_cash_received(frm) {
        frm.trigger('recompute_totals');
    },
    additional_discount_amount(frm) {
        frm.trigger('recompute_totals');
    }
});

frappe.ui.form.on('Pump Reading Credit Allocation', {
    fuel_nozzle(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); },
    qty(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); },
    customer(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); },
    discount_amount(frm, cdt, cdn) { sync_credit_row(frm, cdt, cdn); }
});
