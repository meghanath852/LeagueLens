"use client";

import { createContext, useState, useContext, ReactNode } from "react";

// Define the context shape
interface CommentaryContextType {
  isCommentaryEnabled: boolean;
  setIsCommentaryEnabled: (enabled: boolean) => void;
}

// Create the context with a default value
const CommentaryContext = createContext<CommentaryContextType>({
  isCommentaryEnabled: false,
  setIsCommentaryEnabled: () => {},
});

// Create a provider component
export function CommentaryProvider({ children }: { children: ReactNode }) {
  const [isCommentaryEnabled, setIsCommentaryEnabled] = useState(false);

  return (
    <CommentaryContext.Provider
      value={{
        isCommentaryEnabled,
        setIsCommentaryEnabled,
      }}
    >
      {children}
    </CommentaryContext.Provider>
  );
}

// Create a hook for easy access to the context
export function useCommentary() {
  return useContext(CommentaryContext);
} 