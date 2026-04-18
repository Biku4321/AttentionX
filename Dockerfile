FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 libxext6 libxrender-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Whisper base model
RUN python -c "import whisper; whisper.load_model('base')"

COPY . .

RUN mkdir -p uploads outputs

EXPOSE 8000 8501
