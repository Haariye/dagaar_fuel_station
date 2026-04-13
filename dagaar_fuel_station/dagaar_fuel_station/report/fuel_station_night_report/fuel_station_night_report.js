frappe.query_reports['Fuel Station Night Report'] = {
    filters: [
        {
            fieldname: 'from_date',
            label: __('From Date'),
            fieldtype: 'Date',
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: 'to_date',
            label: __('To Date'),
            fieldtype: 'Date',
            default: frappe.datetime.get_today(),
            reqd: 1
        },
        {
            fieldname: 'from_time',
            label: __('From Time'),
            fieldtype: 'Time',
            default: '00:00:00'
        },
        {
            fieldname: 'to_time',
            label: __('To Time'),
            fieldtype: 'Time',
            default: '23:59:59'
        },
        {
            fieldname: 'company',
            label: __('Company'),
            fieldtype: 'Link',
            options: 'Company',
            default: frappe.defaults.get_user_default('Company')
        },
        {
            fieldname: 'pos_profile',
            label: __('POS Profile / Station'),
            fieldtype: 'Link',
            options: 'POS Profile'
        },
        {
            fieldname: 'owner',
            label: __('Created By'),
            fieldtype: 'Link',
            options: 'User',
            default: 'All'
        }
    ],
    onload: function(report) {
        report.page.add_inner_button(__('Download Night PDF Report'), function() {
            var filters = report.get_values();
            frappe.call({
                method: 'dagaar_fuel_station.dagaar_fuel_station.report.fuel_station_night_report.fuel_station_night_report.generate_pdf',
                args: { filters: filters },
                freeze: true,
                freeze_message: __('Generating Night Report PDF ...'),
                callback: function(r) {
                    if (r.message) {
                        var w = window.open(
                            frappe.urllib.get_full_url(
                                '/api/method/dagaar_fuel_station.dagaar_fuel_station.report.fuel_station_night_report.fuel_station_night_report.download_pdf?token='
                                + encodeURIComponent(r.message)
                            )
                        );
                        if (!w) {
                            frappe.msgprint(__('Please allow pop-ups for this site.'));
                        }
                    }
                }
            });
        }).addClass('btn-primary');
    }
};
