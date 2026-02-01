import Head from 'next/head'
import styles from '../styles/Home.module.css'
import Dashboard from '../src/components/Dashboard'

export default function Home() {
  return (
    <div className={styles.container}>
      <Head>
        <title>Sentinel-Pay — Dashboard</title>
        <meta name="description" content="Agentic operations dashboard for Cyber Cypher" />
      </Head>

      <main className={styles.main}>
        <Dashboard />
      </main>

    </div>
  )
}
