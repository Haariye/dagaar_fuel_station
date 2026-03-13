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
