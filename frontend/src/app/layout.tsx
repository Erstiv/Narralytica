import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Narralytica",
  description: "Natural-Language Video Intelligence Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex flex-col">
          <nav className="border-b border-gray-800 bg-gray-900/50 backdrop-blur">
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
              <a href="/" className="text-xl font-bold text-simpsons-yellow">
                Narralytica
              </a>
              <div className="flex gap-6 text-sm">
                <a href="/" className="hover:text-simpsons-yellow transition">
                  Dashboard
                </a>
                <a href="/search" className="hover:text-simpsons-yellow transition">
                  Search
                </a>
                <a href="/tweak" className="hover:text-simpsons-yellow transition">
                  Tweak Studio
                </a>
                <a href="/admin" className="hover:text-simpsons-yellow transition">
                  Admin
                </a>
              </div>
            </div>
          </nav>
          <main className="flex-1 max-w-7xl mx-auto px-4 py-8 w-full">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
