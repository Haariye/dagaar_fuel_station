
"""
Migration patch: Create Nozzle Meter Ledger table and rebuild from history.

Run via: bench run-patch dagaar_fuel_station.patches.create_nozzle_meter_ledger
Or automatically on bench migrate.
"""

import frappe


def execute():
    _ensure_table()
    _rebuild_all()


def _ensure_table():
    """Create the table if it doesn't exist. Safe to run multiple times."""
    try:
        frappe.db.sql("""
            CREATE TABLE IF NOT EXISTS `tabNozzle Meter Ledger` (
                `name` varchar(140) NOT NULL,
                `creation` datetime(6) DEFAULT NULL,
                `modified` datetime(6) DEFAULT NULL,
                `modified_by` varchar(140) DEFAULT NULL,
                `owner` varchar(140) DEFAULT NULL,
                `docstatus` int(1) NOT NULL DEFAULT 0,
                `idx` int(8) NOT NULL DEFAULT 0,
                `fuel_nozzle` varchar(140) DEFAULT NULL,
                `posting_date` date DEFAULT NULL,
                `posting_time` time(6) DEFAULT NULL,
                `sequence` int(11) DEFAULT 0,
                `entry_type` varchar(140) DEFAULT NULL,
                `source_doctype` varchar(140) DEFAULT NULL,
                `source_document` varchar(140) DEFAULT NULL,
                `source_line` varchar(140) DEFAULT NULL,
                `previous_reading` decimal(21,9) DEFAULT 0,
                `opening_reading` decimal(21,9) DEFAULT 0,
                `closing_reading` decimal(21,9) DEFAULT 0,
                `metered_qty` decimal(21,9) DEFAULT 0,
                `sold_qty` decimal(21,9) DEFAULT 0,
                `cumulative_sold_qty` decimal(21,9) DEFAULT 0,
                `is_current` int(1) DEFAULT 0,
                `variance` decimal(21,9) DEFAULT 0,
                `reason` varchar(140) DEFAULT NULL,
                `remarks` text DEFAULT NULL,
                `_user_tags` text DEFAULT NULL,
                `_comments` text DEFAULT NULL,
                `_assign` text DEFAULT NULL,
                `_liked_by` text DEFAULT NULL,
                PRIMARY KEY (`name`),
                KEY `fuel_nozzle` (`fuel_nozzle`),
                KEY `is_current` (`is_current`),
                KEY `source_document` (`source_document`),
                KEY `posting_date` (`posting_date`),
                KEY `nozzle_current` (`fuel_nozzle`, `is_current`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
    except Exception:
        # Table already exists — that's fine
        pass

    frappe.db.commit()


def _rebuild_all():
    """Rebuild the ledger for every active nozzle from submitted history."""
    nozzles = frappe.db.sql(
        "select name from `tabFuel Nozzle` where active = 1",
        as_dict=True,
    )
    if not nozzles:
        return

    from dagaar_fuel_station.dagaar_fuel_station.nozzle_meter_state import (
        _rebuild_single_nozzle,
    )

    total_mismatches = 0
    for row in nozzles:
        result = _rebuild_single_nozzle(row.name)
        total_mismatches += result.get("mismatch_count", 0)
        if result.get("mismatch_count"):
            frappe.log_error(
                f"Nozzle {row.name}: {result['mismatch_count']} mismatches during rebuild.\n"
                f"Details: {result.get('mismatches')}",
                "Nozzle Meter Ledger Migration",
            )

    frappe.db.commit()

    msg = f"Nozzle Meter Ledger: {len(nozzles)} nozzles rebuilt."
    if total_mismatches:
        msg += f" WARNING: {total_mismatches} mismatches. Check Error Log."
    print(msg)
