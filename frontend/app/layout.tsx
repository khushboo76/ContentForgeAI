import "./globals.css";

export const metadata = {
  title: "Content Transformation Platform",
  description: "Turn one source into every deliverable you need.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[var(--background)] antialiased">{children}</body>
    </html>
  );
}
