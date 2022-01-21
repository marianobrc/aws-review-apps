# Pull base image
FROM python:3.8

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a user to avoid running containers as root in production
RUN addgroup --system mybackend \
    && adduser --system --ingroup mybackend mybackendapi

# Install os-level dependencies
RUN apt-get update && apt-get install -y -q --no-install-recommends \
  # dependencies for building Python packages
  build-essential \
  # postgress client (psycopg2) dependencies
  libpq-dev \
  # cleaning up unused files to reduce the image size
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Switch to the non-root user
USER mybackendapi

# Set working directory
WORKDIR /home/mybackend/

# Install python dependencies
RUN pip install --upgrade pip
COPY ./requirements/base.txt /home/mybackend/requirements/
COPY ./requirements/prod.txt /home/mybackend/requirements/
RUN pip install --no-cache-dir -r requirements/base.txt
RUN pip install --no-cache-dir -r requirements/prod.txt

# Copy project
COPY . /home/mybackend/

# Override SQS endpoint settings as a workaround to make celery to work with VPC endpoints
COPY ./docker/prod/endpoints.json /home/mybackend/botocore/endpoints.json

# Copy the scripts that serves the backend (applying migrations)
COPY ./docker/prod/django/start-prod-server.sh /home/mybackend/start-prod-server.sh

# Switch to root and set execution permissions
USER root
RUN chmod +x /home/mybackend/start-prod-server.sh

# Switch to the non-root user
USER mybackendapi

# Add the path where packages like gunicorn are installed, to the path
ENV PATH="/home/mybackend/.local/bin/:${PATH}"

# Default command starts the web server. This is overwritten when running the workers.
CMD ["/home/mybackend/start-prod-server.sh"]
