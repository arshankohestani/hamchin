import "@fontsource-variable/vazirmatn";
import "./globals.css";

export const metadata = {
  title: "هم‌چین | دستیار هوشمند مدیرگروه",
  description: "طراحی هوشمند برنامه ارائه دروس دانشگاه",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}

