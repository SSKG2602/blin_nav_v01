FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace/browser-runtime

COPY browser-runtime/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY browser-runtime ./ 

EXPOSE 8200

CMD ["uvicorn", "browser_runtime.main:app", "--host", "0.0.0.0", "--port", "8200", "--app-dir", "/workspace/browser-runtime"]
