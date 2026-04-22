// Fuel Customer Ledger – Dagaar Fuel Station
frappe.query_reports["Fuel Customer Ledger"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            default: frappe.defaults.get_user_default("Company"),
            reqd: 1,
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            reqd: 1,
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
            reqd: 1,
        },
        {
            fieldname: "party_type",
            label: __("Party Type"),
            fieldtype: "Link",
            options: "DocType",
            default: "Customer",
            reqd: 1,
            get_query: function () {
                return { filters: { "name": ["in", ["Customer", "Supplier"]] } };
            },
            on_change: function () {
                frappe.query_report.set_filter_value("party", "");
            },
        },
        {
            fieldname: "party",
            label: __("Party"),
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                if (!frappe.query_report.filters) return;
                let party_type = frappe.query_report.get_filter_value("party_type");
                if (!party_type) return;
                return frappe.db.get_link_options(party_type, txt);
            },
            on_change: function () {
                var party_type = frappe.query_report.get_filter_value("party_type");
                var parties = frappe.query_report.get_filter_value("party");
                if (!party_type || parties.length === 0 || parties.length > 1) {
                    frappe.query_report.set_filter_value("party_name", "");
                    return;
                }
                var party = parties[0];
                var fieldname = erpnext.utils.get_party_name(party_type) || "name";
                frappe.db.get_value(party_type, party, fieldname, function (value) {
                    frappe.query_report.set_filter_value("party_name", value[fieldname]);
                });
            },
        },
        {
            fieldname: "party_name",
            label: __("Party Name"),
            fieldtype: "Data",
            hidden: 1,
        },
        {
            fieldname: "cost_center",
            label: __("Cost Center"),
            fieldtype: "MultiSelectList",
            get_data: function (txt) {
                return frappe.db.get_link_options("Cost Center", txt, {
                    company: frappe.query_report.get_filter_value("company"),
                });
            },
        },
        {
            fieldname: "finance_book",
            label: __("Finance Book"),
            fieldtype: "Link",
            options: "Finance Book",
        },
        {
            fieldname: "presentation_currency",
            label: __("Currency"),
            fieldtype: "Select",
            options: erpnext.get_presentation_currency_list(),
        },
        {
            fieldname: "include_default_book_entries",
            label: __("Include Default FB Entries"),
            fieldtype: "Check",
            default: 1,
        },
        {
            fieldname: "show_net_values_in_party_account",
            label: __("Show Net Values in Party Account"),
            fieldtype: "Check",
        },
        {
            fieldname: "show_notes",
            label: __("Show Notes / Remarks Column"),
            fieldtype: "Check",
            default: 1,
        },
    ],
    onload: function(report) {
        report.page.add_inner_button(__('Download PDF Statement'), function() {
            var filters = report.get_values();
            frappe.call({
                method: 'dagaar_fuel_station.dagaar_fuel_station.report.fuel_customer_ledger.fuel_customer_ledger.generate_pdf',
                args: { filters: filters },
                freeze: true,
                freeze_message: __('Generating PDF Statement ...'),
                callback: function(r) {
                    if (r.message) {
                        window.open(
                            frappe.urllib.get_full_url(
                                '/api/method/dagaar_fuel_station.dagaar_fuel_station.report.fuel_customer_ledger.fuel_customer_ledger.download_pdf?token='
                                + encodeURIComponent(r.message)
                            )
                        );
                    }
                }
            });
        }).addClass('btn-primary');
    }
};
