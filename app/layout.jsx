import './globals.css';

export const metadata = {
  title: 'Sosyal Medya Otomasyon — Instagram İçerik Stüdyosu',
  description: 'Yapay zeka destekli Instagram gönderi, hikaye, metin bindirme ve caption üretim otomasyonu.',
  keywords: 'instagram otomasyon, yapay zeka, sosyal medya üretimi, dall-e, gpt-4o, caption üretici',
  authors: [{ name: 'Sosyal Medya Otomasyon' }],
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#000000',
};

export default function RootLayout({ children }) {
  return (
    <html lang="tr" data-theme="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
