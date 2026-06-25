import type { AppProps } from "next/app";
import Head from "next/head";
import Link from "next/link";
import "@/styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <Head>
        <title>AI Video Intelligence</title>
        <meta name="description" content="AI-powered video platform with semantic search" />
      </Head>
      <nav className="navbar">
        <Link href="/" className="logo">AI Video</Link>
        <div className="nav-links">
          <Link href="/">Home</Link>
          <Link href="/upload">Upload</Link>
          <Link href="/search">Search</Link>
        </div>
      </nav>
      <main className="container">
        <Component {...pageProps} />
      </main>
    </>
  );
}
