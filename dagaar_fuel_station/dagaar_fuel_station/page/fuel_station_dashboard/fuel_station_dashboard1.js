frappe.pages['fuel-station-dashboard'].on_page_load = function(wrapper) {
	new FuelStationDashboard(wrapper);
};

class FuelStationDashboard {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __('Fuel Station Dashboard'),
			single_column: true
		});
		this.make();
	}

	make() {
		this.page.add_field({
			label: __('Company'),
			fieldname: 'company',
			fieldtype: 'Link',
			options: 'Company',
			change: () => this.refresh()
		});
		this.page.add_field({
			label: __('Date'),
			fieldname: 'date',
			fieldtype: 'Date',
			default: frappe.datetime.get_today(),
			change: () => this.refresh()
		});
		this.body = $('<div class="fuel-dashboard-root"></div>').appendTo(this.page.main);
		this.refresh();
	}

	refresh() {
		const company = this.page.fields_dict.company.get_value();
		const date = this.page.fields_dict.date.get_value();
		frappe.call({
			method: 'dagaar_fuel_station.dagaar_fuel_station.dashboard.get_dashboard_data',
			args: { company, date },
			callback: (r) => this.render(r.message || {})
		});
	}

	render(data) {
		const dailyBars = (data.daily || []).map(d => {
			const width = Math.max(8, Math.min(100, (d.amount || 0) / Math.max(1, ...((data.daily || []).map(x => x.amount || 0))) * 100));
			return `
				<div class="fuel-bar-row">
					<div class="label">${frappe.datetime.str_to_user(d.date)}</div>
					<div class="bar-wrap"><div class="bar" style="width:${width}%"></div></div>
					<div class="value">${format_currency(d.amount || 0)}</div>
				</div>`;
		}).join('');

		const nozzleRows = (data.top_nozzles || []).map(d => `
			<tr><td>${frappe.utils.escape_html(d.fuel_nozzle || '')}</td><td class="text-right">${format_number(d.liters || 0, null, 3)}</td></tr>
		`).join('');

		this.body.html(`
			<div class="fuel-dashboard-grid">
				<div class="fuel-card orange"><div class="big">${data.shift_closing_count || 0}</div><div class="small">Submitted Shift Closings</div></div>
				<div class="fuel-card blue"><div class="big">${format_currency(data.billed_amount || 0)}</div><div class="small">Billed Amount</div></div>
				<div class="fuel-card red"><div class="big">${format_currency(data.unpaid_credit || 0)}</div><div class="small">Unpaid Credit</div></div>
			</div>
			<div class="fuel-dashboard-grid bottom">
				<div class="fuel-panel">
					<h4>${__('7-Day Billing Trend')}</h4>
					${dailyBars || `<div class="text-muted">${__('No data')}</div>`}
				</div>
				<div class="fuel-panel">
					<h4>${__('Top Nozzles')}</h4>
					<table class="table table-bordered"><thead><tr><th>${__('Nozzle')}</th><th class="text-right">${__('Liters')}</th></tr></thead><tbody>${nozzleRows || `<tr><td colspan="2" class="text-muted">${__('No data')}</td></tr>`}</tbody></table>
				</div>
			</div>
		`);
	}
}
