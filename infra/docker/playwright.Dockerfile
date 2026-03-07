FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace/browser-runtime/playwright_service

COPY browser-runtime/playwright_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY browser-runtime /workspace/browser-runtime

CMD ["python", "-c", "print('BlindNav Playwright runtime placeholder. No browser service is implemented yet.')"]
