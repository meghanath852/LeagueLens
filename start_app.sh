#!/bin/bash

# Store the base directory path
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to kill processes on exit
cleanup() {
  echo "Shutting down services..."
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
  exit 0
}

# Set up cleanup on script exit
trap cleanup EXIT INT TERM

# Check if chat directory exists
if [ ! -d "$BASE_DIR/backend/chat" ]; then
  echo "Chat directory not found. Creating directory structure..."
  mkdir -p "$BASE_DIR/backend/chat"
fi

# Start the backend server
echo "Starting backend server..."
cd "$BASE_DIR/backend" && python app.py &
BACKEND_PID=$!
sleep 2

# Start the frontend
echo "Starting frontend..."
cd "$BASE_DIR" && npm run dev &
FRONTEND_PID=$!

echo "All services started!"
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8051"
echo ""
echo "IMPORTANT: jsonfileupdate.py is NOT run automatically."
echo "To update match data, run the following manually in a separate terminal:"
echo "  cd $BASE_DIR/backend && python jsonfileupdate.py"
echo ""
echo "Commentary service will start when you toggle it on in the UI"
echo "Cricket AI Chat will be available when you toggle it on in the UI"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user to interrupt
wait 