from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.incident import Incident
from app.services.correlation import CorrelationService
from app.services.investigations import InvestigationService
from app.services.reporting import IncidentReportService
from tests.test_incident_correlation import make_alert, make_asset, make_scenario
from tests.test_investigation_assistant import ai_settings, make_incident


@pytest.mark.asyncio
async def test_single_alert_html_report_escapes_content_and_keeps_database_unmapped(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        incident_id, _, _ = await make_incident(session)
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        incident.title = "Unexpected <script>alert('report')</script> connection"
        incident.summary = '<img src=x onerror="alert(1)"> observed safely'
        await session.commit()

        report = await IncidentReportService(session).generate(incident_id, report_format="html")

    rendered = report.content.decode("utf-8")
    assert report.filename.startswith("SENTINEL_INC-")
    assert report.filename.endswith("_Report.html")
    assert "<script>alert" not in rendered
    assert "<img src=x" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;img src=x" in rendered
    assert "DET-DB-001" in rendered
    assert "No precise ATT&amp;CK mapping asserted" in rendered
    assert "T1213" not in rendered
    assert "does not prove queries, collection, or exfiltration" in rendered
    assert ">1</td>" in rendered


@pytest.mark.asyncio
async def test_multi_alert_report_orders_authoritative_attack_techniques(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        asset = await make_asset(session, "employee-01", "10.10.20.10")
        observed = datetime(2026, 8, 26, 10, tzinfo=UTC)
        brute_force = await make_alert(
            session,
            rule_id="DET-SSH-001",
            observed_at=observed,
            asset=asset,
            source_ip="10.10.50.2",
            username="demo-user",
        )
        first = await CorrelationService(session).process_alert(brute_force.id)
        privilege = await make_alert(
            session,
            rule_id="DET-PRIV-001",
            observed_at=observed + timedelta(seconds=20),
            asset=asset,
            source_ip="10.10.50.2",
            username="demo-user",
            event_type="privilege",
            action="sudo_command",
            event_status="success",
        )
        second = await CorrelationService(session).process_alert(privilege.id)
        assert second.incident.id == first.incident.id

        report = await IncidentReportService(session).generate(
            first.incident.id, report_format="html"
        )

    rendered = report.content.decode("utf-8")
    assert rendered.index("T1110") < rendered.index("T1548.003")
    assert "DET-SSH-001" in rendered
    assert "DET-PRIV-001" in rendered
    assert "experimental deterministic score" in rendered


@pytest.mark.asyncio
async def test_scn005_shaped_report_uses_actual_incident_counts_and_mappings(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        employee = await make_asset(session, "employee-01", "10.10.20.10")
        admin = await make_asset(session, "admin-server", "10.10.30.10", criticality="high")
        database = await make_asset(session, "database", "10.10.30.20", criticality="critical")
        web = await make_asset(session, "web-server", "10.10.10.10", criticality="high")
        scenario = await make_scenario(session, "SCN-005")
        observed = datetime(2026, 8, 26, 10, tzinfo=UTC)
        definitions = (
            ("DET-SSH-001", employee, "10.10.50.2", employee.ip_address, "authentication"),
            ("DET-SSH-002", employee, "10.10.50.2", employee.ip_address, "authentication"),
            ("DET-NET-001", employee, employee.ip_address, web.ip_address, "network_connection"),
            ("DET-PRIV-001", admin, employee.ip_address, admin.ip_address, "privilege"),
            (
                "DET-DB-001",
                database,
                employee.ip_address,
                database.ip_address,
                "database_connection",
            ),
        )
        incident_id = None
        for index, (rule_id, asset, source_ip, destination_ip, event_type) in enumerate(
            definitions
        ):
            alert = await make_alert(
                session,
                rule_id=rule_id,
                observed_at=observed + timedelta(seconds=index * 20),
                asset=asset,
                source_ip=source_ip,
                destination_ip=destination_ip,
                username="demo-user",
                scenario_run_id=scenario.id,
                event_type=event_type,
                action="database_connect" if rule_id == "DET-DB-001" else "observed_action",
                event_status="success" if rule_id != "DET-SSH-001" else "failed",
                severity="medium" if rule_id == "DET-DB-001" else "high",
            )
            outcome = await CorrelationService(session).process_alert(alert.id)
            incident_id = incident_id or outcome.incident.id
            assert outcome.incident.id == incident_id
        assert incident_id is not None

        service = IncidentReportService(session)
        context = await service.context_builder.build(incident_id, include_ai=False)
        report = await service.generate(incident_id, report_format="html")

    rendered = report.content.decode("utf-8")
    assert context.incident.alert_count == 5
    assert context.incident.asset_count == 4
    assert context.incident.severity == "critical"
    assert [item.technique_id for item in context.incident.observed_techniques] == [
        "T1110",
        "T1078",
        "T1046",
        "T1548.003",
    ]
    assert "DET-DB-001" in rendered
    assert "T1213" not in rendered
    assert "No precise ATT&amp;CK mapping asserted" in rendered


@pytest.mark.asyncio
async def test_ai_report_section_is_explicit_optional_and_marks_staleness(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        incident_id, _, _ = await make_incident(session)
        investigation = InvestigationService(session, ai_settings())
        pending = await investigation.request_analysis(incident_id)
        completed = await investigation.execute_analysis(pending.id)
        assert completed.status == "completed"

        deterministic = await IncidentReportService(session).generate(
            incident_id, report_format="html", include_ai=False
        )
        current = await IncidentReportService(session).generate(
            incident_id, report_format="html", include_ai=True
        )
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        incident.summary = f"{incident.summary} New authoritative evidence summary."
        await session.commit()
        outdated = await IncidentReportService(session).generate(
            incident_id, report_format="html", include_ai=True
        )

    deterministic_html = deterministic.content.decode("utf-8")
    current_html = current.content.decode("utf-8")
    outdated_html = outdated.content.decode("utf-8")
    assert "AI-Assisted Investigation" not in deterministic_html
    assert "AI-Assisted Investigation" in current_html
    assert "Mock Investigation Provider" in current_html
    assert "Current" in current_html
    assert "Outdated" in outdated_html
    assert "non-authoritative" in outdated_html.lower()


@pytest.mark.asyncio
async def test_pdf_report_is_nonempty_and_handles_long_strings(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        incident_id, _, _ = await make_incident(session)
        incident = await session.get(Incident, incident_id)
        assert incident is not None
        incident.title = "Long report title " + "evidence " * 40
        incident.summary = "Observed bounded activity. " * 80
        await session.commit()

        report = await IncidentReportService(session).generate(incident_id, report_format="pdf")

    assert report.media_type == "application/pdf"
    assert report.filename.endswith("_Report.pdf")
    assert report.content.startswith(b"%PDF-")
    assert len(report.content) > 5_000


@pytest.mark.asyncio
async def test_report_api_uses_safe_download_headers_and_incident_scope(
    client: httpx.AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        incident_id, _, _ = await make_incident(session)

    response = await client.get(f"/api/v1/incidents/{incident_id}/report?format=html")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["content-disposition"].startswith("attachment; filename=")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert incident_id.hex not in response.headers["content-disposition"]

    missing = await client.get("/api/v1/incidents/00000000-0000-0000-0000-000000000000/report")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "INCIDENT_NOT_FOUND"
