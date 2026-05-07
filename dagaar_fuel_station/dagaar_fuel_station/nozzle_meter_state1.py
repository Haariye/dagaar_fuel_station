
"""
Nozzle Meter State Engine
=========================
Single source of truth for per-nozzle meter continuity.

Architecture:
- One "current" row per nozzle in Nozzle Meter Ledger (is_current=1)
- Append-only ledger entries for full audit trail
- All state changes go through this module
- Submit creates a forward entry, Cancel creates a reversal entry

The current reading for any nozzle is always:
    initial_opening_reading + cumulative_confirmed_sold_qty

Variance is tracked when actual closing != expected closing.
"""

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, nowdate, nowtime


# ---------------------------------------------------------------------------
#  READ - get current nozzle state
# ---------------------------------------------------------------------------

def get_current_reading(nozzle):
    """Return the current confirmed meter reading for a nozzle.

    This is the ONLY function that should be used to get the next opening
    reading for any new document. It reads from the Nozzle Meter Ledger
    current-state row, NOT from any previous document lookup.

    Falls back to initial_opening_reading if no ledger entry exists yet.
    """
    if not nozzle:
        return 0

    row = _get_current_ledger_row(nozzle)
    if row:
        return flt(row.closing_reading)

    # No ledger row yet - return initial opening from Fuel Nozzle master
    return flt(frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading"))


def get_nozzle_state(nozzle):
    """Return full current state dict for a nozzle (for diagnostics)."""
    if not nozzle:
        return {}

    row = _get_current_ledger_row(nozzle)
    if row:
        return {
            "nozzle": nozzle,
            "current_reading": flt(row.closing_reading),
            "cumulative_sold_qty": flt(row.cumulative_sold_qty),
            "last_entry_type": row.entry_type,
            "last_source_document": row.source_document,
            "last_posting_date": str(row.posting_date) if row.posting_date else None,
            "sequence": row.sequence,
            "ledger_entry": row.name,
            "has_variance": flt(row.variance) != 0,
            "variance": flt(row.variance),
        }

    initial = flt(frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading"))
    return {
        "nozzle": nozzle,
        "current_reading": initial,
        "cumulative_sold_qty": 0,
        "last_entry_type": "Initial",
        "last_source_document": None,
        "last_posting_date": None,
        "sequence": 0,
        "ledger_entry": None,
        "has_variance": False,
        "variance": 0,
    }


def _get_current_ledger_row(nozzle):
    """Internal: fetch the is_current=1 row for a nozzle using raw SQL
    (works even if DocType metadata hasn't been synced yet)."""
    try:
        rows = frappe.db.sql(
            """
            select name, fuel_nozzle, closing_reading, cumulative_sold_qty,
                   entry_type, source_document, posting_date, `sequence`, variance
            from `tabNozzle Meter Ledger`
            where fuel_nozzle = %s and is_current = 1
            order by `sequence` desc
            limit 1
            """,
            nozzle,
            as_dict=True,
        )
        return rows[0] if rows else None
    except Exception:
        # Table doesn't exist yet
        return None


# ---------------------------------------------------------------------------
#  WRITE - record a shift closing (on_submit)
# ---------------------------------------------------------------------------

def record_shift_closing(shift_closing_entry_doc):
    """Called from ShiftClosingEntry.on_submit().

    For each nozzle line, appends a ledger entry and updates the current state.
    Uses SELECT ... FOR UPDATE to prevent race conditions.
    """
    for line in shift_closing_entry_doc.lines:
        if not line.fuel_nozzle:
            continue

        _append_ledger_entry(
            nozzle=line.fuel_nozzle,
            entry_type="Shift Close",
            source_doctype="Shift Closing Entry",
            source_document=shift_closing_entry_doc.name,
            source_line=line.name,
            posting_date=shift_closing_entry_doc.date,
            posting_time=shift_closing_entry_doc.posting_time,
            opening_reading=flt(line.opening_reading),
            closing_reading=flt(line.closing_reading),
            metered_qty=flt(line.metered_qty),
            sold_qty=flt(line.net_billable_qty),
        )


# ---------------------------------------------------------------------------
#  REVERSE - undo a shift closing (on_cancel)
# ---------------------------------------------------------------------------

def reverse_shift_closing(shift_closing_entry_doc):
    """Called from ShiftClosingEntry.on_cancel().

    For each nozzle line, creates a reversal entry that restores the
    previous state.
    """
    for line in shift_closing_entry_doc.lines:
        if not line.fuel_nozzle:
            continue

        # Find the ledger entry that was created by this submit
        original = None
        try:
            rows = frappe.db.sql(
                """
                select name, previous_reading, sold_qty, cumulative_sold_qty
                from `tabNozzle Meter Ledger`
                where fuel_nozzle = %s
                  and source_doctype = 'Shift Closing Entry'
                  and source_document = %s
                  and source_line = %s
                  and entry_type = 'Shift Close'
                limit 1
                """,
                (line.fuel_nozzle, shift_closing_entry_doc.name, line.name),
                as_dict=True,
            )
            original = rows[0] if rows else None
        except Exception:
            pass

        if not original:
            frappe.log_error(
                f"No ledger entry found for nozzle {line.fuel_nozzle} "
                f"from {shift_closing_entry_doc.name}",
                "Nozzle Meter Reversal Warning",
            )
            prev_reading = flt(line.opening_reading)
            sold_qty_to_reverse = flt(line.net_billable_qty)
        else:
            prev_reading = flt(original.previous_reading)
            sold_qty_to_reverse = flt(original.sold_qty)

        _append_ledger_entry(
            nozzle=line.fuel_nozzle,
            entry_type="Cancel Reversal",
            source_doctype="Shift Closing Entry",
            source_document=shift_closing_entry_doc.name,
            source_line=line.name,
            posting_date=shift_closing_entry_doc.date,
            posting_time=shift_closing_entry_doc.posting_time,
            opening_reading=None,   # Will be set from current state
            closing_reading=prev_reading,  # Restore to pre-submit reading
            metered_qty=0,
            sold_qty=-sold_qty_to_reverse,  # Negative reversal
            reason=f"Cancel of {shift_closing_entry_doc.name}",
        )


# ---------------------------------------------------------------------------
#  CORE APPEND - the only way to write to the ledger (uses raw SQL)
# ---------------------------------------------------------------------------

def _append_ledger_entry(
    nozzle,
    entry_type,
    source_doctype=None,
    source_document=None,
    source_line=None,
    posting_date=None,
    posting_time=None,
    opening_reading=None,
    closing_reading=None,
    metered_qty=None,
    sold_qty=0,
    reason=None,
    remarks=None,
):
    """Atomic append to the nozzle meter ledger.

    Uses raw SQL INSERT so it works both during migration (before DocType
    sync) and during normal operation. This is critical - frappe.new_doc()
    fails during bench migrate if the DocType JSON hasn't been synced yet.
    """
    posting_date = posting_date or nowdate()
    posting_time = posting_time or nowtime()

    # Step 1: Lock and read current state
    current = _lock_and_get_current(nozzle)

    if current:
        prev_reading = flt(current.closing_reading)
        prev_cumulative = flt(current.cumulative_sold_qty)
        prev_sequence = current.sequence or 0
    else:
        prev_reading = flt(
            frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading")
        )
        prev_cumulative = 0
        prev_sequence = 0

    # Step 2: Determine readings
    if opening_reading is None:
        opening_reading = prev_reading

    closing_reading = flt(closing_reading)

    # Step 3: Calculate cumulative and variance
    new_cumulative = prev_cumulative + flt(sold_qty)
    new_sequence = prev_sequence + 1

    initial_reading = flt(
        frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading")
    )
    expected_reading = initial_reading + new_cumulative

    if entry_type == "Cancel Reversal":
        variance = 0
    else:
        variance = flt(closing_reading) - flt(expected_reading)

    # Step 4: Create new ledger entry via RAW SQL
    now = now_datetime()
    entry_name = frappe.generate_hash(length=10)

    if metered_qty is None:
        metered_qty = closing_reading - flt(opening_reading)

    frappe.db.sql(
        """
        insert into `tabNozzle Meter Ledger`
            (name, creation, modified, modified_by, owner, docstatus, idx,
             fuel_nozzle, posting_date, posting_time, `sequence`,
             entry_type, source_doctype, source_document, source_line,
             previous_reading, opening_reading, closing_reading,
             metered_qty, sold_qty, cumulative_sold_qty,
             is_current, variance, reason, remarks)
        values
            (%s, %s, %s, %s, %s, 0, 0,
             %s, %s, %s, %s,
             %s, %s, %s, %s,
             %s, %s, %s,
             %s, %s, %s,
             1, %s, %s, %s)
        """,
        (
            entry_name, now, now, "Administrator", "Administrator",
            nozzle, posting_date, posting_time, new_sequence,
            entry_type, source_doctype, source_document, source_line,
            prev_reading, flt(opening_reading), closing_reading,
            flt(metered_qty), flt(sold_qty), new_cumulative,
            variance, reason, remarks,
        ),
    )

    # Step 5: Unmark old current row
    if current:
        frappe.db.sql(
            """
            update `tabNozzle Meter Ledger`
            set is_current = 0, modified = %s
            where name = %s
            """,
            (now, current.name),
        )

    return entry_name


def _lock_and_get_current(nozzle):
    """SELECT ... FOR UPDATE on the current ledger row to prevent race conditions."""
    try:
        rows = frappe.db.sql(
            """
            select name, closing_reading, cumulative_sold_qty, `sequence`
            from `tabNozzle Meter Ledger`
            where fuel_nozzle = %s and is_current = 1
            order by `sequence` desc
            limit 1
            for update
            """,
            nozzle,
            as_dict=True,
        )
        return rows[0] if rows else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
#  INITIALIZE - create initial ledger entry for a nozzle
# ---------------------------------------------------------------------------

@frappe.whitelist()
def ensure_initial_entry(nozzle):
    """Create the initial ledger entry for a nozzle if none exists.

    Safe to call multiple times - skips if any ledger entry exists.
    """
    if not nozzle:
        return

    try:
        count = frappe.db.sql(
            "select count(*) from `tabNozzle Meter Ledger` where fuel_nozzle = %s",
            nozzle,
        )[0][0]
        if count > 0:
            return
    except Exception:
        return

    initial = flt(frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading"))

    _append_ledger_entry(
        nozzle=nozzle,
        entry_type="Initial",
        posting_date=nowdate(),
        opening_reading=initial,
        closing_reading=initial,
        metered_qty=0,
        sold_qty=0,
        reason="Initial meter registration",
    )


# ---------------------------------------------------------------------------
#  REBUILD - regenerate ledger from historical submitted documents
# ---------------------------------------------------------------------------

@frappe.whitelist()
def rebuild_nozzle_ledger(nozzle=None):
    """Rebuild the meter ledger for one or all nozzles from historical data.

    This reads all submitted Shift Closing Entries in chronological order
    and replays them to reconstruct the ledger.

    Returns a report of what was rebuilt.
    """
    frappe.only_for("System Manager")

    if nozzle:
        nozzles = [nozzle]
    else:
        nozzles = [d.name for d in frappe.get_all("Fuel Nozzle", filters={"active": 1})]

    report = []

    for noz in nozzles:
        result = _rebuild_single_nozzle(noz)
        report.append(result)

    frappe.db.commit()
    return report


def _rebuild_single_nozzle(nozzle):
    """Delete all ledger entries for a nozzle and replay from history."""
    # Delete existing ledger entries
    frappe.db.sql(
        "delete from `tabNozzle Meter Ledger` where fuel_nozzle = %s", nozzle
    )

    initial = flt(frappe.db.get_value("Fuel Nozzle", nozzle, "initial_opening_reading"))

    # Get all submitted shift closing lines for this nozzle, in chronological order
    lines = frappe.db.sql(
        """
        select
            scl.name as line_name,
            scl.opening_reading,
            scl.closing_reading,
            scl.metered_qty,
            scl.net_billable_qty,
            sce.name as sce_name,
            sce.date as posting_date,
            sce.posting_time,
            sce.creation as sce_creation
        from `tabShift Closing Line` scl
        inner join `tabShift Closing Entry` sce on sce.name = scl.parent
        where sce.docstatus = 1 and scl.fuel_nozzle = %s
        order by sce.date asc, sce.posting_time asc, sce.creation asc
        """,
        nozzle,
        as_dict=True,
    )

    # Create initial entry
    _append_ledger_entry(
        nozzle=nozzle,
        entry_type="Initial",
        posting_date=nowdate(),
        opening_reading=initial,
        closing_reading=initial,
        metered_qty=0,
        sold_qty=0,
        reason="Rebuild: initial",
    )

    mismatches = []
    for line in lines:
        current_state = get_current_reading(nozzle)
        doc_opening = flt(line.opening_reading)

        if abs(current_state - doc_opening) > 0.001:
            mismatches.append({
                "document": line.sce_name,
                "line": line.line_name,
                "expected_opening": current_state,
                "document_opening": doc_opening,
                "gap": flt(doc_opening - current_state),
            })

        _append_ledger_entry(
            nozzle=nozzle,
            entry_type="Rebuild",
            source_doctype="Shift Closing Entry",
            source_document=line.sce_name,
            source_line=line.line_name,
            posting_date=line.posting_date,
            posting_time=line.posting_time,
            opening_reading=doc_opening,
            closing_reading=flt(line.closing_reading),
            metered_qty=flt(line.metered_qty),
            sold_qty=flt(line.net_billable_qty),
            reason="Rebuild: replayed from history",
        )

    final_state = get_nozzle_state(nozzle)

    return {
        "nozzle": nozzle,
        "initial_reading": initial,
        "entries_replayed": len(lines),
        "final_reading": final_state.get("current_reading"),
        "final_cumulative_sold": final_state.get("cumulative_sold_qty"),
        "mismatches": mismatches,
        "mismatch_count": len(mismatches),
    }


# ---------------------------------------------------------------------------
#  DIAGNOSTICS - per-nozzle health check
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_nozzle_diagnostics(nozzle=None):
    """Return diagnostic data for one or all nozzles."""
    frappe.only_for(["System Manager", "Sales Manager"])

    if nozzle:
        nozzles = [nozzle]
    else:
        nozzles = [d.name for d in frappe.get_all("Fuel Nozzle", filters={"active": 1}, order_by="name asc")]

    results = []
    for noz in nozzles:
        initial = flt(frappe.db.get_value("Fuel Nozzle", noz, "initial_opening_reading"))
        state = get_nozzle_state(noz)

        expected = initial + flt(state.get("cumulative_sold_qty"))
        actual = flt(state.get("current_reading"))

        history = []
        try:
            history = frappe.db.sql(
                """
                select name, entry_type, posting_date, source_document, source_line,
                       previous_reading, opening_reading, closing_reading,
                       metered_qty, sold_qty, cumulative_sold_qty, variance, reason
                from `tabNozzle Meter Ledger`
                where fuel_nozzle = %s
                order by `sequence` desc
                limit 10
                """,
                noz,
                as_dict=True,
            )
        except Exception:
            pass

        ledger_count = 0
        try:
            ledger_count = frappe.db.sql(
                "select count(*) from `tabNozzle Meter Ledger` where fuel_nozzle = %s",
                noz,
            )[0][0]
        except Exception:
            pass

        results.append({
            "nozzle": noz,
            "initial_opening_reading": initial,
            "current_reading": actual,
            "cumulative_sold_qty": flt(state.get("cumulative_sold_qty")),
            "expected_reading": expected,
            "variance": flt(actual - expected),
            "last_entry_type": state.get("last_entry_type"),
            "last_source_document": state.get("last_source_document"),
            "ledger_entry_count": ledger_count,
            "history": history,
        })

    return results


@frappe.whitelist()
def get_shift_diagnostics(shift_closing_entry):
    """Return per-line diagnostics for a specific Shift Closing Entry."""
    frappe.only_for(["System Manager", "Sales Manager"])

    doc = frappe.get_doc("Shift Closing Entry", shift_closing_entry)
    results = []

    for line in doc.lines:
        if not line.fuel_nozzle:
            continue

        ledger_reading = get_current_reading(line.fuel_nozzle)
        state = get_nozzle_state(line.fuel_nozzle)

        results.append({
            "nozzle": line.fuel_nozzle,
            "display_name": line.display_name,
            "ledger_current_reading": ledger_reading,
            "document_opening_reading": flt(line.opening_reading),
            "opening_match": abs(ledger_reading - flt(line.opening_reading)) < 0.001,
            "document_closing_reading": flt(line.closing_reading),
            "document_metered_qty": flt(line.metered_qty),
            "document_sold_qty": flt(line.net_billable_qty),
            "cumulative_sold_qty": flt(state.get("cumulative_sold_qty")),
            "last_source_document": state.get("last_source_document"),
            "last_entry_type": state.get("last_entry_type"),
        })

    return results
