# ruff: noqa: E501

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)

from app.schemas.reporting import IncidentReportContext

REPORT_DISCLAIMER = (
    "This report is a point-in-time analyst aid generated from persisted SENTINEL "
    "telemetry and deterministic relationships. It is not a forensic-completeness or "
    "compliance certification. Observed relationships are not packet capture, absence of "
    "evidence is not proof of absence, and a database connection does not prove queries, "
    "collection, or exfiltration. AI-assisted content, when included, is non-authoritative."
)


def _datetime(value: datetime | None) -> str:
    if value is None:
        return "Not recorded"
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3_600)
    minutes, seconds = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes or hours:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _enum_text(value: Any) -> str:
    return str(getattr(value, "value", value))


def _html_table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    head = "".join(f'<th scope="col">{escape(header)}</th>' for header in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>")
    if not body:
        body.append(f'<tr><td class="empty" colspan="{len(headers)}">None recorded</td></tr>')
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def _html_list(items: Iterable[str], empty: str = "None recorded") -> str:
    values = list(items)
    if not values:
        return f'<p class="empty">{escape(empty)}</p>'
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in values) + "</ul>"


def _ai_html(context: IncidentReportContext) -> str:
    analysis = context.ai_analysis
    if analysis is None or analysis.output is None:
        return ""
    output = analysis.output
    evidence_state = "Outdated" if analysis.is_stale else "Current"
    observations = _html_list(item.statement for item in output.observations)
    uncertainties = _html_list(
        f"{item.statement} Reason: {item.reason}" for item in output.uncertainties
    )
    actions = _html_list(
        f"{item.priority.upper()}: {item.action} Reason: {item.reason}"
        for item in output.recommended_actions
    )
    return f"""
    <section class="ai-section">
      <h2>AI-Assisted Investigation</h2>
      <p class="ai-warning">Non-authoritative analyst aid - verify against deterministic evidence.</p>
      {
        _html_table(
            ("Provider", "Model", "Generated", "Evidence version"),
            (
                (
                    analysis.provider_label,
                    analysis.model,
                    _datetime(analysis.completed_at),
                    evidence_state,
                ),
            ),
        )
    }
      <h3>Executive Summary</h3>
      <p>{escape(output.executive_summary)}</p>
      <h3>Observations</h3>
      {observations}
      <h3>Correlation Explanation</h3>
      <p>{escape(output.correlation_explanation.statement)}</p>
      <h3>Uncertainties</h3>
      {uncertainties}
      <h3>Investigation Priorities</h3>
      {actions}
    </section>
    """


