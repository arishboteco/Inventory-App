# app/services/goods_receiving_service.py
from datetime import datetime
import traceback
from typing import Optional, Dict, List, Tuple, Any

import pandas as pd
from . import cache_data
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.engine import Engine

from ..core.logging import get_logger
from ..db.database_utils import fetch_data
from . import stock_service
from . import purchase_order_service
from ..core.constants import (
    TX_RECEIVING,
    PO_STATUS_PARTIALLY_RECEIVED,
    PO_STATUS_FULLY_RECEIVED,
    PO_STATUS_CANCELLED_PO,  # Use specific PO cancel status
)

logger = get_logger(__name__)


# ─────────────────────────────────────────────────────────
# GOODS RECEIVED NOTE (GRN) FUNCTIONS
# ─────────────────────────────────────────────────────────
def generate_grn_number(engine: Engine) -> Optional[str]:
    """
    Generates a new Goods Received Note (GRN) number using a database sequence.
    Args:
        engine: SQLAlchemy database engine instance.
    Returns:
        Formatted GRN number string or None on failure.
    """
    if engine is None:
        logger.error(
            "ERROR [goods_receiving_service.generate_grn_number]: Database engine not available."
        )
        return None
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT nextval('grn_sequence');"))
            seq_num = result.scalar_one()
            return f"GRN-{datetime.now().strftime('%Y%m')}-{seq_num:04d}"
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [goods_receiving_service.generate_grn_number]: Error generating GRN Number: %s\n%s",
            e,
            traceback.format_exc(),
        )
        return None


