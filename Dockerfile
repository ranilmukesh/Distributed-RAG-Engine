# Use Python 3.11 slim as base
FROM python:3.11-slim

# Build arguments
ARG user_app
ENV USER_APP=$user_app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    libmagic1 \
    poppler-utils \
    libpoppler-cpp-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r ${USER_APP} && \
    useradd -r -g ${USER_APP} -m ${USER_APP} && \
    mkdir -p /home/${USER_APP}/app

# Set working directory
WORKDIR /home/${USER_APP}/app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /home/${USER_APP}/app/tmp \
    /home/${USER_APP}/app/out \
    /home/${USER_APP}/app/answers \
    /home/${USER_APP}/app/saves \
    /home/${USER_APP}/app/logs

# Set permissions
RUN chown -R ${USER_APP}:${USER_APP} /home/${USER_APP}/app && \
    chmod -R 755 /home/${USER_APP}/app

# Environment variables
ENV PYTHONPATH=/home/${USER_APP}/app
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Switch to non-root user
USER ${USER_APP}

# Expose port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Set entry point
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]