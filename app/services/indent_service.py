# app/services/indent_service.py
from datetime import datetime
import traceback
from typing import Optional, Dict, List, Tuple, Any

import pandas as pd
import streamlit as st  # For type hinting @st.cache_data
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine, Connection


from app.core.logging import get_logger
from app.db.database_utils import fetch_data
from app.core.constants import (
    STATUS_SUBMITTED,
    STATUS_PROCESSING,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    ITEM_STATUS_PENDING_ISSUE,
    ITEM_STATUS_FULLY_ISSUED,
    ITEM_STATUS_PARTIALLY_ISSUED,
    ITEM_STATUS_CANCELLED_ITEM,
    TX_INDENT_FULFILL,
)
from app.services import item_service
from app.services import stock_service

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# INDENT (MATERIAL REQUEST NOTE - MRN) FUNCTIONS
# ─────────────────────────────────────────────────────────
def generate_mrn(engine: Engine) -> Optional[str]:
    """
    Generates a new Material Request Number (MRN) using a database sequence.
    Example: MRN-YYYYMM-NNNNN
    Args:
        engine: SQLAlchemy database engine instance.
    Returns:
        A string representing the new MRN, or None if generation fails.
    """
    if engine is None:
        logger.error("ERROR [indent_service.generate_mrn]: Database engine not available.")
        return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('mrn_seq');"))
            seq_num = result.scalar_one()
            return f"MRN-{datetime.now().strftime('%Y%m')}-{seq_num:05d}"
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [indent_service.generate_mrn]: Error generating MRN: %s. Sequence 'mrn_seq' might not exist or other DB error.\n%s",
            e,
            traceback.format_exc(),
        )
        return None


