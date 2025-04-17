# Project Structure

This repository contains a full-stack cricket statistics and commentary application built with Next.js and FastAPI. The application provides cricket statistics, live commentary, and AI-powered chat capabilities.

## Architecture Overview

The project follows a client-server architecture with:

- **Frontend**: Next.js application with React components
- **Backend**: FastAPI Python application
- **Data Processing**: Python scripts for cricket data management
- **Containerization**: Docker for development and deployment

## Frontend Structure

The frontend is built with Next.js 15, using React 19 and Tailwind CSS 4 for styling.

### Key Directories

- `/src`: Contains the Next.js application code
  - `/app`: Next.js app router pages and layouts
  - `/components`: Reusable React components
  - `/hooks`: Custom React hooks
  - `/lib`: Utility functions and shared code
  - `/styles`: Global CSS and Tailwind configuration

### Main Dependencies

- `next` (v15.3.0): React framework with server-side rendering
- `react` (v19.0.0): UI library for component-based development
- `tailwindcss` (v4): Utility-first CSS framework
- `react-icons` (v5.5.0): Icon library
- `lamejs` (v1.2.1): JavaScript MP3 encoder
- `openai` (v4.95.0): OpenAI API client for AI capabilities

### Key Features

- Modern UI with responsive design
- Server-side rendering for improved performance
- API integration with the backend
- Real-time cricket statistics and commentary display
- Audio playback for cricket commentary

## Backend Structure

The backend is built with FastAPI, a modern Python web framework for building APIs.

### Key Directories

- `/backend`: Main backend application code
  - `/app.py`: Entry point and API route definitions
  - `/chat`: AI chat functionality 
  - `/player_stats`: Player statistics processing
  - `/sql_with_pathway`: SQL database integration
  - `/logs`: Application logs

### Main Dependencies

- `fastapi`: High-performance API framework
- `uvicorn`: ASGI server for FastAPI
- `pandas`: Data manipulation and analysis
- `numpy`: Numerical computing
- `python-dotenv`: Environment variable management
- `openai`: OpenAI API integration
- `langchain`: LLM application framework

### Key Features

- RESTful API for cricket statistics
- Live match data processing
- AI-powered cricket chat using LangGraph
- Real-time commentary generation
- Data storage and retrieval

## Data Flow

1. **Cricket Match Data**:
   - Updated via `jsonfileupdate.py` script
   - Stored in JSON and CSV formats
   - Processed and served through API endpoints

2. **Player Statistics**:
   - Loaded from CSV files
   - Transformed using pandas
   - Exposed through RESTful endpoints

3. **Live Commentary**:
   - Generated through the backend
   - Streamed to the frontend
   - Optionally converted to audio

4. **AI Chat**:
   - User queries sent from frontend to backend
   - Processed using LangGraph agent with SQL capabilities
   - Response returned to the frontend for display

## Docker Structure

The application is containerized using Docker:

- `Dockerfile`: Multi-stage build for the Next.js frontend
- `backend/Dockerfile`: Configuration for the Python backend
- `docker-compose.yml`: Orchestration of frontend and backend services
- `.dockerignore` files: Optimization of build context

## Deployment Workflow

The application supports multiple deployment options:

1. **Docker Deployment**:
   - Using docker-compose for orchestration
   - Container health checks ensure service availability
   - Environment variables for configuration

2. **Manual Deployment**:
   - Backend: Python virtual environment with requirements.txt
   - Frontend: npm for dependency management and build process

3. **Development Workflow**:
   - `start_app.sh` script for starting both services
   - Hot-reloading for frontend development
   - API testing through exposed endpoints

## Environment Configuration

The application is configured through environment variables:

- `.env.local`: Frontend environment variables
- `backend/.env`: Backend environment variables
- `.env.example` files: Templates for configuration

## Conclusion

This project demonstrates a modern approach to full-stack development with a clear separation of concerns between frontend and backend. The architecture is designed for scalability, with containerization supporting consistent deployment across environments. The integration of cricket statistics with AI capabilities showcases the application's ability to combine data processing with interactive user experiences. 