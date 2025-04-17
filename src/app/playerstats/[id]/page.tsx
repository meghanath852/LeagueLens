"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Sidebar from "../../_components/sidebar";

const fallbackPlayerImage =
  "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQSWiniBB7kcUDrDovLwkkdZO4HO9Tstr13Lw&s";

export default function PlayerProfile() {
  const params = useParams();
  const router = useRouter();
  const [player, setPlayer] = useState<any>(null);
  const [error, setError] = useState(false);

  const id = Number(params?.id);

  useEffect(() => {
    if (!id && id !== 0) return;

    fetch(`http://localhost:8051/players/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Player not found");
        return res.json();
      })
      .then((data) => setPlayer(data))
      .catch(() => setError(true));
  }, [id]);

  if (error) {
    return <p style={{ color: "red", padding: "20px" }}>Player not found.</p>;
  }

  if (!player) {
    return <p style={{ color: "white", padding: "20px" }}>Loading...</p>;
  }

  const keysToHighlight = [
    "Runs",
    "balls faced total",
    "fours",
    "sixes",
    "balls faced legal",
    "matches played",
  ];

  const statIcons: Record<string, string> = {
    Runs: "🏏",
    "balls faced total": "🎯",
    fours: "4️⃣",
    sixes: "6️⃣",
    "balls faced legal": "✅",
    "matches played": "📅",
  };

  const highlightedStats = Object.entries(player)
    .filter(([key]) => keysToHighlight.includes(key.replace(/_/g, " ")))
    .map(([key, value]) => {
      const formattedKey = key.replace(/_/g, " ");
      const icon = statIcons[formattedKey] || "";
      return (
        <p
          key={key}
          style={{
            fontSize: "1.3rem",
            fontWeight: "600",
            marginBottom: "12px",
          }}
        >
          <strong>
            {icon && <span style={{ marginRight: "8px" }}>{icon}</span>}
            {formattedKey}:
          </strong>{" "}
          {String(value ?? "N/A")}
        </p>
      );
    });

  const otherStats = Object.entries(player)
    .filter(
      ([key]) =>
        !keysToHighlight.includes(key.replace(/_/g, " ")) &&
        key !== "image_url" &&
        key !== "id" &&
        key !== "image_id" &&
        key.toLowerCase() !== "player"
    )
    .map(([key, value]) => (
      <p
        key={key}
        style={{
          fontSize: "1rem",
          marginBottom: "8px",
        }}
      >
        <strong>{key.replace(/_/g, " ")}:</strong> {String(value ?? "N/A")}
      </p>
    ));

  return (
    <div
      style={{
        marginLeft: "220px",
        padding: "40px",
        color: "white",
        backgroundColor: "#0D1117",
        minHeight: "100vh",
      }}
    >
      <button
        onClick={() => router.back()}
        style={{
          marginBottom: "20px",
          backgroundColor: "#1E90FF",
          padding: "10px 20px",
          borderRadius: "6px",
          border: "none",
          color: "white",
          fontWeight: "bold",
          cursor: "pointer",
        }}
      >
        ← Back
      </button>

      <div
        style={{
          backgroundImage: `url('https://png.pngtree.com/thumb_back/fh260/background/20230630/pngtree-d-illustration-of-a-cricket-pitch-with-a-view-of-the-image_3701619.jpg')`,
          backgroundSize: "cover",
          backgroundRepeat: "no-repeat",
          backgroundPosition: "center",
          padding: "30px",
          borderRadius: "10px",
          boxShadow: "0 4px 10px rgba(0,0,0,0.4)",
          position: "relative",
          // backgroundColor: "#0e1117",
        }}
      >
        {/* Centered Player Name */}
        <h2
          style={{
            textAlign: "center",
            fontSize: "2rem",
            fontWeight: "bold",
            marginBottom: "30px",
            color: "white",
          }}
        >
          Player: {player.Player}
        </h2>

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          {/* Highlighted Stats Box */}
          <div
            style={{
              flex: 1,
              minWidth: "250px",
              padding: "20px",
              //   backgroundColor: "#000",
              borderRadius: "16px",
              marginRight: "20px",
              //   backgroundColor: "rgba(0, 0, 0, 0.4)",
              //   backdropFilter: "blur(10px)",
              //   WebkitBackdropFilter: "blur(10px)",
              //   border: "1px solid rgba(255, 255, 255, 0.2)",
              //
              background:
                "linear-gradient(135deg, rgba(0,0,0,0.75), rgba(0,0,0,0.2))",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            {highlightedStats}
          </div>

          {/* Player Image Box */}
          <div
            style={{
              flex: "0 0 260px",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              textAlign: "center",
              padding: "10px",
            }}
          >
            <img
              src={player.image_url || fallbackPlayerImage}
              alt={player.Player}
              onError={(e) => {
                (e.target as HTMLImageElement).src = fallbackPlayerImage;
              }}
              style={{
                backgroundColor: "#16243c",
                width: "220px",
                height: "260px",
                objectFit: "cover",
                borderRadius: "10px",
                border: "3px solid #3b82f6",
                boxShadow: "0 0 12px rgba(59, 130, 246, 0.6)",
                marginBottom: "10px",
              }}
            />
            <h3 style={{ fontSize: "1.3rem", fontWeight: "bold" }}>
              {player.Player}
            </h3>
          </div>
        </div>
      </div>

      {/* Other Stats */}
      <div
        style={{
          backgroundColor: "#16243c",
          padding: "30px",
          borderRadius: "10px",
          boxShadow: "0 4px 10px rgba(0,0,0,0.4)",
          marginTop: "30px",
        }}
      >
        {otherStats}
      </div>

      {/* Sidebar */}
      <div style={{ position: "fixed", top: 0, left: 0 }}>
        <Sidebar />
      </div>
    </div>
  );
}