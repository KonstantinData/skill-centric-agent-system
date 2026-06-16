FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501

WORKDIR /app

RUN useradd --create-home --uid 10001 scas

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY apps/streamlit_business_ui ./apps/streamlit_business_ui
COPY assets ./assets
COPY examples/tenants ./examples/tenants

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir ".[ui]"

USER scas

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read()"

CMD ["streamlit", "run", "apps/streamlit_business_ui/app.py"]
