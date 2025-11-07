from sqlalchemy import inspect, text

from database import db


def ensure_schema():
    inspector = inspect(db.engine)

    _ensure_column(
        inspector=inspector,
        table='properties',
        column='capex_percent_of_noi',
        ddl='FLOAT DEFAULT 0.0'
    )
    _ensure_column(
        inspector=inspector,
        table='properties',
        column='use_manual_noi_capex',
        ddl='BOOLEAN DEFAULT 0'
    )
    _ensure_column(
        inspector=inspector,
        table='property_manual_cash_flows',
        column='month',
        ddl='INTEGER'
    )


def _ensure_column(inspector, table, column, ddl):
    try:
        columns = [col['name'] for col in inspector.get_columns(table)]
    except Exception:
        return

    if column in columns:
        return

    statement = text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}')
    db.session.execute(statement)
    db.session.commit()
