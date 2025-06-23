# Use the Azure Functions base image for Python
FROM mcr.microsoft.com/azure-functions/python:4-python3.11-appservice

# Install ffmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Setup environment
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true

# Copy requirements and install
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Copy the app code
COPY . /home/site/wwwroot
