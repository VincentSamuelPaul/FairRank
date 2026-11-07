import { zodResolver } from '@hookform/resolvers/zod'
import { Info, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm, type UseFormReturn } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { FairnessPanel } from '@/components/ui/fairness-panel'
import { Field } from '@/components/ui/field'
import { GlassPanel, HairlineRule } from '@/components/ui/glass-panel'
import { Input } from '@/components/ui/input'
import { PillNav } from '@/components/ui/pill-nav'
import { homeFor, useLogin, useMe } from '@/lib/auth'
import { DEMO_ACCOUNTS, DEMO_MODE, DEMO_PASSWORD } from '@/lib/demo'
import { useReducedMotion } from '@/lib/motion'
import { cn } from '@/lib/utils'

const schema = z.object({
  email: z.string().min(1, 'Enter your email').email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

/* Synthetic evidence samples (docs/BRIEF.md). The last one honestly shows the unsure state: no quote, no score. */
type Sample = { criterion: string; quote: string | null }
const SAMPLES: Sample[] = [
  { criterion: 'Spring Boot', quote: 'Built and maintained 12 Spring Boot microservices' },
  { criterion: 'Hibernate', quote: 'Tuned Hibernate queries and PostgreSQL indexes' },
  { criterion: 'Kubernetes', quote: null },
]
const CYCLE_MS = 8000
const FADE_MS = 300

/**
 * The proof line: ONE evidence quote, no card. On load a wash sweeps over the quote (900ms) and the
 * "Verified in CV" tick draws. Every 8s it cross-fades (300ms) to the next sample.
 */
function ProofLine() {
  const reduced = useReducedMotion()
  const [i, setI] = useState(0)
  const [fading, setFading] = useState(false)
  const [paused, setPaused] = useState(false)
  useEffect(() => {
    if (reduced || paused) return
    let swap: ReturnType<typeof setTimeout>
    const t = setTimeout(() => {
      setFading(true)
      swap = setTimeout(() => { setI((n) => (n + 1) % SAMPLES.length); setFading(false) }, FADE_MS)
    }, CYCLE_MS)
    return () => { clearTimeout(t); clearTimeout(swap) }
  }, [reduced, paused, i])
  const s = SAMPLES[i]
  return (
    <div className="max-w-2xl space-y-3" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <figure key={i} className={cn('space-y-1.5 transition-opacity duration-300 ease-ui', fading ? 'opacity-0' : 'opacity-100')}>
        <figcaption className="text-micro uppercase text-text-2">{s.criterion}</figcaption>
        <blockquote className="text-[20px] leading-snug text-text-1">
          {s.quote ? <span className="proof-wash">“{s.quote}”</span> : <span className="text-text-2">No evidence found</span>}
          {s.quote ? (
            <span className="ml-3 inline-flex items-center gap-1.5 whitespace-nowrap align-middle text-micro uppercase text-text-2">
              <svg aria-hidden viewBox="0 0 12 12" className="tick size-3 text-ok" style={{ '--d': '900ms' } as React.CSSProperties}>
                <path d="M2 6.5 5 9.5 10 3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" pathLength={1} />
              </svg>
              Verified in CV
            </span>
          ) : (
            <span className="ml-3 inline-flex items-center whitespace-nowrap rounded-pill border border-dashed px-2.5 py-0.5 align-middle text-micro uppercase text-text-2">A person reads this CV</span>
          )}
        </blockquote>
      </figure>
      <p className="text-micro text-text-2">Live demo, synthetic data</p>
    </div>
  )
}

function SignInCard({ form }: { form: UseFormReturn<Values> }) {
  const login = useLogin()
  const navigate = useNavigate()
  const { register, handleSubmit, setValue, formState: { errors } } = form
  return (
    <GlassPanel strong className="space-y-4 p-5 max-sm:backdrop-blur-none">
      <div className="space-y-1"><h2>Sign in</h2><p className="text-small text-text-2">Use your FairRank account.</p></div>
      <form className="space-y-3.5" noValidate onSubmit={handleSubmit((values) => login.mutate(values, { onSuccess: (u) => navigate(homeFor(u.role), { replace: true }) }))}>
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="username" className="border-border-strong bg-glass-strong" aria-invalid={!!errors.email} {...register('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" className="border-border-strong bg-glass-strong" aria-invalid={!!errors.password} {...register('password')} />
        </Field>
        {login.isError && <p role="alert" className="text-small text-bad">{login.error.message}</p>}
        {/* on a phone the primary action is pinned to the bottom edge so it is always in thumb reach */}
        <div className="max-sm:fixed max-sm:inset-x-0 max-sm:bottom-0 max-sm:z-30 max-sm:border-t max-sm:bg-bg-base max-sm:px-(--gutter) max-sm:pb-[calc(0.75rem+var(--safe-bottom))] max-sm:pt-3">
          <Button type="submit" arrow size="lg" className="w-full" loading={login.isPending}>
            {login.isPending ? 'Signing in' : 'Sign in'}
          </Button>
        </div>
      </form>
      {DEMO_MODE && (
        <div className="flex flex-wrap items-center gap-2 border-t pt-3.5">
          <span className="text-micro uppercase text-text-2">Demo</span>
          {DEMO_ACCOUNTS.map((a) => (
            <button
              key={a.email}
              type="button"
              className="inline-flex h-9 items-center rounded-pill border border-border-strong px-3.5 text-small transition-colors duration-(--dur-fast) hover:bg-glass-strong"
              onClick={() => {
                setValue('email', a.email, { shouldValidate: true })
                setValue('password', DEMO_PASSWORD, { shouldValidate: true })
              }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </GlassPanel>
  )
}

export function LoginPage() {
  const { data: user } = useMe()
  const [dialog, setDialog] = useState<'screen' | 'privacy' | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema) })
  if (user) return <Navigate to={homeFor(user.role)} replace />

  return (
    <div className="min-h-dvh p-(--frame-margin)">
      <div className="showcase-canvas flex min-h-[calc(100dvh-var(--frame-margin)*2)] flex-col gap-6 px-(--gutter) py-5 max-sm:pb-28 md:py-6">
        <div aria-hidden className="showcase-bloom" />
        <header className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-body font-medium">
            <span className="grid size-9 place-items-center rounded-pill border bg-glass"><ShieldCheck className="size-4" aria-hidden /></span>
            <span className="hidden sm:inline">FairRank</span>
          </p>
          <PillNav items={[{ label: 'How we screen', onClick: () => setDialog('screen') }, { label: 'Privacy', onClick: () => setDialog('privacy') }]} />
          <span className="size-9 max-sm:hidden" aria-hidden />
        </header>

        <main className="grid flex-1 content-center gap-8 max-lg:gap-10 lg:mt-12 lg:grid-cols-[1fr_24rem] lg:items-center lg:gap-x-16">
          <div className="relative z-10 space-y-6">
            <h1 className="text-hero text-text-1">
              Hiring that shows <span className="draw-underline">its work.</span>
            </h1>
            <p className="max-w-sm text-balance text-small text-text-2">Every score quotes the CV. Low scorers are labelled, never hidden, and nobody is auto-rejected.</p>
            <ProofLine />
          </div>
          <SignInCard form={form} />
        </main>

        <footer className="space-y-5">
          <HairlineRule />
          <FairnessPanel variant="strip" />
        </footer>
      </div>

      <Dialog open={dialog === 'screen'} onClose={() => setDialog(null)} title="How we screen" description="What the AI does, what it does not do, and how we keep it fair.">
        <FairnessPanel />
      </Dialog>
      <Dialog open={dialog === 'privacy'} onClose={() => setDialog(null)} title="Privacy" description="CVs are personal data under the DPDP Act 2023.">
        <ul className="space-y-3 text-small text-text-2">
          {[
            'A consent entry is recorded for every candidate, and CVs are used for hiring only.',
            'On request, we delete the CV file, extracted text and parsed fields. A tombstone (ID and date) is kept.',
            'Every view of a profile or CV is logged: who, what and when.',
            'Each client sees only the candidates submitted to them, with contact details masked until the interview stage.',
          ].map((t) => (
            <li key={t} className="flex gap-2"><Info className="mt-0.5 size-4 shrink-0 text-text-1" aria-hidden />{t}</li>
          ))}
        </ul>
      </Dialog>
    </div>
  )
}
