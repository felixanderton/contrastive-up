FROM --platform=linux/amd64 debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV http_proxy=""
ENV https_proxy=""
ENV HTTP_PROXY=""
ENV HTTPS_PROXY=""

RUN dpkg --add-architecture i386 \
    && apt-get -o Acquire::AllowInsecureRepositories=true update \
    && apt-get install -y --allow-unauthenticated --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    python3-venv \
    # Required to run the 32-bit optic-clp binary
    lib32gcc-s1 \
    libc6-i386 \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .
RUN chmod +x ./optic-clp

# Default command — override at runtime as needed
CMD ["python", "main.py"]