def create_grn(
    engine: Engine, grn_data: Dict[str, Any], items_received_data: List[Dict[str, Any]]
) -> Tuple[bool, str, Optional[int]]:
    """
    Creates a new Goods Received Note (GRN), updates stock, and PO status.
    Handles None or empty strings for notes fields.
    Args:
        engine: SQLAlchemy database engine instance.
        grn_data: Dictionary of GRN header details.
        items_received_data: List of dictionaries for items received.
    Returns:
        Tuple (success_status, message, new_grn_id).
    """
    if engine is None:
        return False, "Database engine not available.", None

    required_header = ["supplier_id", "received_date", "received_by_user_id"]
    missing_fields = [
        f
        for f in required_header
        if not grn_data.get(f)
        or (isinstance(grn_data.get(f), str) and not str(grn_data.get(f)).strip())
    ]
    if missing_fields:
        return (
            False,
            f"Missing or empty GRN header fields: {', '.join(missing_fields)}",
            None,
        )

    if not items_received_data:
        return False, "GRN must contain at least one received item.", None

    for i, item in enumerate(items_received_data):
        try:
            qty = float(item.get("quantity_received", 0))
            price = float(item.get("unit_price_at_receipt", 0))
            if not item.get("item_id") or qty <= 0 or price < 0:
                return (
                    False,
                    f"Invalid data in received item line {i+1}: Check Item ID, Quantity (>0), or Price (>=0).",
                    None,
                )
        except (ValueError, TypeError):
            return (
                False,
                f"Invalid numeric data for quantity/price in received item line {i+1}.",
                None,
            )

    new_grn_number = generate_grn_number(engine)
    if not new_grn_number:
        return False, "Failed to generate GRN Number.", None

    # Robust handling for GRN header notes
    header_notes_value = grn_data.get("notes")
    cleaned_header_notes = None
    if isinstance(header_notes_value, str):
        cleaned_header_notes = header_notes_value.strip()
        if not cleaned_header_notes:
            cleaned_header_notes = None

    # Assumes created_at column exists in goods_received_notes table.
    # If not, remove created_at and the corresponding NOW() from the query.
    header_q_obj = text(
        """INSERT INTO goods_received_notes 
                           (grn_number, po_id, supplier_id, received_date, notes, received_by_user_id, created_at)
                           VALUES (:grn_number, :po_id, :supplier_id, :received_date, :notes, :received_by_user_id, NOW()) 
                           RETURNING grn_id;"""
    )
    item_q_obj = text(
        """INSERT INTO grn_items 
                       (grn_id, item_id, po_item_id, quantity_ordered_on_po, quantity_received, unit_price_at_receipt, notes)
                       VALUES (:grn_id, :item_id, :po_item_id, :quantity_ordered_on_po, :quantity_received, :unit_price_at_receipt, :item_notes);"""
    )

    header_p = {
        "grn_number": new_grn_number,
        "po_id": grn_data.get("po_id"),
        "supplier_id": grn_data["supplier_id"],
        "received_date": grn_data["received_date"],
        "notes": cleaned_header_notes,  # Use cleaned header notes
        "received_by_user_id": grn_data["received_by_user_id"].strip(),
    }
    new_grn_id: Optional[int] = None

    try:
        with engine.connect() as conn:
            with conn.begin():
                res = conn.execute(header_q_obj, header_p)
                new_grn_id = res.scalar_one_or_none()
                if not new_grn_id:
                    raise Exception(
                        "Failed to retrieve grn_id after GRN header insertion."
                    )

                item_p_list_for_db: List[Dict[str, Any]] = []
                for item_d in items_received_data:
                    qty_rcv = float(item_d["quantity_received"])
                    price_rcv = float(item_d["unit_price_at_receipt"])

                    item_notes_val = item_d.get("item_notes")
                    cleaned_item_notes = None
                    if isinstance(item_notes_val, str):
                        cleaned_item_notes = item_notes_val.strip()
                        if not cleaned_item_notes:
                            cleaned_item_notes = None

                    item_p_list_for_db.append(
                        {
                            "grn_id": new_grn_id,
                            "item_id": item_d["item_id"],
                            "po_item_id": item_d.get("po_item_id"),
                            "quantity_ordered_on_po": item_d.get(
                                "quantity_ordered_on_po"
                            ),
                            "quantity_received": qty_rcv,
                            "unit_price_at_receipt": price_rcv,
                            "item_notes": cleaned_item_notes,
                        }
                    )

                    stock_ok = stock_service.record_stock_transaction(
                        item_id=item_d["item_id"],
                        quantity_change=qty_rcv,
                        transaction_type=TX_RECEIVING,
                        user_id=header_p["received_by_user_id"],
                        related_po_id=header_p["po_id"],
                        notes=f"GRN: {new_grn_number}",
                        db_engine_param=None,
                        db_connection_param=conn,
                    )
                    if not stock_ok:
                        raise Exception(
                            f"Failed to record stock transaction for item_id {item_d['item_id']} on GRN {new_grn_number}."
                        )

                if item_p_list_for_db:
                    conn.execute(item_q_obj, item_p_list_for_db)

                po_id_to_update = header_p["po_id"]
                if po_id_to_update:
                    po_items_query_str = "SELECT po_item_id, quantity_ordered FROM purchase_order_items WHERE po_id = :po_id"
                    po_items_df = fetch_data(
                        conn, po_items_query_str, {"po_id": po_id_to_update}
                    )

                    grn_items_sum_query_str = """SELECT po_item_id, SUM(quantity_received) as total_received 
                                               FROM grn_items gi
                                               JOIN goods_received_notes g ON gi.grn_id = g.grn_id 
                                               WHERE g.po_id = :po_id AND gi.po_item_id IS NOT NULL
                                               GROUP BY gi.po_item_id"""
                    grn_items_sum_df = fetch_data(
                        conn, grn_items_sum_query_str, {"po_id": po_id_to_update}
                    )

                    new_po_stat = PO_STATUS_PARTIALLY_RECEIVED
                    if not po_items_df.empty:
                        all_fulfilled = True
                        for _, po_row in po_items_df.iterrows():
                            po_item_id_val = po_row["po_item_id"]
                            ordered_qty = float(po_row["quantity_ordered"])
                            received_rows = grn_items_sum_df[
                                grn_items_sum_df["po_item_id"] == po_item_id_val
                            ]
                            total_rcv_for_item = (
                                float(received_rows.iloc[0]["total_received"])
                                if not received_rows.empty
                                else 0.0
                            )
                            if total_rcv_for_item < ordered_qty:
                                all_fulfilled = False
                                break
                        if all_fulfilled:
                            new_po_stat = PO_STATUS_FULLY_RECEIVED
                    else:
                        new_po_stat = PO_STATUS_FULLY_RECEIVED

                    # Default: Does not update 'updated_by_user_id' for PO
                    # If 'updated_by_user_id' exists in 'purchase_orders', modify query and params
                    update_po_q_obj = text(
                        """UPDATE purchase_orders 
                                              SET status = :status, updated_at = NOW() 
                                              WHERE po_id = :po_id AND status NOT IN (:fully_received, :cancelled);"""
                    )
                    update_po_params = {
                        "status": new_po_stat,
                        "po_id": po_id_to_update,
                        "fully_received": PO_STATUS_FULLY_RECEIVED,
                        "cancelled": PO_STATUS_CANCELLED_PO,
                    }
                    # If 'updated_by_user_id' exists in purchase_orders table:
                    # update_po_q_obj = text("""UPDATE purchase_orders
                    #                           SET status = :status, updated_at = NOW(), updated_by_user_id = :user_id
                    #                           WHERE po_id = :po_id AND status NOT IN (:fully_received, :cancelled);""")
                    # update_po_params["user_id"] = header_p['received_by_user_id']

                    conn.execute(update_po_q_obj, update_po_params)

                    purchase_order_service.list_pos.clear()
                    purchase_order_service.get_po_by_id.clear()

        list_grns.clear()
        return (
            True,
            f"GRN {new_grn_number} created successfully. Stock updated. PO status updated as applicable.",
            new_grn_id,
        )

    except IntegrityError as e:
        msg = "Database integrity error creating GRN."
        if "goods_received_notes_grn_number_key" in str(e).lower():
            msg = f"GRN Number '{new_grn_number}' conflict."
        logger.error(
            "ERROR [goods_receiving_service.create_grn]: %s Details: %s\n%s",
            msg,
            e,
            traceback.format_exc(),
        )
        return False, msg, None
    except Exception as e:
        logger.error(
            "ERROR [goods_receiving_service.create_grn]: Error during GRN creation for %s: %s\n%s",
            new_grn_number,
            e,
            traceback.format_exc(),
        )
        return False, f"An unexpected error occurred: {str(e)}", None


