import type { Metadata } from 'next'
import { Fraunces, Outfit } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from '@/contexts/AuthContext'
import '@/styles/globals.css'

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-fraunces',
  weight: ['300', '400', '500', '600'],
  style: ['normal', 'italic'],
  display: 'swap',
})

const outfit = Outfit({
  subsets: ['latin'],
  variable: '--font-outfit',
  weight: ['300', '400', '500', '600', '700'],
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'LeafScan — AI Crop Disease Detection',
  description: 'Upload a plant photo and get instant AI-powered disease diagnosis with multilingual treatment advice.',
  icons: { icon: '/favicon.ico' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${fraunces.variable} ${outfit.variable}`}>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange={false}>
          <AuthProvider>
            {children}
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 3500,
                style: {
                  background: 'var(--bg-card)',
                  color:      'var(--text)',
                  border:     '1px solid var(--border)',
                  borderRadius: '12px',
                  fontFamily: 'var(--font-outfit)',
                  fontSize: '14px',
                },
                success: { iconTheme: { primary: '#3a855a', secondary: '#fff' } },
                error:   { iconTheme: { primary: '#dc3545', secondary: '#fff' } },
              }}
            />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
