# Dockerfile
# Purpose: Ink/Stitch microservice — image → SVG → PES
# Stack: FastAPI + Pillow + potrace + Ink/Stitch (from source) + pyembroidery

FROM python:3.12-slim

# Install system deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        potrace \
        inkscape \
        git \
        libcairo2 \
        libpango-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        build-essential \
        pkg-config && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps (API + image processing)
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    pillow \
    pyembroidery \
    numpy \
    python-multipart

# Install Ink/Stitch from source (Python module)
RUN git clone --depth 1 https://github.com/inkstitch/inkstitch.git /opt/inkstitch && \
    cd /opt/inkstitch && \
    pip install --no-cache-dir -r requirements.txt 2>/dev/null || true && \
    pip install --no-cache-dir shapely lxml networkx trimesh scipy 2>/dev/null || true

# Link Ink/Stitch as Inkscape extension
RUN mkdir -p /root/.config/inkscape/extensions && \
    ln -sf /opt/inkstitch /root/.config/inkscape/extensions/inkstitch

# Set PYTHONPATH so we can import inkstitch modules
ENV PYTHONPATH="/opt/inkstitch:${PYTHONPATH}"
ENV INKSTITCH_DIR="/opt/inkstitch"

COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
