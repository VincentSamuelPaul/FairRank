/** Synthetic demo accounts (docs: deployment.md). Only offered on the login page in dev or when VITE_DEMO_LOGINS=true. */
export const DEMO_ENABLED = import.meta.env.DEV || import.meta.env.VITE_DEMO_LOGINS === 'true'
export const DEMO_PASSWORD = 'FairRank-demo-1'
export const DEMO_ACCOUNTS = [
  { label: 'Recruiter', email: 'recruiter1@companya.example' },
  { label: 'Delivery head', email: 'head@companya.example' },
  { label: 'Client · Northwind', email: 'manager@northwind.example' },
  { label: 'Client · Meridian', email: 'manager@meridian.example' },
] as const
