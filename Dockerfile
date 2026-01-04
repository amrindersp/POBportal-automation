FROM python:3.13-slim

# Install only essential dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright with system dependencies
RUN python -m playwright install --with-deps chromium

COPY . .

EXPOSE 10000

CMD ["bash", "start.sh"]
