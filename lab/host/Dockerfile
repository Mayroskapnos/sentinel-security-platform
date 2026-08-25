FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        openssh-client \
        openssh-server \
        postgresql-client \
        procps \
        sshpass \
        sudo \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash demo-user \
    && useradd --create-home --shell /bin/bash ops-user \
    && useradd --create-home --shell /bin/bash admin-demo \
    && install -d -m 0755 /run/sshd \
    && install -d -m 0755 /var/log/sentinel-lab

WORKDIR /app

COPY agent.py ./agent.py
COPY sshd_config /etc/ssh/sshd_config

EXPOSE 22

ENTRYPOINT ["python", "/app/agent.py"]
