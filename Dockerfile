FROM python:3.11-slim

WORKDIR /app

# Clear any existing logs
RUN rm -rf /var/log/*

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first
COPY app/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies
RUN pip install --no-cache-dir \
    discord.py[voice] \
    python-dotenv \
    yt-dlp \
    spotipy \
    sponsorblock.py

# Copy application code
COPY app /app/

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV FFMPEG_HIDE_BANNER=1
ENV FFMPEG_LOGLEVEL=error
ENV PYTHONWARNINGS="ignore"

# Run with warnings disabled
CMD ["python", "-W", "ignore", "main.py"]