"use client";
import { createContext, useState, ReactNode } from "react";

export interface Chat {
  userPrompt: string;
  botResponse: string;
}

interface ChatContextType {
  chats: Chat[];
  setChats: React.Dispatch<React.SetStateAction<Chat[]>>;
}

export const ChatContext = createContext<ChatContextType>({
  chats: [],
  setChats: () => {},
});

export const ChatProvider = ({ children }: { children: ReactNode }) => {
  const [chats, setChats] = useState<Chat[]>([]);

  return (
    <ChatContext.Provider value={{ chats, setChats }}>
      {children}
    </ChatContext.Provider>
  );
};
