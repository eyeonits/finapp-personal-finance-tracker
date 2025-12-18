# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies needed for Snowflake connector
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Important: install snowflake *with* pandas extra just in case,
# and also everything from requirements.txt
RUN pip install --no-cache-dir "snowflake-connector-python[pandas]" \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Flask environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Expose Flask's default port
EXPOSE 5001

# Run Flask server
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]
