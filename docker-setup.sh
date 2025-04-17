#!/bin/bash

echo "Setting up Cricket Stats and Chat Application"
echo "---------------------------------------------"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi

# Check if .env file exists, if not create from example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env file from .env.example"
        echo "Please edit .env file with your API keys and configuration"
    else
        echo "Error: .env.example file not found"
        exit 1
    fi
fi

# Build and start the containers
echo "Building and starting Docker containers..."
docker-compose up --build -d

# Check if containers are running
if [ $? -eq 0 ]; then
    echo "Setup completed successfully!"
    echo "The application should be available at:"
    echo "  - Frontend: http://localhost:3000"
    echo "  - Backend API: http://localhost:8051"
    echo ""
    echo "You can stop the containers with: docker-compose down"
else
    echo "Error: There was a problem setting up the application."
    echo "Please check the Docker logs with: docker-compose logs"
fi 