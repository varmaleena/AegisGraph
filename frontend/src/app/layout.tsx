import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"AegisGraph · Organizational intelligence",description:"Trace decisions. Simulate impact. Remember the fix."};
export default function Layout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>;
}