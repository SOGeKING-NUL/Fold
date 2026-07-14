FROM python:3.11-slim

# Install system dependencies needed for OpenCV, PaddleOCR, and local packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Copy requirements and install dependencies
COPY src/requirements.txt /code/src/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/src/requirements.txt

# Set up user for Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy the application code
COPY --chown=user . $HOME/app

# Create static directory if not exists
RUN mkdir -p $HOME/app/static

# Expose port (Hugging Face Spaces expects 7860)
EXPOSE 7860

# Run the FastAPI server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
