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
