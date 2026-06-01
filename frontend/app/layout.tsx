export const metadata = {
  title: "Deutsch-Tutor",
  description: "Tutor de alemán con voz",
};

import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
