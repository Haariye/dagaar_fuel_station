
frappe.ui.form.on('Fuel Nozzle', {
    refresh(frm) {
        const is_system_manager = frappe.user_roles.includes('System Manager');
        const locked = cint(frm.doc.opening_reading_locked);
        frm.set_df_property('initial_opening_reading', 'read_only', !is_system_manager || locked);
        frm.set_df_property('opening_reading_locked', 'read_only', 1);
        if (locked) {
            frm.dashboard.set_headline(__('Initial opening reading is locked.'));
        }

        // Meter state and diagnostics buttons
        if (!frm.is_new()) {
            frm.add_custom_button(__('View Meter State'), function() {
                frappe.call({
                    method: 'dagaar_fuel_station.dagaar_fuel_station.nozzle_meter_state.get_nozzle_diagnostics',
                    args: { nozzle: frm.doc.name },
                    callback: function(r) {
                        if (!r.message || !r.message.length) {
                            frappe.msgprint(__('No meter ledger data yet. Click "Initialize Ledger" first, or run the Rebuild tool.'));
                            return;
                        }
                        const d = r.message[0];
                        let html = '<div style="font-size:13px">';
                        html += '<table class="table table-bordered">';
                        html += '<tr><td><strong>Current Reading</strong></td><td>' + d.current_reading + '</td></tr>';
                        html += '<tr><td><strong>Initial Opening</strong></td><td>' + d.initial_opening_reading + '</td></tr>';
                        html += '<tr><td><strong>Cumulative Sold Qty</strong></td><td>' + d.cumulative_sold_qty + '</td></tr>';
                        html += '<tr><td><strong>Expected Reading</strong></td><td>' + d.expected_reading + '</td></tr>';
                        html += '<tr><td><strong>Variance</strong></td><td class="' + (d.variance !== 0 ? 'text-danger' : 'text-success') + '">' + d.variance + '</td></tr>';
                        html += '<tr><td><strong>Last Entry Type</strong></td><td>' + (d.last_entry_type || '-') + '</td></tr>';
                        html += '<tr><td><strong>Last Source Doc</strong></td><td>' + (d.last_source_document || '-') + '</td></tr>';
                        html += '<tr><td><strong>Ledger Entries</strong></td><td>' + d.ledger_entry_count + '</td></tr>';
                        html += '</table>';

                        if (d.history && d.history.length) {
                            html += '<h6 style="margin-top:10px">Recent Ledger History (latest first)</h6>';
                            html += '<table class="table table-bordered table-condensed" style="font-size:11px">';
                            html += '<thead><tr><th>Type</th><th>Date</th><th>Prev</th><th>Open</th><th>Close</th><th>Sold</th><th>Cumul.</th><th>Variance</th><th>Source</th><th>Reason</th></tr></thead>';
                            html += '<tbody>';
                            d.history.forEach(h => {
                                html += '<tr>';
                                html += '<td>' + h.entry_type + '</td>';
                                html += '<td>' + (h.posting_date || '-') + '</td>';
                                html += '<td>' + h.previous_reading + '</td>';
                                html += '<td>' + h.opening_reading + '</td>';
                                html += '<td>' + h.closing_reading + '</td>';
                                html += '<td>' + h.sold_qty + '</td>';
                                html += '<td>' + h.cumulative_sold_qty + '</td>';
                                html += '<td>' + h.variance + '</td>';
                                html += '<td>' + (h.source_document || '-') + '</td>';
                                html += '<td>' + (h.reason || '-') + '</td>';
                                html += '</tr>';
                            });
                            html += '</tbody></table>';
                        }
                        html += '</div>';

                        frappe.msgprint({
                            title: __('Meter State – {0}', [frm.doc.nozzle_code || frm.doc.name]),
                            message: html,
                            indicator: 'blue',
                            wide: true
                        });
                    }
                });
            }, __('Meter'));

            if (is_system_manager) {
                frm.add_custom_button(__('Initialize Ledger'), function() {
                    frappe.confirm(
                        __('This will create the initial ledger entry for this nozzle if none exists. Continue?'),
                        function() {
                            frappe.call({
                                method: 'dagaar_fuel_station.dagaar_fuel_station.nozzle_meter_state.ensure_initial_entry',
                                args: { nozzle: frm.doc.name },
                                callback: function() {
                                    frappe.msgprint(__('Ledger initialized.'));
                                }
                            });
                        }
                    );
                }, __('Meter'));

                frm.add_custom_button(__('Rebuild Ledger'), function() {
                    frappe.confirm(
                        __('This will DELETE all ledger entries for this nozzle and rebuild from submitted Shift Closing Entries. This is irreversible. Continue?'),
                        function() {
                            frappe.call({
                                method: 'dagaar_fuel_station.dagaar_fuel_station.nozzle_meter_state.rebuild_nozzle_ledger',
                                args: { nozzle: frm.doc.name },
                                callback: function(r) {
                                    if (!r.message || !r.message.length) {
                                        frappe.msgprint(__('Rebuild completed.'));
                                        return;
                                    }
                                    const result = r.message[0];
                                    let msg = __('Rebuild complete for {0}', [result.nozzle]) + '<br>';
                                    msg += __('Entries replayed: {0}', [result.entries_replayed]) + '<br>';
                                    msg += __('Final reading: {0}', [result.final_reading]) + '<br>';
                                    msg += __('Cumulative sold: {0}', [result.final_cumulative_sold]) + '<br>';
                                    if (result.mismatch_count > 0) {
                                        msg += '<br><strong class="text-danger">' + __('Mismatches found: {0}', [result.mismatch_count]) + '</strong><br>';
                                        msg += '<table class="table table-bordered table-condensed" style="font-size:11px;margin-top:5px">';
                                        msg += '<thead><tr><th>Document</th><th>Expected Opening</th><th>Document Opening</th><th>Gap</th></tr></thead><tbody>';
                                        result.mismatches.forEach(m => {
                                            msg += '<tr><td>' + m.document + '</td><td>' + m.expected_opening + '</td><td>' + m.document_opening + '</td><td class="text-danger">' + m.gap + '</td></tr>';
                                        });
                                        msg += '</tbody></table>';
                                    } else {
                                        msg += '<br><strong class="text-success">' + __('No mismatches – meter continuity is clean.') + '</strong>';
                                    }
                                    frappe.msgprint({
                                        title: __('Rebuild Report'),
                                        message: msg,
                                        indicator: result.mismatch_count > 0 ? 'orange' : 'green',
                                        wide: true
                                    });
                                }
                            });
                        }
                    );
                }, __('Meter'));
            }
        }
    }
});
