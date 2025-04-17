"use client";

import { useState, useRef } from "react";
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
});

interface ChatMessage {
  question: string;
  answer: string | null;
  error: string | null;
  isLoading: boolean;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim()) return;
    
    const question = inputValue.trim();
    setInputValue("");
    
    // Add user question to messages
    const newMessage: ChatMessage = {
      question,
      answer: null,
      error: null,
      isLoading: true
    };
    
    setMessages((prev) => [...prev, newMessage]);
    setIsLoading(true);
    
    try {
      const response = await fetch("http://localhost:8051/api/chat/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question }),
      });
      
      const data = await response.json();
      
      // Update the message with the response
      setMessages((prev) =>
        prev.map((msg, idx) =>
          idx === prev.length - 1
            ? { ...msg, answer: data.answer, error: data.error, isLoading: false }
            : msg
        )
      );
    } catch (error) {
      console.error("Error sending chat message:", error);
      
      // Update the message with the error
      setMessages((prev) =>
        prev.map((msg, idx) =>
          idx === prev.length - 1
            ? { ...msg, error: "Failed to connect to the chat service", isLoading: false }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const startRecording = async () => {
    setRecordingError(null);
    audioChunksRef.current = [];
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Use simple options that most browsers support
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current);
        await transcribeAudio(audioBlob);
        
        // Stop all tracks to release the microphone
        stream.getTracks().forEach(track => track.stop());
      };
      
      // Request data at regular intervals
      mediaRecorder.start(100);
      setIsRecording(true);
    } catch (error) {
      console.error("Error starting recording:", error);
      setRecordingError("Microphone access denied or not available");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAudio = async (audioBlob: Blob) => {
    try {
      setIsLoading(true);
      
      // For debugging - log file size
      console.log(`Audio blob size: ${audioBlob.size} bytes`);
      
      // Convert the blob to an MP3 file that OpenAI accepts
      const formData = new FormData();
      formData.append("file", audioBlob, "audio.mp3");
      formData.append("model", "whisper-1");
      
      // Use fetch directly to the OpenAI API endpoint
      const response = await fetch("https://api.openai.com/v1/audio/transcriptions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${process.env.NEXT_PUBLIC_OPENAI_API_KEY}`
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`OpenAI API error: ${errorData.error?.message || response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.text) {
        setInputValue(data.text);
      } else {
        setRecordingError("Couldn't transcribe audio. Please try again.");
      }
    } catch (error) {
      console.error("Error transcribing audio:", error);
      setRecordingError(`Error transcribing audio: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "rgba(31, 42, 68, 0.8)",
        borderRadius: "8px",
        padding: "15px",
        boxShadow: "0 4px 6px rgba(0, 0, 0, 0.5)",
      }}
    >
      <h3
        style={{
          margin: "0 0 15px 0",
          color: "white",
          fontSize: "1.2rem",
          fontWeight: "bold",
          textAlign: "center",
        }}
      >
        Cricket AI Chat
      </h3>

      {/* Chat messages */}
      <div
        style={{
          flexGrow: 1,
          overflowY: "auto",
          marginBottom: "15px",
          padding: "10px",
          backgroundColor: "rgba(0, 0, 0, 0.2)",
          borderRadius: "5px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {messages.length === 0 ? (
          <div
            style={{
              color: "#ccc",
              fontStyle: "italic",
              textAlign: "center",
              padding: "20px",
            }}
          >
            Ask any cricket-related question to get started!
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index}>
              {/* User question */}
              <div
                style={{
                  backgroundColor: "#1E90FF",
                  padding: "10px",
                  borderRadius: "10px 10px 0 10px",
                  color: "white",
                  alignSelf: "flex-end",
                  marginLeft: "25%",
                }}
              >
                {message.question}
              </div>

              {/* AI response */}
              <div
                style={{
                  backgroundColor: message.isLoading
                    ? "rgba(80, 80, 80, 0.5)"
                    : message.error
                    ? "rgba(220, 53, 69, 0.2)"
                    : "rgba(80, 80, 80, 0.3)",
                  padding: "10px",
                  borderRadius: "10px 10px 10px 0",
                  color: "white",
                  marginTop: "10px",
                  marginRight: "25%",
                }}
              >
                {message.isLoading ? (
                  <div
                    style={{
                      color: "#ccc",
                      fontStyle: "italic",
                    }}
                  >
                    Thinking...
                  </div>
                ) : message.error ? (
                  <div
                    style={{
                      color: "#dc3545",
                    }}
                  >
                    Error: {message.error}
                  </div>
                ) : (
                  <div>{message.answer}</div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Chat input */}
      <form onSubmit={handleSubmit}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {recordingError && (
            <div
              style={{
                color: "#dc3545",
                fontSize: "0.9rem",
                marginBottom: "5px",
              }}
            >
              {recordingError}
            </div>
          )}
          
          <div style={{ display: "flex", gap: "10px" }}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask about cricket..."
              style={{
                flex: "1",
                padding: "10px",
                borderRadius: "5px",
                border: "none",
                backgroundColor: "#1F2A44",
                color: "white",
                outline: "none",
              }}
              disabled={isLoading || isRecording}
            />
            
            <button
              type="button"
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isLoading}
              style={{
                padding: "10px 15px",
                borderRadius: "5px",
                border: "none",
                backgroundColor: isRecording ? "#dc3545" : "#4CAF50",
                color: "white",
                cursor: isLoading ? "not-allowed" : "pointer",
                opacity: isLoading ? 0.7 : 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {isRecording ? (
                <>
                  <span style={{ fontSize: "1.2rem", marginRight: "5px" }}>■</span>
                  <span>Stop</span>
                </>
              ) : (
                <>
                  <span style={{ fontSize: "1.2rem", marginRight: "5px" }}>🎤</span>
                  <span>Speak</span>
                </>
              )}
            </button>
            
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim() || isRecording}
              style={{
                padding: "10px 15px",
                borderRadius: "5px",
                border: "none",
                backgroundColor: "#1E90FF",
                color: "white",
                cursor: isLoading || !inputValue.trim() || isRecording ? "not-allowed" : "pointer",
                opacity: isLoading || !inputValue.trim() || isRecording ? 0.7 : 1,
              }}
            >
              Send
            </button>
          </div>
        </div>
      </form>
    </div>
  );
} 