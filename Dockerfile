# Dockerfile
# Defines the steps to build the container image for our application.

# --- Stage 1: The Builder ---
# This stage installs dependencies to leverage Docker's layer caching.
FROM python:3.11-slim as builder

WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 2: The Final Image ---
# This stage builds the final, lightweight production image.
FROM python:3.11-slim

WORKDIR /app

# Copy the installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy our application source code into the image
COPY ./app /app

# Expose the port the app runs on
EXPOSE 8000

# The command to run when the container starts.
# We use "0.0.0.0" to make the server accessible from outside the container.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]