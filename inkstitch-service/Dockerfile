# Dockerfile
# Purpose: Ink/Stitch microservice — image → SVG → PES via headless Ink/Stitch
# Stack: FastAPI + Pillow + potrace + Ink/Stitch (pre-built binary) + pyembroidery

FROM python:3.12-slim

# Install system deps:
# - potrace: bitmap → vector tracing
# - inkscape: needed by Ink/Stitch for some SVG processing
# - wget: to download Ink/Stitch release
# - libcairo2 etc: SVG rendering deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        potrace \
        inkscape \
        wget \
        xz-utils \
        libcairo2 \
        libpango-1.0-0 \
        libgdk-pixbuf2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Install Ink/Stitch pre-built binary (v3.2.2 Linux x86_64)
# This is the actual compiled extension, NOT the source repo
RUN mkdir -p /opt/inkstitch && \
    cd /opt/inkstitch && \
    wget -q "https://github.com/inkstitch/inkstitch/releases/latest/download/inkstitch-3.2.2-linux-x86_64.tar.xz" -O inkstitch.tar.xz && \
    tar -xJf inkstitch.tar.xz && \
    rm inkstitch.tar.xz && \
    chmod +x /opt/inkstitch/inkstitch/bin/inkstitch || true

# Also install as Inkscape extension (some operations need it)
RUN mkdir -p /root/.config/inkscape/extensions && \
    ln -sf /opt/inkstitch/inkstitch /root/.config/inkscape/extensions/inkstitch || true

WORKDIR /app

# Python deps
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pillow \
    pyembroidery \
    numpy

COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
