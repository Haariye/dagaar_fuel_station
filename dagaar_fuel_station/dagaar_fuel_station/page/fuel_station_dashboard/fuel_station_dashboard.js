frappe.pages['fuel-station-dashboard'].on_page_load = function(wrapper) {
	new DagaarFuelDashboard(wrapper);
};

class DagaarFuelDashboard {
	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __('Fuel Station Dashboard'),
			single_column: true
		});
		this.make_filters();
		this.body = $('<div class="fsd-root"></div>').appendTo(this.page.main);
		this.refresh();
	}

	make_filters() {
		this.page.add_field({
			label: __('Company'),
			fieldname: 'company',
			fieldtype: 'Link',
			options: 'Company',
			change: () => this.refresh()
		});
		this.page.add_field({
			label: __('POS Profile'),
			fieldname: 'pos_profile',
			fieldtype: 'Link',
			options: 'POS Profile',
			change: () => this.refresh()
		});
		this.page.add_field({
			label: __('From Date'),
			fieldname: 'from_date',
			fieldtype: 'Date',
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -6),
			change: () => this.refresh()
		});
		this.page.add_field({
			label: __('To Date'),
			fieldname: 'to_date',
			fieldtype: 'Date',
			default: frappe.datetime.get_today(),
			change: () => this.refresh()
		});
		this.page.set_primary_action(__('Refresh'), () => this.refresh(), 'refresh');
	}

	get_filters() {
		return {
			company: this.page.fields_dict.company.get_value(),
			pos_profile: this.page.fields_dict.pos_profile.get_value(),
			from_date: this.page.fields_dict.from_date.get_value(),
			to_date: this.page.fields_dict.to_date.get_value()
		};
	}

	refresh() {
		const filters = this.get_filters();
		frappe.call({
			method: 'dagaar_fuel_station.dagaar_fuel_station.dashboard.get_dashboard_data',
			args: filters,
			freeze: false,
			callback: (r) => this.render(r.message || {})
		});
	}

	card(title, value, sub) {
		return `<div class="fsd-card"><div class="fsd-kpi-title">${title}</div><div class="fsd-kpi-value">${value}</div><div class="fsd-kpi-sub">${sub || ''}</div></div>`;
	}

	render(data) {
		const s = data.summary || {};
		const stats = data.shift_stats || {};
		const filters = data.filters || {};
		this.body.html(`
			<div class="fsd-toolbar-note">${__('Range')}: <span class="fsd-badge">${frappe.datetime.str_to_user(filters.from_date || '')} → ${frappe.datetime.str_to_user(filters.to_date || '')}</span></div>
			<div class="fsd-grid fsd-cards">
				${this.card(__('Total Sales'), format_currency(s.total_amount || 0), __('Credit {0} | Cash {1}', [format_currency(s.total_credit_amount || 0), format_currency(s.total_cash_amount || 0)]))}
				${this.card(__('Billable Litres'), format_number(s.total_billable_qty || 0, null, 3), __('Metered {0}', [format_number(s.total_metered_qty || 0, null, 3)]))}
				${this.card(__('Credit Litres'), format_number(s.total_credit_qty || 0, null, 3), __('Cash {0}', [format_number(s.total_cash_qty || 0, null, 3)]))}
				${this.card(__('Cash Over / Short'), format_currency(s.cash_over_short || 0), __('Pump Entries {0} | Shift Closings {1}', [s.pump_entries || 0, stats.shift_closings || 0]))}
			</div>
			<div class="fsd-grid fsd-panels-2" style="margin-top:16px;">
				<div class="fsd-panel"><div class="fsd-panel-title"><h4>${__('Daily Sales Trend')}</h4><span class="fsd-mini">${__('Amount, cash and credit by day')}</span></div><div id="fsd-trend" class="fsd-chart"></div></div>
				<div class="fsd-panel"><div class="fsd-panel-title"><h4>${__('Sales Mix')}</h4><span class="fsd-mini">${__('Litres and amount split')}</span></div><div id="fsd-mix" class="fsd-chart-sm"></div><div class="fsd-mini" style="margin-top:10px;">${__('Active Nozzles')}: <b>${stats.active_nozzles || 0}</b> &nbsp;&nbsp; ${__('Attendants')}: <b>${stats.attendants || 0}</b></div></div>
			</div>
			<div class="fsd-grid fsd-panels-3" style="margin-top:16px;">
				<div class="fsd-panel"><div class="fsd-panel-title"><h4>${__('Top Nozzles')}</h4><span class="fsd-mini">${__('By litres')}</span></div>${this.table(data.top_nozzles || [], [
					{key:'fuel_nozzle', label: __('Nozzle')},
					{key:'liters', label: __('Litres'), num:1, fmt:(v)=>format_number(v||0,null,3)},
					{key:'amount', label: __('Amount'), num:1, fmt:(v)=>format_currency(v||0)}
				])}</div>
				<div class="fsd-panel"><div class="fsd-panel-title"><h4>${__('Top Credit Customers')}</h4><span class="fsd-mini">${__('By amount')}</span></div>${this.table(data.top_customers || [], [
					{key:'customer', label: __('Customer')},
					{key:'liters', label: __('Litres'), num:1, fmt:(v)=>format_number(v||0,null,3)},
					{key:'amount', label: __('Amount'), num:1, fmt:(v)=>format_currency(v||0)}
				])}</div>
				<div class="fsd-panel"><div class="fsd-panel-title"><h4>${__('Shift Performance')}</h4><span class="fsd-mini">${__('By shift')}</span></div>${this.table(data.shift_rows || [], [
					{key:'shift', label: __('Shift')},
					{key:'entries', label: __('Entries'), num:1},
					{key:'liters', label: __('Litres'), num:1, fmt:(v)=>format_number(v||0,null,3)},
					{key:'amount', label: __('Amount'), num:1, fmt:(v)=>format_currency(v||0)}
				])}</div>
			</div>
			<div class="fsd-grid" style="margin-top:16px;">
				<div class="fsd-panel"><div class="fsd-panel-title"><h4>${__('Station Summary')}</h4><span class="fsd-mini">${__('POS Profile wise performance')}</span></div>${this.table(data.station_rows || [], [
					{key:'pos_profile', label: __('POS Profile')},
					{key:'liters', label: __('Litres'), num:1, fmt:(v)=>format_number(v||0,null,3)},
					{key:'credit_amount', label: __('Credit'), num:1, fmt:(v)=>format_currency(v||0)},
					{key:'cash_amount', label: __('Cash'), num:1, fmt:(v)=>format_currency(v||0)},
					{key:'amount', label: __('Total'), num:1, fmt:(v)=>format_currency(v||0)}
				])}</div>
			</div>
		`);
		this.render_trend(data.daily_trend || []);
		this.render_mix(s);
	}

	table(rows, cols) {
		if (!rows.length) return `<div class="fsd-empty">${__('No data in this range')}</div>`;
		const head = cols.map(c => `<th class="${c.num ? 'num' : ''}">${c.label}</th>`).join('');
		const body = rows.map(row => `<tr>${cols.map(c => {
			const value = c.fmt ? c.fmt(row[c.key]) : frappe.utils.escape_html(row[c.key] || '');
			return `<td class="${c.num ? 'num' : ''}">${value}</td>`;
		}).join('')}</tr>`).join('');
		return `<table class="fsd-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
	}

	render_trend(rows) {
		const target = this.body.find('#fsd-trend').get(0);
		if (!target) return;
		$(target).empty();
		new frappe.Chart(target, {
			data: {
				labels: rows.map(d => frappe.datetime.str_to_user(d.date)),
				datasets: [
					{name: __('Total Sales'), values: rows.map(d => flt(d.amount || 0))},
					{name: __('Credit'), values: rows.map(d => flt(d.credit_amount || 0))},
					{name: __('Cash'), values: rows.map(d => flt(d.cash_amount || 0))}
				]
			},
			type: 'line',
			height: 280,
			lineOptions: {regionFill: 1},
			axisOptions: {xIsSeries: 1}
		});
	}

	render_mix(s) {
		const target = this.body.find('#fsd-mix').get(0);
		if (!target) return;
		$(target).empty();
		new frappe.Chart(target, {
			data: {
				labels: [__('Credit Amount'), __('Cash Amount'), __('Credit Litres'), __('Cash Litres')],
				datasets: [{values: [flt(s.total_credit_amount || 0), flt(s.total_cash_amount || 0), flt(s.total_credit_qty || 0), flt(s.total_cash_qty || 0)]}]
			},
			type: 'percentage',
			height: 240
		});
	}
}
