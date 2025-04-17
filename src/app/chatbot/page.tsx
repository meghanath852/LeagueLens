"use client";

import { useEffect, useState, useContext } from "react";
import CricketFieldImage from "../public/cricket-field.jpg";
import Sidebar from "../_components/sidebar";
import { ChatContext } from "../_context/Chat";
import Commentary from "../_components/commentary";
import styles from "./page.module.css";
import { useCommentary } from "../_context/CommentaryContext";

interface Chat {
  userPrompt: string;
  botResponse: string;
}

export default function Chatbot() {
  const [inputValue, setInputValue] = useState("");
  const { chats, setChats } = useContext(ChatContext);
  const [messages, setMessages] = useState<any[]>([]);
  const { isCommentaryEnabled, setIsCommentaryEnabled } = useCommentary();
  console.log(chats);
  const handleGo = async () => {
    const newChat: Chat = {
      userPrompt: inputValue,
      botResponse: "Sample Bot Response",
    };

    setInputValue("");

    setChats((prevChats: Chat[]) => {
      return [...prevChats, newChat];
    });
  };

  return (
    <div
      className={styles.chatbot_main}
      style={{
        backgroundColor: "#0D1117",
        overflowY: "hidden",
        display: "flex",
        flexDirection: "row",
        minHeight: "100vh",
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          zIndex: 1000,
          width: "220px",
          height: "100vh",
        }}
      >
        <Sidebar />
      </div>

      {/* Main Chat Area */}
      <div
        style={{
          backgroundColor: "#0D1117",
          marginLeft: "220px", // space for sidebar
          flex: 1,
          padding: "20px",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "center",
            width: "100%",
            maxWidth: "1200px",
            flexWrap: "wrap", // ensures stacking on smaller screens
            gap: "20px",
          }}
        >
          {/* Chat Section */}
          <div
            style={{
              flex: "1 1 600px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              maxWidth: "800px",
            }}
          >
            <div
              className={styles.chatbot_response}
              style={{
                padding: "20px",
                borderRadius: "10px",
                boxShadow: "0 4px 8px rgba(0, 0, 0, 0.5)",
                backgroundColor: "#16243c",
                overflowY: "auto",
                border: "0.1px solid #A8A8A8",
                height: "600px",
              }}
            >
              {chats.length > 0 ? (
                chats.map((chat, index) => (
                  <div key={index} style={{ marginBottom: "10px" }}>
                    <h2
                      style={{
                        whiteSpace: "pre-line",
                        overflowWrap: "break-word",
                        wordBreak: "break-word",
                        fontWeight: 475,
                        color: "var(--text-textMain)",
                        maxHeight: "144px",
                      }}
                    >
                      {chat.userPrompt}
                    </h2>
                    <hr
                      style={{
                        border: "0.05px solid grey",
                        margin: "10px 0",
                      }}
                    />
                    <p
                      style={{
                        padding: "10px",
                        borderRadius: "5px",
                        color: "#ccc",
                        display: "flex",
                        fontSize: "1em",
                        lineHeight: "1.5",
                        margin: "10px 0",
                      }}
                    >
                      {chat.botResponse}
                    </p>
                  </div>
                ))
              ) : (
                <div style={{ textAlign: "center", color: "#ccc" }}>
                  No chat history available.
                </div>
              )}

              {/* Input Box */}
              <div
                style={{
                  marginTop: "20px",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  width: "100%",
                  border: "0.1px solid #A8A8A8",
                  borderRadius: "7px",
                }}
              >
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Ask anything..."
                  style={{
                    padding: "10px",
                    fontSize: "1em",
                    border: "none",
                    borderRadius: "5px 0 0 5px",
                    outline: "none",
                    backgroundColor: "#1F2A44",
                    color: "white",
                    flex: 1,
                    minWidth: "0",
                  }}
                />
                <button
                  onClick={handleGo}
                  style={{
                    padding: "10px 20px",
                    fontSize: "1em",
                    border: "none",
                    borderRadius: "0 5px 5px 0",
                    backgroundColor: "#1E90FF",
                    color: "white",
                    cursor: "pointer",
                  }}
                >
                  Go
                </button>
              </div>
            </div>
          </div>

          {/* Commentary */}
          <div
            style={{
              flex: "1 1 400px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "flex-start",
            }}
          >
            <div style={{ 
              display: "flex", 
              alignItems: "center", 
              justifyContent: "flex-start",
              marginBottom: "10px" 
            }}>
              <span style={{ marginRight: "8px", fontSize: "0.9rem", color: "white" }}>
                Commentary
              </span>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={isCommentaryEnabled}
                  onChange={() => setIsCommentaryEnabled(!isCommentaryEnabled)}
                />
                <span className="toggle-slider"></span>
              </label>
            </div>

            <Commentary isEnabled={isCommentaryEnabled} />
          </div>
        </div>
        
        <style jsx>{`
          .toggle-switch {
            position: relative;
            display: inline-block;
            width: 40px;
            height: 20px;
          }
          .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
          }
          .toggle-slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #ccc;
            transition: 0.4s;
            border-radius: 20px;
          }
          .toggle-slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 2px;
            bottom: 2px;
            background-color: white;
            transition: 0.4s;
            border-radius: 50%;
          }
          input:checked + .toggle-slider {
            background-color: #2196f3;
          }
          input:checked + .toggle-slider:before {
            transform: translateX(20px);
          }
        `}</style>
      </div>
    </div>
  );
}
