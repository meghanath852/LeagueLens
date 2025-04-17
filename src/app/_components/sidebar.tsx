"use client";

import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import { FaComments, FaChartBar } from "react-icons/fa";
import Image from "next/image";

const Index = () => {
  const router = useRouter();
  const pathname = usePathname();
  return (
    <div
      className="sidebar"
      style={{
        backgroundColor: "#0f152b",
        width: "220px",
        height: "100vh",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        position: "fixed",
        top: 0,
        left: 0,
        boxSizing: "border-box",
        zIndex: 1000,
      }}
    >
      <div
        className="sidebar_top"
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div
          className="sidebar_top_heading"
          style={{
            display: "flex",
            alignItems: "center",
            fontSize: "32px",
            fontWeight: "bold",
            marginBottom: "20px",
            cursor: "pointer",
          }}
          onClick={() => router.push("/")}
        >
          <Image
            src="/circular_logo2.png"
            alt="Logo"
            width={32}
            height={32}
            style={{ marginRight: "10px" }}
          />
          <span style={{ color: "#FFFFFF", fontSize: "24px" }}>LeagueLens</span>
        </div>
        <div className="sidebar_top_options">
          <div
            style={{
              marginBottom: "10px",
              display: "flex",
              alignItems: "center",
              cursor: "pointer",
            }}
            onClick={() => router.push("/")}
          >
            <FaComments
              style={{
                marginRight: "8px",
                color: pathname === "/chatbot" ? "#FFFFFF" : "#BEBEBE",
              }}
            />
            <span
              style={{
                fontSize: "18px",
                color: pathname === "/chatbot" ? "#FFFFFF" : "#BEBEBE",
                fontWeight: pathname === "/chatbot" ? "bold" : "normal",
              }}
            >
              New Chat
            </span>
          </div>
          <div
            style={{ display: "flex", alignItems: "center", cursor: "pointer" }}
            onClick={() => router.push("/playerstats")}
          >
            <FaChartBar
              style={{
                marginRight: "8px",
                color: pathname === "/playerstats" ? "#FFFFFF" : "#BEBEBE",
              }}
            />
            <span
              style={{
                fontSize: "18px",
                color: pathname === "/playerstats" ? "#FFFFFF" : "#BEBEBE",
                fontWeight: pathname === "/playerstats" ? "bold" : "normal",
              }}
            >
              Player Stats
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;