import './globals.css';
import type { Metadata } from 'next';
import { ReactNode } from 'react';

export const metadata: Metadata = {
  title: 'ScoreForge',
  description: 'Convert audio into beautifully engraved sheet music with ScoreForge.'
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="bg-background">
      <body className="min-h-screen">
        {children}
      </body>
    </html>
  );
}
