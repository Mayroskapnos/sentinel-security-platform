FROM postgres:16-alpine

ENV TZ=UTC

RUN install -d -o postgres -g postgres /var/log/postgresql

COPY init.sh /docker-entrypoint-initdb.d/10-corporate-demo.sh
RUN sed -i 's/\r$//' /docker-entrypoint-initdb.d/10-corporate-demo.sh \
    && chmod 0755 /docker-entrypoint-initdb.d/10-corporate-demo.sh
