# Use an official Python runtime as a parent image
FROM python:3.11

# Set the working directory inside the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for SQLite database storage (Render persistent disk)
RUN mkdir -p /data

# Set the environment variable to tell Django where to store the database
ENV DATABASE_PATH=/data/db.sqlite4

# Collect static files
RUN python manage.py collectstatic --noinput

# Apply database migrations
RUN python manage.py migrate

# Expose port 8000 for the web server
EXPOSE 8000
# Start the Gunicorn server
CMD ["gunicorn", "datafactz:application", "--bind", "0.0.0.0:8000"]
