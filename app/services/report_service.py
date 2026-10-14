"""Servicio de generación de informes financieros para envío por email.

Reutiliza la lógica de reports.py (resumen del periodo) y heatmap.py
(indicadores con color) para producir un informe HTML del negocio.
"""
from datetime import date

from app.catalog import category_label, is_inverted
from app.models.business import Business
from app.routes.reports import _query_period_data, _summarize_data
from app.services.heatmap import calculate_all_indicators, get_net_profit_indicator

# Nombres de color legibles y su emoji
_COLOR_INFO = {
    'green': ('🟢', 'Saludable'),
    'yellow': ('🟡', 'Precaución'),
    'orange': ('🟠', 'Advertencia'),
    'red': ('🔴', 'Alerta'),
    'critical': ('🚨', 'Crítico'),
    'neutral': ('⚪', 'Sin datos'),
}

_MONTH_NAMES = [
    '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
]


def _fmt_money(value):
    """Formatea un número como moneda legible."""
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def build_report_data(business_id, ref_date=None):
    """Arma los datos del informe mensual de un negocio.

    Args:
        business_id: id del negocio.
        ref_date: fecha de referencia (por defecto hoy). El informe cubre
                  el mes en curso hasta esa fecha.

    Returns:
        dict con summary, net_profit (color), alertas e indicadores del día.
    """
    ref_date = ref_date or date.today()
    date_from = ref_date.replace(day=1)
    date_to = ref_date

    # Resumen del periodo (mes en curso) reutilizando reports.py
    data = _query_period_data(business_id, date_from, date_to)
    summary = _summarize_data(data)

    # Indicadores del día (semáforo) y ganancia neta con color
    indicators = calculate_all_indicators(business_id, ref_date)
    net_profit = get_net_profit_indicator(business_id, ref_date)

    # Categorías en alerta (naranja/rojo/crítico) del día
    alerts = []
    for cat, info in indicators.get('indicators', {}).items():
        color = info.get('color')
        if color in ('orange', 'red', 'critical'):
            alerts.append({
                'category': category_label(cat),
                'color': color,
                'emoji': _COLOR_INFO.get(color, ('⚪', ''))[0],
                'percentage': info.get('percentage'),
                'amount': info.get('amount'),
            })

    return {
        'ref_date': ref_date,
        'period_label': f"{_MONTH_NAMES[ref_date.month]} {ref_date.year}",
        'summary': summary,
        'net_profit': net_profit,
        'alerts': alerts,
        'day_indicators': indicators.get('indicators', {}),
    }


def render_report_html(business, report):
    """Genera el HTML del informe para el email.

    Args:
        business: instancia Business.
        report: dict devuelto por build_report_data.
    """
    s = report['summary']
    npf = report['net_profit']
    np_emoji, np_label = _COLOR_INFO.get(npf.get('color', 'neutral'), ('⚪', ''))
    np_pct = npf.get('percentage')
    np_pct_txt = f"{np_pct:.1f}%" if np_pct is not None else "N/A"

    # Filas de alertas
    if report['alerts']:
        alert_rows = "".join(
            f"<li>{a['emoji']} <b>{a['category']}</b>: "
            f"{_fmt_money(a['amount'])}"
            + (f" ({a['percentage']:.1f}% del ingreso)" if a['percentage'] is not None else "")
            + "</li>"
            for a in report['alerts']
        )
        alerts_html = f"<ul style='margin:0;padding-left:1.2em;'>{alert_rows}</ul>"
    else:
        alerts_html = "<p style='color:#2e7d32;margin:0;'>Sin categorías en alerta hoy. 👍</p>"

    net_color_hex = {
        'green': '#2e7d32', 'yellow': '#f9a825', 'orange': '#ef6c00',
        'red': '#c62828', 'critical': '#b71c1c', 'neutral': '#777',
    }.get(npf.get('color', 'neutral'), '#777')

    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:0 auto;color:#222;">
  <h2 style="margin-bottom:0;">💰 FinanzApp — Informe de {business.name}</h2>
  <p style="color:#666;margin-top:4px;">Resumen de {report['period_label']} · generado el {report['ref_date'].isoformat()}</p>

  <table style="width:100%;border-collapse:collapse;margin:16px 0;">
    <tr>
      <td style="padding:10px;background:#f1f8e9;border-radius:6px;">
        <div style="font-size:12px;color:#666;">INGRESO BRUTO (mes)</div>
        <div style="font-size:20px;font-weight:bold;color:#2e7d32;">{_fmt_money(s['total_income'])}</div>
      </td>
      <td style="width:12px;"></td>
      <td style="padding:10px;background:#fff3e0;border-radius:6px;">
        <div style="font-size:12px;color:#666;">TOTAL GASTOS (mes)</div>
        <div style="font-size:20px;font-weight:bold;color:#ef6c00;">{_fmt_money(s['total_expenses'])}</div>
      </td>
    </tr>
  </table>

  <div style="padding:14px;border:2px solid {net_color_hex};border-radius:8px;margin-bottom:16px;">
    <div style="font-size:12px;color:#666;">GANANCIA NETA (mes)</div>
    <div style="font-size:24px;font-weight:bold;color:{net_color_hex};">
      {np_emoji} {_fmt_money(s['net_profit'])} <span style="font-size:14px;">({np_pct_txt} · {np_label})</span>
    </div>
  </div>

  <h3 style="margin-bottom:6px;">Desglose de gastos del mes</h3>
  <ul style="margin:0 0 16px;padding-left:1.2em;color:#444;">
    <li>Salarios: {_fmt_money(s['total_salaries'])}</li>
    <li>Retiros del dueño: {_fmt_money(s['total_withdrawals'])}</li>
    <li>Gastos variables: {_fmt_money(s['total_variable_expenses'])}</li>
    <li>Costos operativos: {_fmt_money(s['total_operating_costs'])}</li>
  </ul>

  <h3 style="margin-bottom:6px;">⚠️ Categorías en alerta (hoy)</h3>
  {alerts_html}

  <p style="color:#999;font-size:12px;margin-top:24px;border-top:1px solid #eee;padding-top:12px;">
    Este es un informe automático de FinanzApp. Negocio: {business.name} ({business.business_type}).
  </p>
</div>
"""


def build_report_for_business(business_id, ref_date=None):
    """Devuelve (business, report_data, html) para un negocio, o None si no existe."""
    business = Business.query.get(business_id)
    if business is None:
        return None
    report = build_report_data(business_id, ref_date)
    html = render_report_html(business, report)
    return business, report, html
