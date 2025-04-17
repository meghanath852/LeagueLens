import "./globals.css";
import { ChatProvider } from "./_context/Chat"; // Import the ChatProvider
import { CommentaryProvider } from "./_context/CommentaryContext"; // Import our new CommentaryProvider

export const metadata = {
  title: "LeagueLens",
  description: "A chatbot UI similar to Perplexity",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ChatProvider>
          <CommentaryProvider>{children}</CommentaryProvider>
        </ChatProvider>
      </body>
    </html>
  );
}
