"use client";
import Sidebar from "../_components/sidebar";
import { useState, useEffect } from "react";
import { FaSearch } from "react-icons/fa";
import { useRouter } from "next/navigation";

const fallbackPlayerImage =
  "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQSWiniBB7kcUDrDovLwkkdZO4HO9Tstr13Lw&s";

const PlayerStats = () => {
  const [searchTerm, setSearchTerm] = useState("");
  const [sortBy, setSortBy] = useState("runs");
  const [players, setPlayers] = useState<any[]>([]);
  const router = useRouter();

  useEffect(() => {
    fetch("http://localhost:8051/players")
      .then((res) => res.json())
      .then((data) => setPlayers(data))
      .catch((err) => console.error("Failed to load players:", err));
  }, []);

  const filteredPlayers = [...players]
    .filter((player) =>
      (player.Player || "").toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      if (sortBy === "name")
        return (a.Player || "").localeCompare(b.Player || "");
      if (sortBy === "runs") return (b.Runs ?? 0) - (a.Runs ?? 0);
      if (sortBy === "wickets") return (b.Wickets ?? 0) - (a.Wickets ?? 0);
      return 0;
    });

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        backgroundColor: "#0D1117",
      }}
    >
      {/* Sidebar */}
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          width: "220px",
          height: "100vh",
          zIndex: 1000,
        }}
      >
        <Sidebar />
      </div>

      {/* Main Content */}
      <div
        style={{
          marginLeft: "220px",
          flex: 1,
          padding: "20px",
          color: "white",
        }}
      >
        {/* Search + Sort Controls */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            marginBottom: "25px",
          }}
        >
          {/* Search Bar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              position: "relative",
              width: "100%",
              maxWidth: "500px",
              marginBottom: "16px",
            }}
          >
            <FaSearch
              style={{
                position: "absolute",
                left: "12px",
                color: "#999",
                fontSize: "16px",
              }}
            />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search players..."
              style={{
                padding: "10px 10px 10px 35px",
                fontSize: "1rem",
                borderRadius: "5px",
                border: "none",
                outline: "none",
                backgroundColor: "#1F2A44",
                color: "white",
                width: "100%",
              }}
            />
          </div>

          {/* Sort Control */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
            }}
          >
            <span style={{ color: "#ccc", fontSize: "1rem" }}>Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                padding: "8px 12px",
                backgroundColor: "#1F2A44",
                color: "white",
                border: "none",
                borderRadius: "5px",
                fontSize: "1rem",
                cursor: "pointer",
              }}
            >
              <option value="name">Alphabetical (A-Z)</option>
              <option value="runs">Most Runs</option>
              <option value="wickets">Most Wickets</option>
            </select>
          </div>
        </div>

        {/* Player Cards */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "30px",
            justifyItems: "center",
          }}
        >
          {filteredPlayers.map((player) => (
            <div
              key={player.id}
              onClick={() => router.push(`/playerstats/${player.id}`)}
              style={{
                backgroundColor: "#16243c",
                borderRadius: "10px",
                padding: "15px",
                width: "100%",
                maxWidth: "180px",
                boxShadow: "0 4px 8px rgba(0, 0, 0, 0.3)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                cursor: "pointer",
              }}
            >
              <img
                src={player.image_url || fallbackPlayerImage}
                alt={player.Player || "Player"}
                onError={(e) => {
                  (e.target as HTMLImageElement).src = fallbackPlayerImage;
                }}
                style={{
                  width: "80px",
                  height: "80px",
                  borderRadius: "50%",
                  marginBottom: "10px",
                  objectFit: "cover",
                }}
              />
              <h3
                style={{
                  marginBottom: "5px",
                  fontSize: "1rem",
                  color: "#fff",
                }}
              >
                {player.Player || "Unnamed"}
              </h3>
              <p
                style={{
                  fontSize: "0.85rem",
                  marginTop: "8px",
                  color: "#aaa",
                }}
              >
                Runs: {player.Runs ?? 0}
                <br />
                Wickets: {player.Wickets ?? 0}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PlayerStats;