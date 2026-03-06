import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'DateNow | AI-Guided Relationship Readiness',
  description: 'A premium, emotionally intelligent dating experience.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-slate-50 text-slate-900`}>
        <main className="min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
