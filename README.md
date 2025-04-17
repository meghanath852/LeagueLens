# Cricket Statistics and Commentary Application

## Demo Videos

### Main Page and Chat Demo
[![Main Page and Chat Demo](https://i.ytimg.com/vi/kz1UalbZqD4/0.jpg)](https://www.youtube.com/watch?v=kz1UalbZqD4 "Main Page and Chat Demo")

### Commentary and Stats Demo
[![Commentary and Stats Demo](https://img.youtube.com/vi/YKD5knkQLbM/0.jpg)](https://www.youtube.com/watch?v=YKD5knkQLbM "Commentary and Stats Demo")

## Getting Started

### Option 1: Running with Docker (Recommended)

1. Make sure you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your system.

2. Clone this repository:
   ```bash
   git clone https://github.com/meghanath852/frontendcharp.git
   cd frontendcharp
   ```

3. Run the Docker setup script:
   
   **For macOS/Linux:**
   ```bash
   chmod +x docker-setup.sh
   ./docker-setup.sh
   ```
   
   **For Windows (PowerShell):**
   ```powershell
   # Option 1: If your execution policy allows script execution
   .\docker-setup.sh
   
   # Option 2: If you prefer to run the commands directly
   # Check if .env file exists, if not create from example
   if (-not (Test-Path .env)) {
     if (Test-Path .env.example) {
       Copy-Item .env.example .env
       Write-Output "Created .env file from .env.example"
       Write-Output "Please edit .env file with your API keys and configuration"
     }
   }
   
   # Build and start the containers
   docker-compose up --build -d
   ```
   
   This script will:
   - Check if Docker and Docker Compose are installed
   - Create a `.env` file from `.env.example` if it doesn't exist
   - Build and start the Docker containers

   Alternatively, you can manually set up:
   - Create a `.env` file with your OpenAI API key
   - Run `docker-compose up -d` to build and start containers

4. The application will be available at:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API: [http://localhost:8051](http://localhost:8051)

5. To stop the containers:
   ```bash
   docker-compose down
   ```

### Option 2: Manual Setup

1. Start the backend server:

   **For macOS/Linux:**
   ```bash
   cd backend
   # Create a Python virtual environment (recommended)
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
   
   **For Windows:**
   ```cmd
   cd backend
   # Create a Python virtual environment (recommended)
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

2. In a new terminal, start the frontend:

   ```bash
   npm install
   npm run dev
   ```

3. Or use the provided script to start both services (macOS/Linux only):

   ```bash
   chmod +x start_app.sh
   ./start_app.sh
   ```

## Updating Match Data

To update match data, run the following in a separate terminal:
```bash
cd backend && python jsonfileupdate.py
```

## Project Structure

- `backend/`: FastAPI backend with cricket data and AI chat functionality
- `src/`: Next.js frontend components and pages
- `public/`: Static assets
- `Dockerfile`: Frontend Docker configuration
- `backend/Dockerfile`: Backend Docker configuration
- `docker-compose.yml`: Docker Compose configuration for orchestrating services

