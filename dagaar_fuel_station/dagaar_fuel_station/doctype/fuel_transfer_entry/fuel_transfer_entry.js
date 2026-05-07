frappe.ui.form.on("Fuel Transfer Entry", {
    setup(frm) {
        frm.set_query("pos_profile", () => ({ filters: { company: frm.doc.company || undefined } }));
    },
    company(frm) {
        if (frm.doc.company && !frm.doc.currency) {
            frappe.db.get_value("Company", frm.doc.company, "default_currency").then(r => {
                if (r.message && r.message.default_currency) {
                    frm.set_value("currency", r.message.default_currency);
                }
            });
        }
    }
});

frappe.ui.form.on("Fuel Transfer Line", {
    fuel_nozzle(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.fuel_nozzle) return;
        frappe.call({
            method: "dagaar_fuel_station.dagaar_fuel_station.doctype.fuel_transfer_entry.fuel_transfer_entry.get_nozzle_transfer_defaults",
            args: {
                nozzle: row.fuel_nozzle,
                pos_profile: frm.doc.pos_profile,
                currency: frm.doc.currency,
                company: frm.doc.company,
                posting_date: frm.doc.date
            },
            callback: function(r) {
                const d = r.message || {};
                frappe.model.set_value(cdt, cdn, "display_name", d.display_name || "");
                frappe.model.set_value(cdt, cdn, "fuel_pump", d.fuel_pump || "");
                frappe.model.set_value(cdt, cdn, "item", d.item || "");
                frappe.model.set_value(cdt, cdn, "uom", d.uom || "");
                frappe.model.set_value(cdt, cdn, "source_warehouse", d.source_warehouse || "");
                frappe.model.set_value(cdt, cdn, "cost_center", d.cost_center || "");
                frappe.model.set_value(cdt, cdn, "opening_reading", flt(d.opening_reading));
                frappe.model.set_value(cdt, cdn, "rate", flt(d.rate));
                frappe.model.set_value(cdt, cdn, "base_rate", flt(d.base_rate));
                const qty = flt(row.transfer_qty);
                frappe.model.set_value(cdt, cdn, "closing_reading", flt(d.opening_reading) + qty);
                frappe.model.set_value(cdt, cdn, "amount", qty * flt(d.rate));
                frappe.model.set_value(cdt, cdn, "amount_home", qty * flt(d.base_rate));
            }
        });
    },
    transfer_qty(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const qty = flt(row.transfer_qty);
        frappe.model.set_value(cdt, cdn, "closing_reading", flt(row.opening_reading) + qty);
        frappe.model.set_value(cdt, cdn, "amount", qty * flt(row.rate));
        frappe.model.set_value(cdt, cdn, "amount_home", qty * flt(row.base_rate));
    }
});