def create_indent(
    engine: Engine, indent_data: Dict[str, Any], items_data: List[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Creates a new indent (material request) and its associated items in the database.
    Args:
        engine: SQLAlchemy database engine instance.
        indent_data: Dictionary containing header details for the indent.
        items_data: List of dictionaries, each representing an item in the indent.
    Returns:
        A tuple (bool, str) indicating success status and a message.
    """
    if engine is None:
        return False, "Database engine not available."

    required_header_fields = ["mrn", "requested_by", "department", "date_required"]
    missing_or_empty_fields = [
        k
        for k in required_header_fields
        if not indent_data.get(k)
        or (isinstance(indent_data.get(k), str) and not indent_data.get(k).strip())
    ]
    if missing_or_empty_fields:
        return (
            False,
            f"Missing or empty required indent header fields: {', '.join(missing_or_empty_fields)}",
        )

    if not items_data:
        return False, "Indent must contain at least one item."

    for i, item in enumerate(items_data):
        try:
            qty_val = float(item.get("requested_qty", 0))
            if not item.get("item_id") or qty_val <= 0:
                return (
                    False,
                    f"Invalid data in item row {i+1}: Item ID missing or requested quantity is not positive.",
                )
        except (ValueError, TypeError):
            return False, f"Invalid numeric quantity for item in row {i+1}."

    indent_query_str = """
        INSERT INTO indents (mrn, requested_by, department, date_required, notes, status, date_submitted, created_at, updated_at)
        VALUES (:mrn, :requested_by, :department, :date_required, :notes, :status, NOW(), NOW(), NOW())
        RETURNING indent_id;
    """
    item_query_str = """
        INSERT INTO indent_items (indent_id, item_id, requested_qty, notes, item_status)
        VALUES (:indent_id, :item_id, :requested_qty, :notes, :item_status);
    """

    header_notes_value = indent_data.get("notes")
    cleaned_header_notes = None
    if isinstance(header_notes_value, str):
        cleaned_header_notes = header_notes_value.strip()
        if not cleaned_header_notes:
            cleaned_header_notes = None

    indent_params = {
        "mrn": indent_data["mrn"].strip(),
        "requested_by": indent_data["requested_by"].strip(),
        "department": indent_data["department"],
        "date_required": indent_data["date_required"],
        "notes": cleaned_header_notes,
        "status": indent_data.get("status", STATUS_SUBMITTED),
    }
    new_indent_id: Optional[int] = None
    try:
        with engine.connect() as connection:
            with connection.begin():
                result = connection.execute(text(indent_query_str), indent_params)
                new_indent_id = result.scalar_one_or_none()

                if not new_indent_id:
                    raise Exception(
                        "Failed to retrieve indent_id after indent header insertion."
                    )

                item_params_list_for_db: List[Dict[str, Any]] = []
                for item in items_data:
                    item_note_value = item.get("notes")
                    cleaned_item_note = None
                    if isinstance(item_note_value, str):
                        cleaned_item_note = item_note_value.strip()
                        if not cleaned_item_note:
                            cleaned_item_note = None

                    item_params_list_for_db.append(
                        {
                            "indent_id": new_indent_id,
                            "item_id": item["item_id"],
                            "requested_qty": float(item["requested_qty"]),
                            "notes": cleaned_item_note,
                            "item_status": ITEM_STATUS_PENDING_ISSUE,
                        }
                    )

                if item_params_list_for_db:
                    connection.execute(text(item_query_str), item_params_list_for_db)

        get_indents.clear()
        get_indents_for_processing.clear()
        return (
            True,
            f"Indent {indent_data['mrn']} created successfully with ID {new_indent_id}.",
        )
    except IntegrityError as e:
        error_msg = "Database integrity error creating indent."
        if "indents_mrn_key" in str(e).lower() or (
            "unique constraint" in str(e).lower() and "mrn" in str(e).lower()
        ):
            error_msg = (
                f"Failed to create indent: MRN '{indent_params['mrn']}' already exists."
            )
        elif "indent_items_item_id_fkey" in str(e).lower():
            error_msg = "Failed to create indent: One or more selected Item IDs are invalid or do not exist in the item master."
        logger.error(
            "ERROR [indent_service.create_indent]: %s Details: %s\n%s",
            error_msg,
            e,
            traceback.format_exc(),
        )
        return False, error_msg
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [indent_service.create_indent]: Database error creating indent: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return False, "A database error occurred while creating the indent."


@st.cache_data(ttl=120, show_spinner="Fetching indent list...")
def get_indents(
    _engine: Engine,
    mrn_filter: Optional[str] = None,
    dept_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    date_start_str: Optional[str] = None,
    date_end_str: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetches a list of indents based on specified filters.
    Assumes 'indents' table has 'processed_by_user_id', 'date_processed', 'created_at', 'updated_at'.
    Args:
        _engine: SQLAlchemy database engine instance.
        mrn_filter: Filter by MRN (case-insensitive, contains).
        dept_filter: Filter by department name.
        status_filter: Filter by indent status.
        date_start_str: Start date for submission date filter (YYYY-MM-DD).
        date_end_str: End date for submission date filter (YYYY-MM-DD).
    Returns:
        Pandas DataFrame of indents.
    """
    if _engine is None:
        logger.error("ERROR [indent_service.get_indents]: Database engine not available.")
        return pd.DataFrame()

    date_start_filter: Optional[date] = None
    date_end_filter: Optional[date] = None
    if date_start_str:
        try:
            date_start_filter = datetime.strptime(date_start_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(
                "WARNING [indent_service.get_indents]: Invalid start date format: %s. Ignoring.",
                date_start_str,
            )
    if date_end_str:
        try:
            date_end_filter = datetime.strptime(date_end_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(
                "WARNING [indent_service.get_indents]: Invalid end date format: %s. Ignoring.",
                date_end_str,
            )

    query_str = """
        SELECT 
            i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
            i.date_submitted, i.status, i.notes AS indent_notes, 
            i.processed_by_user_id, i.date_processed, 
            i.created_at, i.updated_at, 
            COUNT(ii.indent_item_id) AS item_count
        FROM indents i 
        LEFT JOIN indent_items ii ON i.indent_id = ii.indent_id 
        WHERE 1=1
    """
    params: Dict[str, Any] = {}
    if mrn_filter and mrn_filter.strip():
        query_str += " AND i.mrn ILIKE :mrn"
        params["mrn"] = f"%{mrn_filter.strip()}%"
    if dept_filter:
        query_str += " AND i.department = :department"
        params["department"] = dept_filter
    if status_filter:
        query_str += " AND i.status = :status"
        params["status"] = status_filter
    if date_start_filter:
        query_str += " AND DATE(i.date_submitted) >= :date_from"
        params["date_from"] = date_start_filter
    if date_end_filter:
        query_str += " AND DATE(i.date_submitted) <= :date_to"
        params["date_to"] = date_end_filter

    query_str += """
        GROUP BY i.indent_id, i.mrn, i.requested_by, i.department, i.date_required,
                 i.date_submitted, i.status, i.notes, 
                 i.processed_by_user_id, i.date_processed, 
                 i.created_at, i.updated_at
        ORDER BY i.date_submitted DESC, i.indent_id DESC;
    """
    df = fetch_data(_engine, query_str, params)
    if not df.empty:
        date_cols = [
            "date_required",
            "date_submitted",
            "date_processed",
            "created_at",
            "updated_at",
        ]
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        if "item_count" in df.columns:
            df["item_count"] = (
                pd.to_numeric(df["item_count"], errors="coerce").fillna(0).astype(int)
            )
    return df


@st.cache_data(ttl=120, show_spinner="Fetching indents to process...")
def get_indents_for_processing(_engine: Engine) -> pd.DataFrame:
    """
    Fetches indents that are in 'Submitted' or 'Processing' status.
    Args:
        _engine: SQLAlchemy database engine instance.
    Returns:
        Pandas DataFrame of indents suitable for processing.
    """
    if _engine is None:
        logger.error(
            "ERROR [indent_service.get_indents_for_processing]: Database engine not available."
        )
        return pd.DataFrame()

    query_str = """
        SELECT i.indent_id, i.mrn, i.department, i.requested_by,
               i.date_submitted, i.date_required, i.status
        FROM indents i
        WHERE i.status IN (:status_submitted, :status_processing)
        ORDER BY i.date_submitted ASC, i.mrn ASC;
    """
    params = {
        "status_submitted": STATUS_SUBMITTED,
        "status_processing": STATUS_PROCESSING,
    }
    df = fetch_data(_engine, query_str, params)
    if not df.empty:
        for col in ["date_required", "date_submitted"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def get_indent_items_for_display(engine: Engine, indent_id: int) -> pd.DataFrame:
    """
    Fetches line items for a specific indent, intended for display during processing.
    (This function is NOT CACHED, so no .clear() method is available)
    Args:
        engine: SQLAlchemy database engine instance.
        indent_id: The ID of the indent.
    Returns:
        Pandas DataFrame of indent items with stock details.
    """
    if engine is None or not indent_id:
        logger.error(
            "ERROR [indent_service.get_indent_items_for_display]: DB engine or indent_id missing."
        )
        return pd.DataFrame()

    query_str = """
        SELECT ii.indent_item_id, ii.item_id, i.name AS item_name, i.base_unit AS item_unit,
               i.current_stock AS stock_on_hand, ii.requested_qty,
               ii.issued_qty, ii.item_status, ii.notes AS item_notes
        FROM indent_items ii
        JOIN items i ON ii.item_id = i.item_id
        WHERE ii.indent_id = :indent_id
        ORDER BY i.name ASC;
    """
    params = {"indent_id": indent_id}
    df = fetch_data(engine, query_str, params)

    if not df.empty:
        for col in ["requested_qty", "issued_qty", "stock_on_hand"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        df["qty_remaining_to_issue"] = (df["requested_qty"] - df["issued_qty"]).clip(
            lower=0.0
        )

        if "item_status" in df.columns:
            df["item_status"] = df["item_status"].fillna(ITEM_STATUS_PENDING_ISSUE)
    else:
        df = pd.DataFrame(
            columns=[
                "indent_item_id",
                "item_id",
                "item_name",
                "item_unit",
                "stock_on_hand",
                "requested_qty",
                "issued_qty",
                "item_status",
                "item_notes",
                "qty_remaining_to_issue",
            ]
        )
    return df


def get_indent_details_for_pdf(
    engine: Engine, mrn: str
) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """
    Fetches detailed header and item information for an indent, formatted for PDF generation.
    Args:
        engine: SQLAlchemy database engine instance.
        mrn: The Material Request Number of the indent.
    Returns:
        Tuple (header_dict, list_of_item_dicts) or (None, None) if not found.
    """
    if engine is None or not mrn or not mrn.strip():
        logger.error(
            "ERROR [indent_service.get_indent_details_for_pdf]: Database engine or MRN not provided."
        )
        return None, None

    header_data: Optional[Dict[str, Any]] = None
    items_data: Optional[List[Dict[str, Any]]] = None

    try:
        with engine.connect() as connection:
            header_query = text(
                """
                SELECT ind.indent_id, ind.mrn, ind.department, ind.requested_by,
                       ind.date_submitted, ind.date_required, ind.status, ind.notes
                FROM indents ind WHERE ind.mrn = :mrn;
            """
            )
            header_result = (
                connection.execute(header_query, {"mrn": mrn.strip()})
                .mappings()
                .first()
            )

            if not header_result:
                logger.warning(
                    "WARNING [indent_service.get_indent_details_for_pdf]: Indent with MRN '%s' not found for PDF generation.",
                    mrn,
                )
                return None, None

            header_data = dict(header_result)
            if header_data.get("date_submitted") and pd.notna(
                header_data["date_submitted"]
            ):
                header_data["date_submitted"] = pd.to_datetime(
                    header_data["date_submitted"]
                ).strftime("%Y-%m-%d %H:%M")
            if header_data.get("date_required") and pd.notna(
                header_data["date_required"]
            ):
                header_data["date_required"] = pd.to_datetime(
                    header_data["date_required"]
                ).strftime("%Y-%m-%d")

            items_query = text(
                """
                SELECT ii.item_id, i.name AS item_name, i.base_unit AS item_unit,
                       COALESCE(i.category, 'Uncategorized') AS item_category,
                       COALESCE(i.sub_category, 'General') AS item_sub_category,
                       ii.requested_qty, ii.notes AS item_notes
                FROM indent_items ii
                JOIN items i ON ii.item_id = i.item_id
                JOIN indents ind ON ii.indent_id = ind.indent_id
                WHERE ind.mrn = :mrn
                ORDER BY item_category ASC, item_sub_category ASC, item_name ASC;
            """
            )
            items_result = (
                connection.execute(items_query, {"mrn": mrn.strip()}).mappings().all()
            )
            items_data = [dict(row) for row in items_result]

        return header_data, items_data
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [indent_service.get_indent_details_for_pdf]: Database error fetching details for indent PDF (MRN: %s): %s\n%s",
            mrn,
            e,
            traceback.format_exc(),
        )
        return None, None


def _update_indent_overall_status(
    connection: Connection, indent_id: int, new_status: str, user_id: str
) -> None:
    """
    Internal helper function to update the overall status of an indent within an existing transaction.
    Also updates updated_at timestamp and processing details if they exist.
    Args:
        connection: Active SQLAlchemy Connection object.
        indent_id: The ID of the indent.
        new_status: The new overall status for the indent.
        user_id: User ID performing the action.
    """
    update_indent_query = text(
        """
        UPDATE indents 
        SET status = :status, 
            processed_by_user_id = CASE WHEN :status IN (:completed_status, :cancelled_status, :processing_status) THEN :user_id ELSE processed_by_user_id END,
            date_processed = CASE WHEN :status IN (:completed_status, :cancelled_status, :processing_status) THEN NOW() ELSE date_processed END,
            updated_at = NOW()
        WHERE indent_id = :indent_id;
    """
    )
    connection.execute(
        update_indent_query,
        {
            "status": new_status,
            "user_id": user_id,
            "indent_id": indent_id,
            "completed_status": STATUS_COMPLETED,
            "cancelled_status": STATUS_CANCELLED,
            "processing_status": STATUS_PROCESSING,
        },
    )


def process_indent_issuance(
    engine: Engine,
    indent_id: int,
    items_to_issue: List[Dict[str, Any]],
    user_id: str,
    indent_mrn: str,
) -> Tuple[bool, str]:
    """
    Processes the issuance of items for an indent, updating stock and item statuses.
    Args:
        engine: SQLAlchemy database engine instance.
        indent_id: The ID of the indent being processed.
        items_to_issue: List of items with quantities to issue. Each dict should have
                        'indent_item_id', 'item_id', 'qty_to_issue_now'.
        user_id: User ID performing the issuance.
        indent_mrn: MRN of the indent, for logging in stock transactions.
    Returns:
        Tuple (success_status, message_string).
    """
    if engine is None:
        return False, "Database engine not available."
    if not all([indent_id, user_id, user_id.strip(), indent_mrn, indent_mrn.strip()]):
        return (
            False,
            "Missing or invalid required parameters: indent_id, user_id, or indent_mrn.",
        )

    processed_messages: List[str] = []
    any_actual_issuance_occurred = False

    try:
        with engine.connect() as connection:
            with connection.begin():
                for item_data in items_to_issue:
                    indent_item_id = item_data.get("indent_item_id")
                    item_id_from_data = item_data.get("item_id")
                    qty_to_issue_now = 0.0

                    if not indent_item_id or not item_id_from_data:
                        processed_messages.append(
                            f"Skipped item due to missing indent_item_id or item_id in data: {item_data}"
                        )
                        continue
                    try:
                        qty_to_issue_now = float(item_data.get("qty_to_issue_now", 0))
                    except (ValueError, TypeError):
                        processed_messages.append(
                            f"Skipped item ID {item_id_from_data}: Invalid quantity '{item_data.get('qty_to_issue_now')}'."
                        )
                        continue

                    if qty_to_issue_now <= 0:
                        continue

                    any_actual_issuance_occurred = True

                    current_item_details_query = text(
                        "SELECT requested_qty, issued_qty FROM indent_items WHERE indent_item_id = :indent_item_id FOR UPDATE;"
                    )
                    current_item_res = (
                        connection.execute(
                            current_item_details_query,
                            {"indent_item_id": indent_item_id},
                        )
                        .mappings()
                        .first()
                    )
                    if not current_item_res:
                        raise Exception(
                            f"Indent item ID {indent_item_id} (for item ID {item_id_from_data}) not found during processing."
                        )

                    current_requested_qty = float(current_item_res["requested_qty"])
                    current_issued_qty = float(current_item_res["issued_qty"])
                    qty_still_pending = current_requested_qty - current_issued_qty

                    if qty_still_pending <= 0:
                        processed_messages.append(
                            f"Item ID {item_id_from_data}: Already fulfilled. No further issuance."
                        )
                        continue

                    original_qty_to_issue_now_for_msg = qty_to_issue_now
                    if qty_to_issue_now > qty_still_pending:
                        qty_to_issue_now = qty_still_pending
                        processed_messages.append(
                            f"Item ID {item_id_from_data}: Issue quantity ({original_qty_to_issue_now_for_msg:.2f}) reduced to pending amount ({qty_to_issue_now:.2f})."
                        )

                    stock_on_hand_query = text(
                        "SELECT current_stock FROM items WHERE item_id = :item_id FOR UPDATE;"
                    )
                    stock_on_hand_res = connection.execute(
                        stock_on_hand_query, {"item_id": item_id_from_data}
                    ).scalar_one_or_none()
                    if stock_on_hand_res is None:
                        raise Exception(
                            f"Item ID {item_id_from_data} not found in items master for stock check."
                        )
                    stock_on_hand = float(stock_on_hand_res)

                    if qty_to_issue_now > stock_on_hand:
                        qty_to_issue_now = stock_on_hand
                        processed_messages.append(
                            f"Item ID {item_id_from_data}: Issue quantity ({original_qty_to_issue_now_for_msg:.2f}) further reduced to stock on hand ({qty_to_issue_now:.2f})."
                        )

                    if qty_to_issue_now <= 0:
                        processed_messages.append(
                            f"Item ID {item_id_from_data}: Skipped (no available stock or quantity became zero)."
                        )
                        continue

                    stock_tx_success = stock_service.record_stock_transaction(
                        item_id=item_id_from_data,
                        quantity_change=-qty_to_issue_now,
                        transaction_type=TX_INDENT_FULFILL,
                        user_id=user_id.strip(),
                        related_mrn=indent_mrn.strip(),
                        db_engine_param=None,
                        db_connection_param=connection,
                    )
                    if not stock_tx_success:
                        raise Exception(
                            f"Failed to record stock transaction for item_id {item_id_from_data} on MRN {indent_mrn}."
                        )

                    new_total_issued_for_item = current_issued_qty + qty_to_issue_now
                    new_item_status_for_item = ITEM_STATUS_PARTIALLY_ISSUED
                    if new_total_issued_for_item >= current_requested_qty:
                        new_item_status_for_item = ITEM_STATUS_FULLY_ISSUED
                        new_total_issued_for_item = current_requested_qty

                    update_indent_item_query = text(
                        """
                        UPDATE indent_items 
                        SET issued_qty = :issued_qty, item_status = :item_status 
                        WHERE indent_item_id = :indent_item_id;
                    """
                    )
                    connection.execute(
                        update_indent_item_query,
                        {
                            "issued_qty": new_total_issued_for_item,
                            "item_status": new_item_status_for_item,
                            "indent_item_id": indent_item_id,
                        },
                    )
                    processed_messages.append(
                        f"Item ID {item_id_from_data}: Issued {qty_to_issue_now:.2f}. New total issued: {new_total_issued_for_item:.2f}. Status: {new_item_status_for_item}."
                    )

                all_items_statuses_query = text(
                    "SELECT item_status FROM indent_items WHERE indent_id = :indent_id;"
                )
                item_statuses_results = connection.execute(
                    all_items_statuses_query, {"indent_id": indent_id}
                ).fetchall()

                all_statuses_list = (
                    [row[0] for row in item_statuses_results]
                    if item_statuses_results
                    else []
                )
                current_overall_indent_status = STATUS_PROCESSING

                if not all_statuses_list:
                    current_overall_indent_status = STATUS_SUBMITTED
                elif all(
                    s == ITEM_STATUS_FULLY_ISSUED or s == ITEM_STATUS_CANCELLED_ITEM
                    for s in all_statuses_list
                ):
                    current_overall_indent_status = STATUS_COMPLETED
                elif not any(
                    s == ITEM_STATUS_PENDING_ISSUE or s == ITEM_STATUS_PARTIALLY_ISSUED
                    for s in all_statuses_list
                ):
                    current_overall_indent_status = STATUS_COMPLETED

                if (
                    any_actual_issuance_occurred
                    or current_overall_indent_status == STATUS_COMPLETED
                    or not items_to_issue
                ):
                    current_db_indent_status_res = connection.execute(
                        text("SELECT status FROM indents WHERE indent_id = :indent_id"),
                        {"indent_id": indent_id},
                    ).scalar_one_or_none()
                    if (
                        current_db_indent_status_res != current_overall_indent_status
                        or any_actual_issuance_occurred
                    ):
                        _update_indent_overall_status(
                            connection,
                            indent_id,
                            current_overall_indent_status,
                            user_id.strip(),
                        )
                        processed_messages.append(
                            f"Indent MRN {indent_mrn} overall status is now: {current_overall_indent_status}."
                        )

                if not items_to_issue and not any_actual_issuance_occurred:
                    processed_messages.append(
                        f"No items were marked for issuance in MRN {indent_mrn} for this submission."
                    )
                elif not any_actual_issuance_occurred and items_to_issue:
                    processed_messages.append(
                        f"No actual stock was issued for MRN {indent_mrn} in this batch. Check item availability and pending quantities."
                    )

            item_service.get_all_items_with_stock.clear()
            stock_service.get_stock_transactions.clear()
            get_indents.clear()
            get_indents_for_processing.clear()

            final_message = "Indent processing complete."
            if processed_messages:
                final_message += " Details: " + " | ".join(processed_messages)
            return True, final_message

    except Exception as e:
        logger.error(
            "ERROR [indent_service.process_indent_issuance]: Exception during indent processing for MRN %s:\n%s",
            indent_mrn,
            traceback.format_exc(),
        )
        detailed_error_message = f"Error processing indent: {str(e)}."
        if processed_messages:
            detailed_error_message += " Partial processing messages: " + " | ".join(
                processed_messages
            )
        return False, detailed_error_message


def mark_indent_completed(
    engine: Engine, indent_id: int, user_id: str, indent_mrn: str
) -> Tuple[bool, str]:
    """
    Marks an entire indent as completed. Any remaining pending/partially issued items are marked as 'Item Cancelled'.
    Args:
        engine: SQLAlchemy database engine instance.
        indent_id: The ID of the indent.
        user_id: User ID performing the action.
        indent_mrn: MRN of the indent for messaging.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    if not all([indent_id, user_id, user_id.strip(), indent_mrn, indent_mrn.strip()]):
        return False, "Missing or invalid indent_id, user_id, or indent_mrn."

    try:
        with engine.connect() as connection:
            with connection.begin():
                update_pending_items_sql = text(
                    """
                    UPDATE indent_items 
                    SET item_status = :new_status 
                    WHERE indent_id = :indent_id AND item_status IN (:pending_status, :partial_status);
                """
                )
                connection.execute(
                    update_pending_items_sql,
                    {
                        "new_status": ITEM_STATUS_CANCELLED_ITEM,
                        "indent_id": indent_id,
                        "pending_status": ITEM_STATUS_PENDING_ISSUE,
                        "partial_status": ITEM_STATUS_PARTIALLY_ISSUED,
                    },
                )
                _update_indent_overall_status(
                    connection, indent_id, STATUS_COMPLETED, user_id.strip()
                )

        get_indents.clear()
        get_indents_for_processing.clear()
        return (
            True,
            f"Indent MRN {indent_mrn} successfully marked as {STATUS_COMPLETED}. Any remaining pending/partially issued items were marked as cancelled.",
        )
    except Exception as e:
        logger.error(
            "ERROR [indent_service.mark_indent_completed]: Error marking indent %s as completed: %s\n%s",
            indent_mrn,
            e,
            traceback.format_exc(),
        )
        return False, f"Error marking indent {indent_mrn} as completed: {str(e)}"


def cancel_entire_indent(
    engine: Engine, indent_id: int, user_id: str, indent_mrn: str
) -> Tuple[bool, str]:
    """
    Cancels an entire indent. Items not yet fully issued are marked as 'Item Cancelled'.
    Args:
        engine: SQLAlchemy database engine instance.
        indent_id: The ID of the indent.
        user_id: User ID performing the action.
        indent_mrn: MRN of the indent for messaging.
    Returns:
        Tuple (success_status, message).
    """
    if engine is None:
        return False, "Database engine not available."
    if not all([indent_id, user_id, user_id.strip(), indent_mrn, indent_mrn.strip()]):
        return False, "Missing or invalid indent_id, user_id, or indent_mrn."

    try:
        with engine.connect() as connection:
            with connection.begin():
                update_items_sql = text(
                    """
                    UPDATE indent_items 
                    SET item_status = :cancelled_item_status 
                    WHERE indent_id = :indent_id AND item_status != :fully_issued_status; 
                """
                )
                connection.execute(
                    update_items_sql,
                    {
                        "cancelled_item_status": ITEM_STATUS_CANCELLED_ITEM,
                        "indent_id": indent_id,
                        "fully_issued_status": ITEM_STATUS_FULLY_ISSUED,
                    },
                )

                _update_indent_overall_status(
                    connection, indent_id, STATUS_CANCELLED, user_id.strip()
                )

        get_indents.clear()
        get_indents_for_processing.clear()
        return (
            True,
            f"Indent MRN {indent_mrn} and its non-issued items successfully cancelled.",
        )
    except Exception as e:
        logger.error(
            "ERROR [indent_service.cancel_entire_indent]: Error cancelling indent %s: %s\n%s",
            indent_mrn,
            e,
            traceback.format_exc(),
        )
        return False, f"Error cancelling indent {indent_mrn}: {str(e)}"
