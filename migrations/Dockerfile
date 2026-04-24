FROM python:3.10-slim
WORKDIR /app
RUN pip install --no-cache-dir alembic==1.13.1 sqlalchemy==2.0.30 psycopg2-binary==2.9.9
COPY migrations/ ./migrations/
CMD ["alembic", "-c", "migrations/alembic.ini", "upgrade", "head"]
