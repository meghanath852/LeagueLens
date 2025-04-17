"use client";
import { useEffect, useState, useRef } from "react";

interface CommentaryProps {
  isEnabled: boolean;
}

interface CommentaryData {
  commentary: string;
  timestamp: string;
}

export default function Commentary({ isEnabled }: CommentaryProps) {
  const [commentary, setCommentary] = useState<CommentaryData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<string>("stopped");
  const hasBeenEnabled = useRef(false);

  // Control the commentary service based on isEnabled prop
  useEffect(() => {
    // Track if the component has ever been enabled
    if (isEnabled) {
      hasBeenEnabled.current = true;
    }
    
    const controlCommentaryService = async () => {
      try {
        if (isEnabled) {
          // Start the service
          const response = await fetch("http://localhost:8051/api/commentary/start", {
            method: "POST",
          });
          const data = await response.json();
          console.log("Commentary service start response:", data);
          setServiceStatus(data.status);
        } else if (hasBeenEnabled.current) {
          // Only attempt to stop if it was previously enabled
          // This ensures we don't make unnecessary API calls
          const response = await fetch("http://localhost:8051/api/commentary/stop", {
            method: "POST",
          });
          const data = await response.json();
          console.log("Commentary service stop response:", data);
          setServiceStatus(data.status);
          
          // Clear the commentary when disabled
          setCommentary(null);
        }
      } catch (error) {
        console.error("Error controlling commentary service:", error);
      }
    };

    controlCommentaryService();
    
    // Cleanup function to ensure the service is stopped when component unmounts
    return () => {
      if (hasBeenEnabled.current) {
        fetch("http://localhost:8051/api/commentary/stop", {
          method: "POST",
        }).catch(error => {
          console.error("Error stopping commentary service during cleanup:", error);
        });
      }
    };
  }, [isEnabled]);

  // Fetch commentary updates when enabled
  useEffect(() => {
    // Don't fetch if commentary is disabled
    if (!isEnabled) return;

    const fetchCommentary = async () => {
      setIsLoading(true);
      try {
        const response = await fetch("http://localhost:8051/api/live-commentary");
        if (!response.ok) throw new Error("Failed to fetch commentary");
        const data = await response.json();
        setCommentary(data);
      } catch (error) {
        console.error("Error fetching commentary:", error);
      } finally {
        setIsLoading(false);
      }
    };

    // Fetch commentary immediately
    fetchCommentary();

    // Set up interval to fetch commentary every 5 seconds
    const interval = setInterval(fetchCommentary, 5000);
    
    // Clean up interval on unmount or when isEnabled changes
    return () => clearInterval(interval);
  }, [isEnabled]);

  // Don't render anything if commentary is disabled
  if (!isEnabled) return null;

  // Format timestamp if it exists
  const formattedTime = commentary?.timestamp 
    ? new Date(commentary.timestamp).toLocaleTimeString()
    : "";

  return (
    <div
      style={{
        padding: "15px",
        backgroundColor: "rgba(31, 42, 68, 0.9)",
        borderRadius: "8px",
        boxShadow: "0 4px 6px rgba(0, 0, 0, 0.5)",
        margin: "15px 0",
        color: "white",
      }}
    >
      <h3 style={{ margin: "0 0 8px 0", fontSize: "1.2rem", fontWeight: "bold" }}>
        Live Commentary
      </h3>
      
      {isLoading && !commentary ? (
        <p style={{ fontStyle: "italic", color: "#ccc" }}>Loading commentary...</p>
      ) : !commentary ? (
        <p style={{ fontStyle: "italic", color: "#ccc" }}>Starting commentary service...</p>
      ) : (
        <div>
          <p style={{ margin: "0 0 5px 0", fontSize: "1rem" }}>
            {commentary.commentary}
          </p>
          {formattedTime && (
            <p style={{ margin: "5px 0 0 0", fontSize: "0.8rem", color: "#ccc", textAlign: "right" }}>
              {formattedTime}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
