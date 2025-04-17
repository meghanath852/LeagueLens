"use client";

import { useEffect, useState, useContext } from "react";
import CricketFieldImage from "../public/cricket-field.jpg";
import Sidebar from "./_components/sidebar";
import { ChatContext } from "./_context/Chat";
import { Chat } from "./_context/Chat";
import { useRouter } from "next/navigation";
import Commentary from "./_components/commentary";
import ChatInterface from "./_components/ChatInterface";
import { useCommentary } from "./_context/CommentaryContext";

export default function Home() {
  const router = useRouter();

  const [scores, setScores] = useState<any[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isPro, setIsPro] = useState(false);
  const [isDeepSearch, setIsDeepSearch] = useState(false);
  const { isCommentaryEnabled, setIsCommentaryEnabled } = useCommentary();
  const [showChat, setShowChat] = useState(false);
  const { chats, setChats } = useContext(ChatContext);
  const fallbackPlayerImage =
    "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQSWiniBB7kcUDrDovLwkkdZO4HO9Tstr13Lw&s"; // Adjust path if needed

  useEffect(() => {
    const fetchLiveScores = async () => {
      try {
        const response = await fetch("http://localhost:8051/api/live-scores");
        if (!response.ok) throw new Error("Network response was not ok");
        const data = await response.json();
        setScores(data);
      } catch (error) {
        console.error("Failed to fetch live scores:", error);
      }
    };
    fetchLiveScores();
    const interval = setInterval(fetchLiveScores, 10000);
    return () => clearInterval(interval);
  }, []);
  // console.log(scores);

  const handleGo = async () => {
    // const botResponse = await fetch(`http://localhost:5000/api/query`, {
    //   method: "POST",
    //   headers: {
    //     "Content-Type": "application/json",
    //   },
    //   body: JSON.stringify({ query: inputValue }),
    // });
    // if (!botResponse.ok) {
    //   console.error("Failed to fetch bot response");
    //   return;
    // }
    // const botData = await botResponse.json();
    // const botChat: Chat = { content: botData.content, owner: "bot" };
    const newChat: Chat = {
      userPrompt: inputValue,
      botResponse: "Sample Bot Response",
    };

    setInputValue("");

    setChats((prevChats: Chat[]) => {
      return [...prevChats, newChat];
    });
    router.push("/chatbot");
    console.log("Go clicked with:", inputValue, isPro, isDeepSearch);
  };

  const handleProClick = () => setIsPro(!isPro);
  const handleDeepSearchClick = () => setIsDeepSearch(!isDeepSearch);
  const handleLiveScoresClick = () => {
    // Logic for Live Scores (already handled by useEffect)
  };

  //main "#0D1117"
  //sidebar "#232526"

  return (
    <div
      style={{
        backgroundColor: "#0D1117",
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        paddingLeft: "220px", // Sidebar width + margin
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "1100px",
          color: "white",
          padding: "20px",
          boxSizing: "border-box",
        }}
      >
        <span
          style={{
            display: "block",
            marginBottom: "20px",
            fontSize: "36px",
            background:
              "linear-gradient(to right, #7953cd 20%, #00affa 30%, #0190cd 70%, #764ada 80%)",
            backgroundSize: "500% auto",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            animation: "textShine 5s ease-in-out infinite alternate",
            fontFamily: "Arial, sans-serif",
            textAlign: "center",
            fontWeight: "bold",
          }}
        >
          <style>
            {`
        @keyframes textShine {
          0% { background-position: 0% 50%; }
          100% { background-position: 100% 50%; }
        }
      `}
          </style>
          Ask me anything about IPL!
        </span>

        {scores &&
          scores.map((score, index) => (
            <div
              key={index}
              style={{
                padding: "15px",
                backgroundColor: "rgba(31, 42, 68, 0.8)",
                borderRadius: "8px",
                boxShadow: "0 4px 6px rgba(0, 0, 0, 0.5)",
                minHeight: "250px",
                margin: "0 auto 20px",
                width: "100%",
                boxSizing: "border-box",
                position: "relative",
              }}
            >
              {/* Match Header with Controls */}
              <div style={{ textAlign: "center", marginBottom: "10px", position: "relative" }}>
                <h2
                  style={{
                    fontSize: "1.5rem",
                    fontWeight: "bold",
                    color: "white",
                  }}
                >
                  {score.team1} vs {score.team2}
                </h2>
                <p style={{ color: "#ccc", fontSize: "0.9rem" }}>
                  {score.stadium}
                </p>
                
                {/* Match Status Information */}
                {score.status_info && score.status_info.required_info && (
                  <div 
                    style={{ 
                      backgroundColor: "rgba(30, 144, 255, 0.2)",
                      padding: "8px 15px",
                      borderRadius: "5px",
                      marginTop: "10px",
                      marginBottom: "15px"
                    }}
                  >
                    {score.status_info.required_info && (
                      <p style={{ color: "#ffc107", fontSize: "0.9rem", margin: "3px 0 0 0" }}>
                        {score.status_info.required_info}
                      </p>
                    )}
                  </div>
                )}

                {/* Controls */}
                <div
                  style={{
                    position: "absolute",
                    top: "0",
                    left: "15px",
                    display: "flex",
                    alignItems: "center",
                    gap: "15px",
                    width: "calc(100% - 30px)",
                    justifyContent: "space-between"
                  }}
                >
                  {/* Commentary Toggle */}
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <span style={{ marginRight: "8px", fontSize: "0.9rem" }}>
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

                  {/* Chat Toggle */}
                  <div style={{ display: "flex", alignItems: "center" }}>
                    <span style={{ marginRight: "8px", fontSize: "0.9rem" }}>
                      Cricket AI
                    </span>
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={showChat}
                        onChange={() => setShowChat(!showChat)}
                      />
                      <span className="toggle-slider"></span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Teams & Players */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-around",
                  flexWrap: "wrap",
                }}
              >
                {/* Left Team */}
                <div style={{ textAlign: "center" }}>
                  <img
                    src={`https://a.espncdn.com/i/teamlogos/cricket/500/${score.team1ObjectId}.png`}
                    alt={`${score.team1} logo`}
                    style={{ width: "60px", height: "60px" }}
                  />
                  <h3>
                    {score.team1}: {score.team1Score}
                  </h3>

                  {score.bowler && (
                    <div
                      style={{
                        marginTop: "10px",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                      }}
                    >
                      <strong
                        style={{
                          fontSize: "0.9rem",
                          color: "#ccc",
                          marginBottom: "4px",
                        }}
                      >
                        Bowler:
                      </strong>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          backgroundColor: "rgba(255, 255, 255, 0.05)",
                          padding: "8px 12px",
                          borderRadius: "8px",
                          width: "100%",
                          justifyContent: "center",
                        }}
                      >
                        <img
                          src={score.bowler.image_url || fallbackPlayerImage}
                          alt={score.bowler.name || "Bowler"}
                          onError={(e) => {
                            (e.target as HTMLImageElement).src =
                              fallbackPlayerImage;
                          }}
                          style={{
                            width: "30px",
                            height: "30px",
                            borderRadius: "50%",
                            marginRight: "10px",
                            objectFit: "cover",
                          }}
                        />
                        <div
                          style={{
                            color: "#ccc",
                            fontSize: "0.85rem",
                            lineHeight: "1.4",
                          }}
                        >
                          <div style={{ fontWeight: "bold", color: "white" }}>
                            {score.bowler.name}
                          </div>
                          <div>
                            {score.bowler.overs} overs, {score.bowler.wickets}{" "}
                            wickets
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Right Team */}
                <div style={{ textAlign: "center" }}>
                  <img
                    src={`https://a.espncdn.com/i/teamlogos/cricket/500/${score.team2ObjectId}.png`}
                    alt={`${score.team2} logo`}
                    style={{ width: "60px", height: "60px" }}
                  />
                  <h3>
                    {score.team2}: {score.team2Score}
                  </h3>

                  {score.batsmen && (
                    <div
                      style={{
                        marginTop: "10px",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                      }}
                    >
                      <strong
                        style={{
                          fontSize: "0.9rem",
                          color: "#ccc",
                          marginBottom: "6px",
                        }}
                      >
                        Batsmen:
                      </strong>

                      {score.batsmen.map(
                        (
                          batsman: {
                            name: string;
                            runs: number;
                            balls: number;
                            image_url: string;
                          },
                          i: number
                        ) => (
                          <div
                            key={i}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              backgroundColor: "rgba(255, 255, 255, 0.05)",
                              padding: "8px 12px",
                              borderRadius: "8px",
                              width: "100%",
                              justifyContent: "center",
                              marginBottom: "6px",
                            }}
                          >
                            <img
                              src={batsman.image_url || fallbackPlayerImage}
                              alt={batsman.name}
                              onError={(e) => {
                                (e.target as HTMLImageElement).src =
                                  fallbackPlayerImage;
                              }}
                              style={{
                                width: "30px",
                                height: "30px",
                                borderRadius: "50%",
                                marginRight: "10px",
                                objectFit: "cover",
                              }}
                            />
                            <div
                              style={{
                                color: "#ccc",
                                fontSize: "0.85rem",
                                lineHeight: "1.4",
                              }}
                            >
                              <div
                                style={{ fontWeight: "bold", color: "white" }}
                              >
                                {batsman.name}
                              </div>
                              <div>
                                {batsman.runs} runs ({batsman.balls} balls)
                              </div>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Footer */}
              <p style={{ textAlign: "center", marginTop: "10px" }}>
                {score.status_info?.match_status || `Result: ${score.result || "Ongoing"}`}
              </p>
              <p
                style={{
                  textAlign: "center",
                  color: "#ccc",
                  fontSize: "0.85rem",
                }}
              >
                Last updated at {score.last_updated}
              </p>
              {(!score.result || 
                score.result.toLowerCase() === "ongoing" || 
                (score.status_info?.match_status && score.status_info.match_status.includes("require"))) && (
                <div
                  style={{
                    position: "absolute",
                    bottom: 0,
                    left: 0,
                    width: "100%",
                    height: "4px",
                    backgroundColor: "#3B82F6",
                    animation: "pulse 2s infinite",
                  }}
                />
              )}

              {/* Custom CSS for toggle switch */}
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

              {/* Add the Commentary component */}
              <Commentary isEnabled={isCommentaryEnabled} />
              
              {/* Add the ChatInterface component */}
              {showChat && (
                <div style={{ marginTop: "15px", height: "500px" }}>
                  <ChatInterface />
                </div>
              )}
            </div>
          ))}
      </div>

      <div style={{ position: "fixed", top: 0, left: 0 }}>
        <Sidebar />
      </div>
    </div>
  );
}