@cache_data(ttl=60)
def get_received_quantities_for_po(_engine: Engine, po_id: int) -> pd.DataFrame:
    """
    Fetches the total quantities already received for each line item of a specific PO.
    Args:
        _engine: SQLAlchemy database engine instance.
        po_id: The ID of the Purchase Order.
    Returns:
        Pandas DataFrame with 'po_item_id' and 'total_previously_received'.
    """
    if _engine is None or not po_id:
        logger.warning(
            "WARNING [goods_receiving_service.get_received_quantities_for_po]: Engine or PO ID not provided."
        )
        return pd.DataFrame(columns=["po_item_id", "total_previously_received"])

    query_string = """
        SELECT gi.po_item_id, SUM(gi.quantity_received) as total_previously_received
        FROM grn_items gi
        JOIN goods_received_notes g ON gi.grn_id = g.grn_id
        WHERE g.po_id = :po_id AND gi.po_item_id IS NOT NULL
        GROUP BY gi.po_item_id;
    """
    df = fetch_data(_engine, query_string, {"po_id": po_id})

    if "po_item_id" not in df.columns:
        df["po_item_id"] = pd.Series(dtype="Int64")
    if "total_previously_received" not in df.columns:
        df["total_previously_received"] = 0.0
    else:
        df["total_previously_received"] = pd.to_numeric(
            df["total_previously_received"], errors="coerce"
        ).fillna(0.0)
    return df


