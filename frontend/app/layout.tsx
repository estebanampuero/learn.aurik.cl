export const metadata = {
  title: "Tutor de idiomas — alemán & inglés con voz",
  description: "Practica alemán o inglés hablando: te corrige, responde con voz y traduce cualquier palabra.",
};

import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