def render_html_report(context: IncidentReportContext) -> str:
    incident = context.incident
    summary_table = _html_table(
        ("Severity", "Status", "Confidence", "Risk", "Alerts", "Assets", "Events"),
        (
            (
                _enum_text(incident.severity).upper(),
                _enum_text(incident.status).replace("_", " ").title(),
                f"{incident.confidence_score} / 100 (experimental deterministic score)",
                f"{incident.risk_score:g} / 100",
                incident.alert_count,
                incident.asset_count,
                incident.event_count,
            ),
        ),
    )
    time_table = _html_table(
        ("First activity", "Last activity", "Duration", "Generated"),
        (
            (
                _datetime(incident.first_activity_at),
                _datetime(incident.last_activity_at),
                _duration(context.duration_seconds),
                _datetime(context.generated_at),
            ),
        ),
    )
    assets = _html_table(
        ("Hostname", "Role / type", "IP address", "Zone", "Status", "Risk"),
        (
            (
                item.hostname,
                _enum_text(item.asset_type).replace("_", " ").title(),
                item.ip_address,
                item.network_zone,
                _enum_text(item.status).replace("_", " ").title(),
                f"{item.risk_score:g} / 100",
            )
            for item in incident.assets
        ),
    )
    alerts = _html_table(
        ("Rule", "Title", "Severity", "First activity", "Last activity", "Evidence"),
        (
            (
                item.rule_id,
                item.title,
                _enum_text(item.severity).upper(),
                _datetime(item.first_event_at),
                _datetime(item.last_event_at),
                item.evidence_count,
            )
            for item in incident.alerts
        ),
    )
    story_items = []
    for index, item in enumerate(incident.story, start=1):
        attack = (
            f"{item.mitre_technique_id} - {item.mitre_technique_name}"
            if item.mitre_technique_id
            else "No precise ATT&CK mapping asserted"
        )
        story_items.append(
            f"""
            <article class="story-item">
              <div class="story-number">{index:02d}</div>
              <div><h3>{escape(item.title)}</h3>
              <p class="meta">{escape(_datetime(item.timestamp))} | {escape(item.rule_id)} | {escape(attack)}</p>
              <p>{escape(item.description)}</p></div>
            </article>
            """
        )
    story = "".join(story_items) or '<p class="empty">No deterministic story items recorded.</p>'
    timeline = _html_table(
        ("Time", "Activity", "Rule", "Alert", "Evidence count"),
        (
            (
                _datetime(item.first_event_at),
                item.title,
                item.rule_id,
                str(item.id),
                item.evidence_count,
            )
            for item in incident.alerts
        ),
    )
    correlation = _html_table(
        ("Signal", "Strength", "Weight", "Explanation"),
        (
            (
                item.type.replace("_", " ").title(),
                item.strength.title(),
                f"+{item.weight}",
                item.description,
            )
            for item in incident.correlation_signals
        ),
    )
    techniques = _html_table(
        ("Technique", "Name", "Tactic", "First observed", "Alerts"),
        (
            (
                item.technique_id,
                item.technique_name,
                item.tactic,
                _datetime(item.first_observed_at),
                len(item.alert_ids),
            )
            for item in incident.observed_techniques
        ),
    )
    relationships = _html_table(
        ("Source", "Destination", "Service", "First observed", "Last observed", "Count"),
        (
            (
                f"{item.source_hostname} ({item.source_ip})",
                f"{item.destination_hostname} ({item.destination_ip}:{item.destination_port or '-'})",
                f"{item.protocol.upper()} / {item.connection_type}",
                _datetime(item.first_seen),
                _datetime(item.last_seen),
                item.connection_count,
            )
            for item in context.network_relationships
        ),
    )
    scenario = (
        f'<p class="snapshot">Scenario attribution: <strong>{escape(incident.scenario.scenario_id)}</strong> - '
        f"{escape(incident.scenario.scenario_name)} ({escape(incident.scenario.status)})</p>"
        if incident.scenario
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="referrer" content="no-referrer">
  <title>SENTINEL {escape(incident.incident_number)} Security Incident Report</title>
  <style>
    :root {{ color: #152238; background: #eef2f5; font-family: Inter, "Segoe UI", Arial, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 28px; }}
    main {{ max-width: 1080px; margin: 0 auto; background: #fff; border: 1px solid #d7e0e7; box-shadow: 0 12px 38px rgba(21,34,56,.08); }}
    header {{ padding: 34px 40px 30px; border-top: 7px solid #168f7a; border-bottom: 1px solid #d7e0e7; }}
    .brand {{ margin: 0; color: #168f7a; font-size: 13px; font-weight: 800; letter-spacing: .2em; }}
    h1 {{ margin: 10px 0 4px; font-size: 28px; }}
    .incident-number {{ margin: 0; color: #526478; font-family: Consolas, monospace; }}
    section {{ padding: 24px 40px; border-bottom: 1px solid #e4eaee; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; color: #122033; }}
    h3 {{ margin: 0 0 6px; font-size: 13px; }}
    p, li {{ font-size: 12px; line-height: 1.62; }}
    .lede {{ max-width: 850px; color: #405166; }}
    .snapshot, .ai-warning {{ padding: 10px 12px; border-left: 3px solid #168f7a; background: #edf8f5; color: #274b45; }}
    .table-wrap {{ overflow-x: auto; margin: 12px 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 10.5px; }}
    th {{ background: #edf2f5; color: #33465c; text-align: left; font-weight: 700; }}
    th, td {{ padding: 8px; border: 1px solid #d7e0e7; vertical-align: top; overflow-wrap: anywhere; }}
    .empty {{ color: #6e7e8f; font-style: italic; text-align: center; }}
    .story-item {{ display: grid; grid-template-columns: 34px 1fr; gap: 12px; margin: 10px 0; padding: 12px; border: 1px solid #dde5ea; border-radius: 6px; break-inside: avoid; }}
    .story-number {{ display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: #e2f4ef; color: #168f7a; font: 700 10px Consolas, monospace; }}
    .meta {{ margin: 0 0 5px; color: #69798b; font: 10px Consolas, monospace; }}
    .ai-section {{ border-left: 5px solid #7857a8; background: #fcfaff; }}
    .ai-section .ai-warning {{ border-left-color: #7857a8; background: #f0eafb; color: #4f3c6b; }}
    footer {{ padding: 20px 40px 28px; color: #5c6d7f; background: #f7f9fa; }}
    @media print {{ body {{ padding: 0; background: white; }} main {{ border: 0; box-shadow: none; }} section {{ break-inside: auto; }} thead {{ display: table-header-group; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="brand">SENTINEL</p>
    <h1>Security Incident Report</h1>
    <p class="incident-number">{escape(incident.incident_number)} | Generated {_datetime(context.generated_at)}</p>
  </header>
  <section>
    <h2>Incident Summary</h2>
    <h3>{escape(incident.title)}</h3>
    <p class="lede">{escape(incident.summary)}</p>
    {scenario}
    {summary_table}
    {time_table}
  </section>
  <section><h2>Affected Assets</h2>{assets}</section>
  <section><h2>Alert Summary</h2>{alerts}</section>
  <section><h2>Deterministic Attack Story</h2><p class="lede">Chronological observations reconstructed from persisted Alert evidence.</p>{story}</section>
  <section><h2>Timeline</h2>{timeline}</section>
  <section><h2>Correlation Evidence</h2><p class="lede">Why SENTINEL grouped these Alerts. Confidence is an experimental deterministic score, not a probability.</p>{correlation}</section>
  <section><h2>Observed ATT&amp;CK Techniques</h2><p class="lede">Only mappings carried by observed, non-false-positive Alerts are included.</p>{techniques}</section>
  <section><h2>Network Relationships</h2><p class="lede">Only relationships supported by this Incident's persisted evidence are included.</p>{relationships}</section>
  {_ai_html(context)}
  <footer><h2>Limitations and Evidence Disclaimer</h2><p>{escape(REPORT_DISCLAIMER)}</p><p>Handle this export as security-sensitive data; it may contain hostnames, IP addresses, usernames, and evidence identifiers.</p></footer>
</main>
</body>
</html>"""


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "ReportBrand",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#168f7a"),
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#122033"),
            spaceAfter=5,
        ),
        "section": ParagraphStyle(
            "ReportSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#122033"),
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "subsection": ParagraphStyle(
            "ReportSubsection",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#24364b"),
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#405166"),
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=6.8,
            leading=9,
            textColor=colors.HexColor("#405166"),
        ),
        "meta": ParagraphStyle(
            "ReportMeta",
            parent=base["BodyText"],
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#607184"),
            spaceAfter=8,
        ),
        "notice": ParagraphStyle(
            "ReportNotice",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            borderColor=colors.HexColor("#168f7a"),
            borderWidth=0.7,
            borderPadding=7,
            backColor=colors.HexColor("#edf8f5"),
            textColor=colors.HexColor("#274b45"),
            spaceBefore=4,
            spaceAfter=8,
        ),
    }


def _pdf_paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)), style)


def _pdf_table(
    headers: Sequence[str],
    rows: Iterable[Sequence[Any]],
    widths: Sequence[float],
    styles: dict[str, ParagraphStyle],
) -> LongTable:
    values = list(rows)
    if not values:
        values = [("None recorded", *("" for _ in headers[1:]))]
    data = [
        [_pdf_paragraph(header, styles["small"]) for header in headers],
        *[[_pdf_paragraph(value, styles["small"]) for value in row] for row in values],
    ]
    table = LongTable(data, colWidths=list(widths), repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef2")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#24364b")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cdd8df")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafb")]),
            ]
        )
    )
    return table


def _pdf_header_footer(canvas, document) -> None:  # noqa: ANN001
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#168f7a"))
    canvas.setLineWidth(1.5)
    canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#607184"))
    canvas.drawString(18 * mm, 10 * mm, "SENTINEL Security Incident Report")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def render_pdf_report(context: IncidentReportContext) -> bytes:
    incident = context.incident
    buffer = BytesIO()
    styles = _pdf_styles()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=17 * mm,
        title=f"SENTINEL {incident.incident_number} Security Incident Report",
        author="SENTINEL",
        subject="Point-in-time security Incident report",
    )
    story: list[Any] = [
        Spacer(1, 4 * mm),
        _pdf_paragraph("SENTINEL", styles["brand"]),
        _pdf_paragraph("Security Incident Report", styles["title"]),
        _pdf_paragraph(
            f"{incident.incident_number} | Generated {_datetime(context.generated_at)}",
            styles["meta"],
        ),
        _pdf_paragraph(
            "Point-in-time snapshot from deterministic SENTINEL evidence.", styles["notice"]
        ),
        _pdf_paragraph("Incident Summary", styles["section"]),
        _pdf_paragraph(incident.title, styles["subsection"]),
        _pdf_paragraph(incident.summary, styles["body"]),
    ]
    if incident.scenario:
        story.append(
            _pdf_paragraph(
                f"Scenario attribution: {incident.scenario.scenario_id} - "
                f"{incident.scenario.scenario_name} ({incident.scenario.status})",
                styles["notice"],
            )
        )
    story.extend(
        [
            _pdf_table(
                ("Severity", "Status", "Confidence", "Risk", "Alerts", "Assets", "Events"),
                (
                    (
                        _enum_text(incident.severity).upper(),
                        _enum_text(incident.status).replace("_", " ").title(),
                        f"{incident.confidence_score} / 100",
                        f"{incident.risk_score:g} / 100",
                        incident.alert_count,
                        incident.asset_count,
                        incident.event_count,
                    ),
                ),
                (21 * mm, 24 * mm, 32 * mm, 22 * mm, 19 * mm, 19 * mm, 19 * mm),
                styles,
            ),
            Spacer(1, 3 * mm),
            _pdf_table(
                ("First activity", "Last activity", "Duration", "Generated"),
                (
                    (
                        _datetime(incident.first_activity_at),
                        _datetime(incident.last_activity_at),
                        _duration(context.duration_seconds),
                        _datetime(context.generated_at),
                    ),
                ),
                (44 * mm, 44 * mm, 24 * mm, 44 * mm),
                styles,
            ),
            _pdf_paragraph("Affected Assets", styles["section"]),
            _pdf_table(
                ("Hostname", "Role / type", "IP", "Zone", "Status", "Risk"),
                (
                    (
                        item.hostname,
                        _enum_text(item.asset_type).replace("_", " ").title(),
                        item.ip_address,
                        item.network_zone,
                        _enum_text(item.status).replace("_", " ").title(),
                        f"{item.risk_score:g}",
                    )
                    for item in incident.assets
                ),
                (34 * mm, 29 * mm, 29 * mm, 25 * mm, 22 * mm, 17 * mm),
                styles,
            ),
            _pdf_paragraph("Alert Summary", styles["section"]),
            _pdf_table(
                ("Rule", "Title", "Severity", "First activity", "Last activity", "Evidence"),
                (
                    (
                        item.rule_id,
                        item.title,
                        _enum_text(item.severity).upper(),
                        _datetime(item.first_event_at),
                        _datetime(item.last_event_at),
                        item.evidence_count,
                    )
                    for item in incident.alerts
                ),
                (24 * mm, 43 * mm, 20 * mm, 31 * mm, 31 * mm, 17 * mm),
                styles,
            ),
            _pdf_paragraph("Deterministic Attack Story", styles["section"]),
            _pdf_paragraph(
                "Chronological observations reconstructed from persisted Alert evidence.",
                styles["body"],
            ),
        ]
    )
    for index, item in enumerate(incident.story, start=1):
        attack = (
            f"{item.mitre_technique_id} - {item.mitre_technique_name}"
            if item.mitre_technique_id
            else "No precise ATT&CK mapping asserted"
        )
        story.append(
            KeepTogether(
                [
                    _pdf_paragraph(f"{index:02d}. {item.title}", styles["subsection"]),
                    _pdf_paragraph(
                        f"{_datetime(item.timestamp)} | {item.rule_id} | {attack}",
                        styles["meta"],
                    ),
                    _pdf_paragraph(item.description, styles["body"]),
                ]
            )
        )
    story.extend(
        [
            _pdf_paragraph("Timeline", styles["section"]),
            _pdf_table(
                ("Time", "Activity", "Rule", "Alert ID", "Evidence"),
                (
                    (
                        _datetime(item.first_event_at),
                        item.title,
                        item.rule_id,
                        str(item.id),
                        item.evidence_count,
                    )
                    for item in incident.alerts
                ),
                (33 * mm, 42 * mm, 24 * mm, 47 * mm, 20 * mm),
                styles,
            ),
            _pdf_paragraph("Correlation Evidence", styles["section"]),
            _pdf_paragraph(
                "Why SENTINEL grouped these Alerts. Confidence is an experimental "
                "deterministic score, not a probability.",
                styles["body"],
            ),
            _pdf_table(
                ("Signal", "Strength", "Weight", "Explanation"),
                (
                    (
                        item.type.replace("_", " ").title(),
                        item.strength.title(),
                        f"+{item.weight}",
                        item.description,
                    )
                    for item in incident.correlation_signals
                ),
                (35 * mm, 25 * mm, 18 * mm, 88 * mm),
                styles,
            ),
            _pdf_paragraph("Observed ATT&CK Techniques", styles["section"]),
            _pdf_paragraph(
                "Only mappings carried by observed, non-false-positive Alerts are included.",
                styles["body"],
            ),
            _pdf_table(
                ("Technique", "Name", "Tactic", "First observed", "Alerts"),
                (
                    (
                        item.technique_id,
                        item.technique_name,
                        item.tactic,
                        _datetime(item.first_observed_at),
                        len(item.alert_ids),
                    )
                    for item in incident.observed_techniques
                ),
                (24 * mm, 49 * mm, 34 * mm, 42 * mm, 17 * mm),
                styles,
            ),
            _pdf_paragraph("Network Relationships", styles["section"]),
            _pdf_paragraph(
                "Only relationships supported by this Incident's persisted evidence are included.",
                styles["body"],
            ),
            _pdf_table(
                ("Source", "Destination", "Service", "First observed", "Last observed", "Count"),
                (
                    (
                        f"{item.source_hostname} ({item.source_ip})",
                        f"{item.destination_hostname} ({item.destination_ip}:{item.destination_port or '-'})",
                        f"{item.protocol.upper()} / {item.connection_type}",
                        _datetime(item.first_seen),
                        _datetime(item.last_seen),
                        item.connection_count,
                    )
                    for item in context.network_relationships
                ),
                (33 * mm, 39 * mm, 27 * mm, 28 * mm, 28 * mm, 11 * mm),
                styles,
            ),
        ]
    )
    analysis = context.ai_analysis
    if analysis is not None and analysis.output is not None:
        output = analysis.output
        story.extend(
            [
                PageBreak(),
                _pdf_paragraph("AI-Assisted Investigation", styles["section"]),
                _pdf_paragraph(
                    "Non-authoritative analyst aid - verify against deterministic evidence.",
                    styles["notice"],
                ),
                _pdf_table(
                    ("Provider", "Model", "Generated", "Evidence version"),
                    (
                        (
                            analysis.provider_label,
                            analysis.model,
                            _datetime(analysis.completed_at),
                            "Outdated" if analysis.is_stale else "Current",
                        ),
                    ),
                    (44 * mm, 44 * mm, 44 * mm, 34 * mm),
                    styles,
                ),
                _pdf_paragraph("Executive Summary", styles["subsection"]),
                _pdf_paragraph(output.executive_summary, styles["body"]),
                _pdf_paragraph("Observations", styles["subsection"]),
            ]
        )
        for item in output.observations:
            story.append(_pdf_paragraph(f"- {item.statement}", styles["body"]))
        story.append(_pdf_paragraph("Correlation Explanation", styles["subsection"]))
        story.append(_pdf_paragraph(output.correlation_explanation.statement, styles["body"]))
        story.append(_pdf_paragraph("Uncertainties", styles["subsection"]))
        for item in output.uncertainties:
            story.append(
                _pdf_paragraph(f"- {item.statement} Reason: {item.reason}", styles["body"])
            )
        story.append(_pdf_paragraph("Investigation Priorities", styles["subsection"]))
        for item in output.recommended_actions:
            story.append(
                _pdf_paragraph(
                    f"- {item.priority.upper()}: {item.action} Reason: {item.reason}",
                    styles["body"],
                )
            )
    story.extend(
        [
            _pdf_paragraph("Limitations and Evidence Disclaimer", styles["section"]),
            _pdf_paragraph(REPORT_DISCLAIMER, styles["notice"]),
            _pdf_paragraph(
                "Handle this export as security-sensitive data; it may contain hostnames, "
                "IP addresses, usernames, and evidence identifiers.",
                styles["body"],
            ),
        ]
    )
    document.build(story, onFirstPage=_pdf_header_footer, onLaterPages=_pdf_header_footer)
    return buffer.getvalue()
