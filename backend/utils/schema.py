from sqlalchemy import inspect, text

from database import db
from sqlalchemy.exc import OperationalError


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
        table='portfolios',
        column='auto_refinance_enabled',
        ddl='BOOLEAN DEFAULT 0'
    )
    _ensure_column(
        inspector=inspector,
        table='portfolios',
        column='auto_refinance_spreads',
        ddl='TEXT'
    )
    _ensure_column(
        inspector=inspector,
        table='properties',
        column='market_value_start',
        ddl='FLOAT'
    )
    _ensure_column(
        inspector=inspector,
        table='property_manual_cash_flows',
        column='month',
        ddl='INTEGER'
    )
    _ensure_column(
        inspector=inspector,
        table='loans',
        column='interest_day_count',
        ddl="VARCHAR(20) DEFAULT '30/360'"
    )
    _ensure_properties_portfolio_unique()


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


def _ensure_properties_portfolio_unique():
    try:
        indexes = db.session.execute(text("PRAGMA index_list('properties')")).fetchall()
    except OperationalError:
        return

    needs_rebuild = False
    for idx in indexes:
        name = idx[1]
        unique = idx[2]
        origin = idx[3] if len(idx) > 3 else None
        if not unique or origin != 'u':
            continue
        cols = db.session.execute(text(f"PRAGMA index_info('{name}')")).fetchall()
        col_names = [col[2] for col in cols]
        if len(col_names) == 1 and col_names[0] == 'property_id':
            needs_rebuild = True
            break

    if needs_rebuild:
        _rebuild_properties_table()

    db.session.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_properties_portfolio_property_id "
        "ON properties (portfolio_id, property_id)"
    ))
    db.session.commit()


def _rebuild_properties_table():
    columns = [
        "id",
        "portfolio_id",
        "property_id",
        "property_name",
        "property_type",
        "address",
        "city",
        "state",
        "zip_code",
        "purchase_price",
        "purchase_date",
        "exit_date",
        "exit_cap_rate",
        "year_1_cap_rate",
        "building_size",
        "market_value_start",
        "noi_growth_rate",
        "initial_noi",
        "valuation_method",
        "ownership_percent",
        "capex_percent_of_noi",
        "use_manual_noi_capex",
        "created_at",
        "updated_at",
        "additional_data",
    ]
    column_list = ", ".join(columns)

    with db.engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=off"))
        conn.execute(text("ALTER TABLE properties RENAME TO properties_old"))
        conn.execute(text("""
            CREATE TABLE properties (
                id INTEGER PRIMARY KEY,
                portfolio_id INTEGER NOT NULL,
                property_id VARCHAR(100) NOT NULL,
                property_name VARCHAR(255) NOT NULL,
                property_type VARCHAR(100),
                address VARCHAR(500),
                city VARCHAR(100),
                state VARCHAR(50),
                zip_code VARCHAR(20),
                purchase_price FLOAT,
                purchase_date DATE,
                exit_date DATE,
                exit_cap_rate FLOAT,
                year_1_cap_rate FLOAT,
                building_size FLOAT,
                market_value_start FLOAT,
                noi_growth_rate FLOAT,
                initial_noi FLOAT,
                valuation_method VARCHAR(50),
                ownership_percent FLOAT DEFAULT 1.0,
                capex_percent_of_noi FLOAT DEFAULT 0.0,
                use_manual_noi_capex BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                additional_data TEXT,
                FOREIGN KEY(portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
            )
        """))
        conn.execute(text(f"""
            INSERT INTO properties ({column_list})
            SELECT {column_list} FROM properties_old
        """))
        conn.execute(text("DROP TABLE properties_old"))
        conn.execute(text("PRAGMA foreign_keys=on"))
