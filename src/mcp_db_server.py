#!/usr/bin/env python3
"""
MCP Postgres Database Server
A Model Context Protocol server for database operations
"""
# server.py
from mcp.server.fastmcp import FastMCP
from urllib.parse import quote
import os
from sqlmodel import create_engine, Session
from dotenv import load_dotenv
import logging
from mcp.types import TextContent
import mcp.types as types
import argparse
import httpx
import uvicorn
from sqlalchemy.sql import text

# Load environment variables
load_dotenv()

# Create an MCP server
mcp = FastMCP("Postgres Server")

# Optional: configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# # Connect to a Database instance in Postgres Server
# @mcp.tool()
# def connect_database(dbhost: str, dbuser: str, dbpass: str, 
#                             dbname: str, application_name: str = "mcp-database-server") -> Session:
#         """Connect to PostgreSQL database"""
#         try:
#             # Create database URL
#             dburl = f"postgresql+psycopg2://{dbuser}:{quote(dbpass)}@{dbhost}/{dbname}?application_name={application_name}"
#             print(f"Database URL: {dburl}")  # Print the URL (optional)
#             # Create engine and session
#             engine = create_engine(dburl, pool_pre_ping=True, echo=False)
#             session = Session(bind=engine)
            
#             # Test connection
#             session.exec(text('SELECT 1'))
            
#             logger.info(f"Connected to database: {dbname} at {dbhost}")
#             return session
            
#         except Exception as e:
#             logger.error(f"Failed to connect to database: {e}")
#             session = None
#             engine = None
#             return None
        
# Global session object
session = None

@mcp.tool()
def connect_database(dbhost: str, dbuser: str, dbpass: str, 
                     dbname: str, application_name: str = "mcp-database-server") -> bool:
    """Connect to PostgreSQL database and initialize session."""
    global session
    try:
        dburl = f"postgresql+psycopg2://{dbuser}:{quote(dbpass)}@{dbhost}/{dbname}?application_name={application_name}"
        print(f"Database URL: {dburl}")
        engine = create_engine(dburl, pool_pre_ping=True, echo=False)
        session = Session(bind=engine)
        session.exec(text('SELECT 1'))  # Test the connection
        logger.info(f"Connected to database: {dbname} at {dbhost}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        session = None
        return False

@mcp.tool()
def get_order_details(email: str) -> list[dict]:
    """
    Fetch order details for a given customer email.
    First, retrieve the customer's ID, then fetch their orders.
    """
    global session
    connect_database('ep-misty-frog-a2lv3z65.eu-central-1.pg.koyeb.app','koyeb-adm','npg_8nNAxBMZfq4U','testpostgress')
    if session is None:
        logger.error("Database session not initialized.")
        return []

    try:
        # Step 1: Get customer ID from email
        customer_stmt = text("""
            SELECT customer_id FROM customers WHERE email = :email
        """)
        customer_result = session.exec(customer_stmt, params={"email": email}).first()

        if not customer_result:
            logger.warning(f"No customer found with email: {email}")
            return []

        customer_id = customer_result.customer_id

        # Step 2: Get order details
        order_stmt = text("""
            SELECT order_id, order_date, total_amount, status
            FROM orders
            WHERE customer_id = :customer_id
            ORDER BY order_date DESC
        """)
        result = session.exec(order_stmt, params={"customer_id": customer_id})

        orders = [
            {
                "order_id": row.order_id,
                "order_date": row.order_date.isoformat(),
                "total_amount": float(row.total_amount),
                "status": row.status
            }
            for row in result.fetchall()
        ]

        logger.info(f"Fetched {len(orders)} orders for email {email} (customer_id={customer_id})")
        return orders

    except Exception as e:
        logger.error(f"Failed to fetch orders for email {email}: {e}")
        return []

@mcp.tool()
def get_orders_by_status(status: str) -> list[dict]:
    """
    Fetch all orders with a given status.
    """
    global session
    if session is None:
        logger.error("Database session not initialized.")
        return []

    try:
        stmt = text("""
            SELECT order_id, customer_id, order_date, total_amount, status
            FROM orders
            WHERE status = :status
            ORDER BY order_date DESC
        """)
        result = session.exec(stmt, params={"status": status})

        orders = [
            {
                "order_id": row.order_id,
                "customer_id": row.customer_id,
                "order_date": row.order_date.isoformat(),
                "total_amount": float(row.total_amount),
                "status": row.status
            }
            for row in result.fetchall()
        ]

        logger.info(f"Fetched {len(orders)} orders with status '{status}'")
        return orders

    except Exception as e:
        logger.error(f"Error fetching orders by status '{status}': {e}")
        return []


@mcp.tool()
def update_order_date(order_id: int = None, status: str = None, new_date: str = None) -> str:
    """
    Update the order_date for an order by order_id or for all orders with a given status.
    new_date should be in 'YYYY-MM-DD' format.
    """
    global session
    if session is None:
        logger.error("Database session not initialized.")
        return "Database session is not initialized."

    if not new_date:
        return "new_date parameter is required in YYYY-MM-DD format."

    try:
        if order_id:
            stmt = text("""
                UPDATE orders
                SET order_date = :new_date
                WHERE order_id = :order_id
            """)
            result = session.exec(stmt, params={"new_date": new_date, "order_id": order_id})
            session.commit()
            return f"Updated order_date for order_id {order_id} to {new_date}"

        elif status:
            stmt = text("""
                UPDATE orders
                SET order_date = :new_date
                WHERE status = :status
            """)
            result = session.exec(stmt, params={"new_date": new_date, "status": status})
            session.commit()
            return f"Updated order_date to {new_date} for all orders with status '{status}'"

        else:
            return "Either order_id or status must be provided."

    except Exception as e:
        logger.error(f"Failed to update order date: {e}")
        return f"Error updating order date: {e}"

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run MCP Streamable HTTP based server")
    parser.add_argument("--port", type=int, default=8123, help="Localhost port to listen on")
    args = parser.parse_args()

    # Start the server with Streamable HTTP transport
    uvicorn.run(mcp.streamable_http_app, host="localhost", port=args.port)