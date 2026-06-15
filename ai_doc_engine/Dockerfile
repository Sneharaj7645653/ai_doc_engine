# Use official Python image
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (required for ChromaDB and compilation)
RUN apt-get update && apt-get install -y build-essential curl

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000 8501

# Command to run both services using a shell script or directly via CMD. 
# For Docker Compose, we override this CMD.
CMD ["bash"]