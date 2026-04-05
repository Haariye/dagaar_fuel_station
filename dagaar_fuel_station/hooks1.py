app_name = "dagaar_fuel_station"
app_title = "Dagaar Fuel Station"
app_publisher = "OpenAI"
app_description = "Advanced nozzle, shift, billing, dashboard, and reports for ERPNext fuel stations"
app_email = "support@example.com"
app_license = "MIT"

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [[
            "name",
            "in",
            [
                "Sales Invoice-pump_reading_entry",
                "Sales Invoice-shift_closing_entry",
                "Sales Invoice-fuel_pump",
                "Sales Invoice-fuel_nozzle",
                "Sales Invoice-pos_profile_link",
                "Sales Invoice-fuel_station_date",
                "Sales Invoice Item-source_pump_reading_line",
                "Sales Invoice Item-source_shift_closing_line",
                "Sales Invoice Item-opening_meter_reading",
                "Sales Invoice Item-closing_meter_reading",
                "Sales Invoice Item-metered_qty",
                "Sales Invoice Item-allocated_qty",
                "Sales Invoice Item-fuel_pump",
                "Sales Invoice Item-fuel_nozzle"
            ]
        ]]
    }
]
