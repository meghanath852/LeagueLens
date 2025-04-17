# Cricket Statistics and Commentary Application

<p align="center">
  <img src="https://img1.hscicdn.com/image/upload/f_auto,t_ds_square_w_320,q_50/lsci/db/PICTURES/CMS/316500/316555.png" alt="Cricket Player" width="200" />
</p>

## Demo Videos
- [Main Page and Chat Demo](https://www.youtube.com/watch?v=kz1UalbZqD4)
- [Commentary and Stats Demo](https://www.youtube.com/watch?v=1vWXb16vwnQ)

This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

### Option 1: Running with Docker (Recommended)

1. Make sure you have [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) installed on your system.

2. Clone this repository:
   ```bash
   git clone https://github.com/meghanath852/frontendcharp.git
   cd frontendcharp
   ```

3. Run the Docker setup script:
   ```bash
   chmod +x docker-setup.sh
   ./docker-setup.sh
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

   ```bash
   cd backend
   # Create a Python virtual environment (recommended)
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```

2. In a new terminal, start the frontend:

   ```bash
   npm install
   npm run dev
   ```

3. Or use the provided script to start both services:

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

