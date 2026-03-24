
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
    frappe.model.set_value(cdt, cdn, 'base_rate', flt(row.rate) * flt(frm.doc.conversion_rate || 1));
    frappe.model.set_value(cdt, cdn, 'gross_amount_home', flt(row.gross_amount) * flt(frm.doc.conversion_rate || 1));
    frappe.model.set_value(cdt, cdn, 'net_billable_amount_home', flt(row.net_billable_amount) * flt(frm.doc.conversion_rate || 1));
    frm.trigger('recompute_totals');
}

function apply_nozzle_defaults(frm, cdt, cdn, nozzle_name) {
    if (!nozzle_name) return;
    frappe.call({
        method: 'dagaar_fuel_station.dagaar_fuel_station.doctype.pump_reading_entry.pump_reading_entry.get_nozzle_defaults',
        args: { nozzle: nozzle_name, pos_profile: frm.doc.pos_profile, currency: frm.doc.currency, company: frm.doc.company, posting_date: frm.doc.date },
        callback: function(r) {
            if (!r.message) return;
            frappe.model.set_value(cdt, cdn, 'fuel_pump', r.message.fuel_pump || null);
            frappe.model.set_value(cdt, cdn, 'item', r.message.item || null);
            frappe.model.set_value(cdt, cdn, 'uom', r.message.uom || null);
            frappe.model.set_value(cdt, cdn, 'warehouse', r.message.warehouse || null);
            frappe.model.set_value(cdt, cdn, 'display_name', r.message.display_name || nozzle_name);
            frappe.model.set_value(cdt, cdn, 'opening_reading', r.message.opening_reading || 0);
            frappe.model.set_value(cdt, cdn, 'rate', r.message.rate || 0);
            frappe.model.set_value(cdt, cdn, 'base_rate', r.message.base_rate || 0);
            update_closing_line(frm, cdt, cdn);
        }
    });
}

function refresh_opening_readings(frm) {
    const nozzles = (frm.doc.lines || []).map(d => d.fuel_nozzle).filter(Boolean);
    if (!nozzles.length) return;
    frappe.call({
        method: 'dagaar_fuel_station.dagaar_fuel_station.doctype.shift_closing_entry.shift_closing_entry.get_latest_opening_readings',
        args: { nozzles: nozzles },
        callback: function(r) {
            const readings = r.message || {};
            (frm.doc.lines || []).forEach(row => {
                if (row.fuel_nozzle && Object.prototype.hasOwnProperty.call(readings, row.fuel_nozzle)) {
                    frappe.model.set_value(row.doctype, row.name, 'opening_reading', flt(readings[row.fuel_nozzle]));
                    update_closing_line(frm, row.doctype, row.name);
                }
            });
        }
    });
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

function load_station_nozzles(frm) {
    if (!frm.doc.company || !frm.doc.pos_profile || frm.doc.docstatus > 0) return;
    const existing = (frm.doc.lines || []).map(d => d.fuel_nozzle).filter(Boolean);
    frappe.call({
        method: 'dagaar_fuel_station.dagaar_fuel_station.doctype.shift_closing_entry.shift_closing_entry.get_station_nozzles',
        args: {
            company: frm.doc.company,
            pos_profile: frm.doc.pos_profile,
            existing_nozzles: existing,
            currency: frm.doc.currency,
            posting_date: frm.doc.date
        },
        callback: function(r) {
            (r.message || []).forEach(d => {
                const row = frm.add_child('lines');
                Object.assign(row, d);
            });
            frm.refresh_field('lines');
            refresh_opening_readings(frm);
            frm.trigger('recompute_totals');
        }
    });
}

frappe.ui.form.on('Shift Closing Entry', {
    setup(frm) {
        frm.set_query('pos_profile', () => ({ filters: { company: frm.doc.company } }));
        frm.set_query('fuel_nozzle', 'lines', function(doc, cdt, cdn) {
            const row = locals[cdt][cdn] || {};
            const filters = {
                company: doc.company,
                pos_profile: doc.pos_profile,
                active: 1
            };
            if (row.fuel_pump) filters.fuel_pump = row.fuel_pump;
            return { filters };
        });
    },
    refresh(frm) {
        if (!frm.is_new() && frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Refresh Opening Readings'), function() {
                refresh_opening_readings(frm);
            });
        }
    },
    onload(frm) {
        set_currency_context(frm);
    },
    company(frm) { set_currency_context(frm); },
    date(frm) { set_currency_context(frm); },
    currency(frm) { set_currency_context(frm, () => frm.trigger('recompute_totals')); },
    pos_profile(frm) {
        if (!frm.doc.company || !frm.doc.pos_profile) return;
        frappe.db.get_value('POS Profile', frm.doc.pos_profile, 'company').then(r => {
            if (r.message && r.message.company) frm.set_value('company', r.message.company);
            load_station_nozzles(frm);
        });
    },
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
        frm.set_value('total_gross_amount_home', total_gross_amount * flt(frm.doc.conversion_rate || 1));
        frm.set_value('total_net_billable_amount_home', total_net_billable_amount * flt(frm.doc.conversion_rate || 1));
        frm.set_value('expected_cash_amount', total_net_billable_amount);
        frm.set_value('expected_cash_amount_home', total_net_billable_amount * flt(frm.doc.conversion_rate || 1));
        frm.set_value('opening_cash_float_home', flt(frm.doc.opening_cash_float) * flt(frm.doc.conversion_rate || 1));
        frm.set_value('actual_cash_on_hand_home', flt(frm.doc.actual_cash_on_hand) * flt(frm.doc.conversion_rate || 1));
        frm.set_value('cash_over_short', flt(frm.doc.actual_cash_on_hand) - total_net_billable_amount);
        frm.set_value('cash_over_short_home', flt(frm.doc.cash_over_short) * flt(frm.doc.conversion_rate || 1));
    },
    actual_cash_on_hand(frm) { frm.trigger('recompute_totals'); },
    opening_cash_float(frm) { frm.trigger('recompute_totals'); }
});

frappe.ui.form.on('Shift Closing Line', {
    fuel_pump(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.fuel_nozzle) frappe.model.set_value(cdt, cdn, 'fuel_nozzle', '');
    },
    fuel_nozzle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        apply_nozzle_defaults(frm, cdt, cdn, row.fuel_nozzle);
    },
    closing_reading(frm, cdt, cdn) { update_closing_line(frm, cdt, cdn); },
    test_qty(frm, cdt, cdn) { update_closing_line(frm, cdt, cdn); },
    calibration_qty(frm, cdt, cdn) { update_closing_line(frm, cdt, cdn); },
    adjustment_qty(frm, cdt, cdn) { update_closing_line(frm, cdt, cdn); }
});
