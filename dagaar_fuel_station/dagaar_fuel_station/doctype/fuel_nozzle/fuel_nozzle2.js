
frappe.ui.form.on('Fuel Nozzle', {
    refresh(frm) {
        const is_system_manager = frappe.user_roles.includes('System Manager');
        const locked = cint(frm.doc.opening_reading_locked);
        frm.set_df_property('initial_opening_reading', 'read_only', !is_system_manager || locked);
        frm.set_df_property('opening_reading_locked', 'read_only', 1);
        if (locked) {
            frm.dashboard.set_headline(__('Initial opening reading is locked.'));
        }
    }
});
