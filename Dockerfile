# Use the official Python image from the Docker Hub
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application into the container
COPY . .

# Collect static files (if applicable)
RUN python manage.py collectstatic --noinput

# Apply database migrations (optional, depending on your setup)
RUN python manage.py migrate

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "datafactz.wsgi:application", "--bind", "0.0.0.0:8000"]