@cache_data(ttl=120, show_spinner="Fetching GRN list...")
def list_grns(
    _engine: Engine, filters: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    """
    Lists Goods Received Notes based on optional filters.
    Args:
        _engine: SQLAlchemy database engine instance.
        filters: Dictionary of filters to apply.
    Returns:
        Pandas DataFrame of GRNs.
    """
    if _engine is None:
        logger.error(
            "ERROR [goods_receiving_service.list_grns]: Database engine not available."
        )
        return pd.DataFrame()

    query_list_grn_str = """SELECT g.grn_id, g.grn_number, g.po_id, po.po_number, g.supplier_id, s.name AS supplier_name,
                               g.received_date, g.notes, g.received_by_user_id, g.created_at
                           FROM goods_received_notes g 
                           JOIN suppliers s ON g.supplier_id = s.supplier_id
                           LEFT JOIN purchase_orders po ON g.po_id = po.po_id 
                           WHERE 1=1"""
    params_list_grn: Dict[str, Any] = {}
    if filters:
        if filters.get("grn_number_ilike") and filters["grn_number_ilike"].strip():
            query_list_grn_str += " AND g.grn_number ILIKE :grn_number"
            params_list_grn["grn_number"] = f"%{filters['grn_number_ilike'].strip()}%"
        if filters.get("supplier_id"):
            query_list_grn_str += " AND g.supplier_id = :supplier_id"
            params_list_grn["supplier_id"] = filters["supplier_id"]
        if filters.get("po_number_ilike") and filters["po_number_ilike"].strip():
            query_list_grn_str += " AND po.po_number ILIKE :po_number"
            params_list_grn["po_number"] = f"%{filters['po_number_ilike'].strip()}%"

    query_list_grn_str += " ORDER BY g.received_date DESC, g.created_at DESC;"
    return fetch_data(_engine, query_list_grn_str, params_list_grn)


@cache_data(ttl=60, show_spinner="Fetching GRN details...")
def get_grn_details(_engine: Engine, grn_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches details for a specific GRN by its ID, including its line items.
    Args:
        _engine: SQLAlchemy database engine instance.
        grn_id: The ID of the GRN.
    Returns:
        Dictionary of GRN details with items, or None if not found.
    """
    if _engine is None or not grn_id:
        logger.error(
            "ERROR [goods_receiving_service.get_grn_details]: Database engine or GRN ID not provided."
        )
        return None

    grn_header_query_str = """SELECT g.grn_id, g.grn_number, g.po_id, po.po_number, g.supplier_id, s.name as supplier_name,
                                   g.received_date, g.notes, g.received_by_user_id, g.created_at
                               FROM goods_received_notes g 
                               JOIN suppliers s ON g.supplier_id = s.supplier_id
                               LEFT JOIN purchase_orders po ON g.po_id = po.po_id 
                               WHERE g.grn_id = :grn_id;"""
    grn_items_query_str = """SELECT gi.grn_item_id, gi.item_id, i.name as item_name, i.purchase_unit as item_unit,
                                   gi.po_item_id, gi.quantity_ordered_on_po, gi.quantity_received,
                                   gi.unit_price_at_receipt, gi.notes as item_notes
                               FROM grn_items gi
                               JOIN items i ON gi.item_id = i.item_id
                               WHERE gi.grn_id = :grn_id ORDER BY i.name;"""
    try:
        grn_header_df = fetch_data(_engine, grn_header_query_str, {"grn_id": grn_id})
        if grn_header_df.empty:
            logger.warning(
                "WARNING [goods_receiving_service.get_grn_details]: No GRN header found for grn_id %s.",
                grn_id,
            )
            return None

        grn_header = grn_header_df.iloc[0].to_dict()
        grn_items_df = fetch_data(_engine, grn_items_query_str, {"grn_id": grn_id})
        grn_header["items"] = grn_items_df.to_dict(orient="records")
        return grn_header
    except (SQLAlchemyError, Exception) as e:
        logger.error(
            "ERROR [goods_receiving_service.get_grn_details]: DB error fetching GRN details for grn_id %s: %s\n%s",
            grn_id,
            e,
            traceback.format_exc(),
        )
        return None
