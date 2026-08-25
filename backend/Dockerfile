FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

RUN addgroup --system sentinel && adduser --system --ingroup sentinel sentinel

RUN install -d -o sentinel -g sentinel /var/lib/sentinel-collector

COPY requirements.txt ./
RUN python -m pip install --requirement requirements.txt

COPY --chown=sentinel:sentinel alembic.ini ./
COPY --chown=sentinel:sentinel alembic ./alembic
COPY --chown=sentinel:sentinel app ./app

USER sentinel

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m app.cli.sync_rules && python -m app.cli.sync_lab_assets && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
