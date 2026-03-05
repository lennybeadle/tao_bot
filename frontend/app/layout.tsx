import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'TAO Staking Bot Dashboard',
  description: 'Monitor and manage your TAO staking bot',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
