/** Synthetic demo accounts (docs: deployment.md). Quick-fill chips on the login page appear only when VITE_DEMO_MODE=true. */
export const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'
export const DEMO_PASSWORD = 'FairRank-demo-1'
export const DEMO_ACCOUNTS = [
  { label: 'Recruiter', email: 'recruiter1@companya.example' },
  { label: 'Delivery head', email: 'head@companya.example' },
  { label: 'Client', email: 'manager@northwind.example' },
] as const
