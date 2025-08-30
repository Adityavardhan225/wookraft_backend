# Use the official Python image as the base image
FROM python:3.10


# Install system dependencies for SSL and pip
# RUN apt-get update && apt-get install -y \
#     gcc \
#     libssl-dev \
#     ca-certificates \
#     curl \
#     wkhtmltopdf \
#     && rm -rf /var/lib/apt/lists/*


RUN apt-get update && apt-get install -y \
    gcc \
    libssl-dev \
    ca-certificates \
    curl \
    wget \
    gnupg \
    xfonts-base \
    xfonts-75dpi \
 && wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb \
 && apt install -y ./wkhtmltox_0.12.6-1.focal_amd64.deb \
 && rm -f wkhtmltox_0.12.6-1.focal_amd64.deb \
 && rm -rf /var/lib/apt/lists/*




    
# Set environment variables to prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Expose the port that FastAPI will run on
EXPOSE 8000

# Set the command to run the FastAPI application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
