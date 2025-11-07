from __future__ import annotations

from collections import defaultdict
from datetime import date
from io import BytesIO
from typing import Dict, List, Tuple

from openpyxl import Workbook
from openpyxl.styles import Font

from database import db
from models import CashFlow, Loan, Portfolio, Property


def build_cash_flow_report(portfolio_id: int) -> BytesIO:
    portfolio = Portfolio.query.get_or_404(portfolio_id)

    properties: List[Property] = (
        Property.query.filter_by(portfolio_id=portfolio_id).all()
    )
    property_map: Dict[int, Property] = {prop.id: prop for prop in properties}
    ownership_lookup = _prepare_ownership_lookup(properties)

    loans: List[Loan] = Loan.query.filter_by(portfolio_id=portfolio_id).all()
    loan_map: Dict[int, Loan] = {loan.id: loan for loan in loans}

    cash_flows: List[CashFlow] = (
        CashFlow.query.filter_by(portfolio_id=portfolio_id)
        .order_by(CashFlow.date)
        .all()
    )

    type_set = set()
    aggregate_by_date: Dict[date, dict] = {}
    property_rows: List[dict] = []
    property_rows_ownership: List[dict] = []

    for cf in cash_flows:
        cf_date = cf.date
        cf_type = cf.cash_flow_type or 'Uncategorized'
        type_set.add(cf_type)

        base_amount = cf.amount or 0.0
        property_id = cf.property_id

        if property_id and property_id in property_map:
            ownership_percent = _ownership_percent(
                ownership_lookup[property_id],
                cf_date,
                default=property_map[property_id].ownership_percent or 1.0
            )
        else:
            ownership_percent = 1.0

        ownership_amount = base_amount * ownership_percent if property_id else base_amount

        date_entry = aggregate_by_date.setdefault(
            cf_date,
            {
                'date': cf_date,
                'total': 0.0,
                'total_ownership': 0.0,
                'type_totals': defaultdict(float),
                'type_totals_ownership': defaultdict(float),
            },
        )
        date_entry['total'] += base_amount
        date_entry['total_ownership'] += ownership_amount
        date_entry['type_totals'][cf_type] += base_amount
        date_entry['type_totals_ownership'][cf_type] += ownership_amount

        property_label, loan_label = _resolve_labels(property_map, loan_map, cf)
        property_rows.append(
            {
                'property': property_label,
                'date': cf_date,
                'loan': loan_label,
                'type': cf_type,
                'amount': base_amount,
                'description': cf.description or '',
            }
        )
        property_rows_ownership.append(
            {
                'property': property_label,
                'date': cf_date,
                'loan': loan_label,
                'type': cf_type,
                'amount': ownership_amount,
                'description': cf.description or '',
            }
        )

    workbook = Workbook()
    type_headers = sorted(type_set)

    _build_aggregate_sheet(
        workbook.active,
        title='Fund Aggregate 100%',
        aggregate_by_date=aggregate_by_date,
        type_headers=type_headers,
        beginning_cash=portfolio.beginning_cash or 0.0,
        ownership=False,
    )

    sheet2 = workbook.create_sheet('Fund Aggregate Ownership')
    _build_aggregate_sheet(
        sheet2,
        title='Fund Aggregate Ownership',
        aggregate_by_date=aggregate_by_date,
        type_headers=type_headers,
        beginning_cash=portfolio.beginning_cash or 0.0,
        ownership=True,
    )

    sheet3 = workbook.create_sheet('Property Detail 100%')
    _build_property_sheet(sheet3, property_rows)

    sheet4 = workbook.create_sheet('Property Detail Ownership')
    _build_property_sheet(sheet4, property_rows_ownership)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def _build_aggregate_sheet(ws, title, aggregate_by_date, type_headers, beginning_cash, ownership=False):
    ws.title = title
    header = ['Date', 'Beginning Cash', 'Total', 'Ending Cash'] + type_headers
    ws.append(header)
    ws.row_dimensions[1].font = Font(bold=True)

    running_cash_100 = beginning_cash
    running_cash_own = beginning_cash
    sorted_dates = sorted(aggregate_by_date.keys())

    for cf_date in sorted_dates:
        entry = aggregate_by_date[cf_date]
        total = entry['total']
        total_ownership = entry['total_ownership']

        total_used = total_ownership if ownership else total
        running_begin = running_cash_own if ownership else running_cash_100
        running_end = running_begin + total_used

        row = [
            cf_date.isoformat(),
            round(running_begin),
            round(total_used),
            round(running_end),
        ]

        type_totals = entry['type_totals_ownership'] if ownership else entry['type_totals']
        for type_name in type_headers:
            row.append(round(type_totals.get(type_name, 0.0)))

        ws.append(row)

        if ownership:
            running_cash_own = running_end
        else:
            running_cash_100 = running_end

    for column_cells in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max_len + 2, 40)


def _build_property_sheet(ws, rows):
    ws.append(['Property', 'Date', 'Loan', 'Type', 'Amount', 'Description'])
    ws.row_dimensions[1].font = Font(bold=True)

    for row in sorted(rows, key=lambda item: (item['property'], item['date'])):
        ws.append([
            row['property'],
            row['date'].isoformat(),
            row['loan'],
            row['type'],
            round(row['amount'] or 0.0),
            row['description'],
        ])

    for column_cells in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(max_len + 2, 50)


def _prepare_ownership_lookup(properties: List[Property]) -> Dict[int, List[Tuple[date, float]]]:
    lookup = {}
    for property_obj in properties:
        events = sorted(property_obj.ownership_events, key=lambda event: event.event_date or date.min)
        lookup[property_obj.id] = [(event.event_date, event.ownership_percent) for event in events]
    return lookup


def _ownership_percent(events: List[Tuple[date, float]], target_date: date, default: float = 1.0) -> float:
    percent = default or 1.0
    for event_date, event_percent in events:
        if not event_date:
            continue
        if event_date <= target_date:
            percent = event_percent
        else:
            break
    return percent


def _resolve_labels(property_map, loan_map, cf):
    if cf.property_id and cf.property_id in property_map:
        property_obj = property_map[cf.property_id]
        property_label = property_obj.property_name or property_obj.property_id or f"Property #{property_obj.id}"
    else:
        property_label = "Unassigned"

    if cf.loan_id and cf.loan_id in loan_map:
        loan_obj = loan_map[cf.loan_id]
        loan_label = loan_obj.loan_name or loan_obj.loan_id or f"Loan #{loan_obj.id}"
    else:
        loan_label = '—'

    if property_label == "Unassigned" and loan_label != '—':
        property_label = f"Unassigned ({loan_label})"

    return property_label, loan_label
