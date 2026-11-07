import { zodResolver } from '@hookform/resolvers/zod'
import { Info, KeyRound, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { EvidenceQuote } from '@/components/ui/evidence-quote'
import { FairnessPanel } from '@/components/ui/fairness-panel'
import { Field } from '@/components/ui/field'
import { GlassPanel, HairlineRule } from '@/components/ui/glass-panel'
import { Input } from '@/components/ui/input'
import { PillNav } from '@/components/ui/pill-nav'
import { ScoreRing } from '@/components/ui/score-ring'
import { homeFor, useLogin, useMe } from '@/lib/auth'
import { DEMO_ACCOUNTS, DEMO_ENABLED, DEMO_PASSWORD } from '@/lib/demo'

const schema = z.object({
  email: z.string().min(1, 'Enter your email').email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

/** Synthetic sample: shows what a screened candidate looks like. Name is hidden while scoring (blind scoring). */
function ProofPanel() {
  return (
    <GlassPanel rule className="space-y-4 p-5 pt-6">
      <div className="flex items-center gap-4">
        <ScoreRing value={82} band="strong" size="md" />
        <div className="min-w-0">
          <p className="text-micro uppercase text-text-2">Sample · CND-91022 · name hidden</p>
          <p className="text-body font-medium">Senior Java Developer</p>
          <p className="text-small text-text-2"><span className="tnum">6.5</span> yrs · notice <span className="tnum">60</span> days · Noida</p>
        </div>
      </div>
      <EvidenceQuote criterion="Spring Boot" quote="Built and maintained 12 Spring Boot microservices" status="verified" />
      <EvidenceQuote criterion="Notice period" quote="Notice Period: 60 days" status="verified" />
    </GlassPanel>
  )
}

function SignInCard({ showDemo }: { showDemo: boolean }) {
  const login = useLogin()
  const navigate = useNavigate()
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<Values>({ resolver: zodResolver(schema) })
  return (
    <GlassPanel strong className="space-y-5 p-6" >
      <div className="space-y-1">
        <h2>Sign in to FairRank</h2>
        <p className="text-small text-text-2">Screening with evidence, never auto-rejection.</p>
      </div>
      <form
        className="space-y-4"
        noValidate
        onSubmit={handleSubmit((values) => login.mutate(values, { onSuccess: (u) => navigate(homeFor(u.role), { replace: true }) }))}
      >
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input id="email" type="email" autoComplete="username" className="bg-glass" aria-invalid={!!errors.email} {...register('email')} />
        </Field>
        <Field label="Password" htmlFor="password" error={errors.password?.message}>
          <Input id="password" type="password" autoComplete="current-password" className="bg-glass" aria-invalid={!!errors.password} {...register('password')} />
        </Field>
        {login.isError && <p role="alert" className="text-small text-bad">{login.error.message}</p>}
        <Button type="submit" arrow size="lg" className="w-full" disabled={login.isPending}>
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>
      {showDemo && (
        <div className="space-y-2 border-t pt-4">
          <p className="text-micro uppercase text-text-2">Demo accounts (synthetic)</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_ACCOUNTS.map((a) => (
              <Button
                key={a.email}
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setValue('email', a.email, { shouldValidate: true })
                  setValue('password', DEMO_PASSWORD, { shouldValidate: true })
                }}
              >
                {a.label}
              </Button>
            ))}
          </div>
        </div>
      )}
    </GlassPanel>
  )
}

export function LoginPage() {
  const { data: user } = useMe()
  const [dialog, setDialog] = useState<'screen' | 'privacy' | null>(null)
  const [demo, setDemo] = useState(true)
  if (user) return <Navigate to={homeFor(user.role)} replace />

  return (
    <div className="min-h-dvh p-(--frame-margin)">
      <div className="showcase-canvas flex min-h-[calc(100dvh-var(--frame-margin)*2)] flex-col gap-8 px-(--gutter) py-5 md:py-6">
        <header className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-body font-medium">
            <span className="grid size-9 place-items-center rounded-pill border bg-glass"><ShieldCheck className="size-4" aria-hidden /></span>
            <span className="hidden sm:inline">FairRank</span>
          </p>
          <PillNav
            items={[
              { label: 'How we screen', onClick: () => setDialog('screen') },
              { label: 'Privacy', onClick: () => setDialog('privacy') },
            ]}
          />
          <div className="flex size-9 items-center justify-end">
            {DEMO_ENABLED && (
              <Button variant="secondary" size="icon-sm" aria-label="Demo accounts" aria-pressed={demo} className="bg-glass" onClick={() => setDemo((d) => !d)}>
                <KeyRound />
              </Button>
            )}
          </div>
        </header>

        <main className="grid flex-1 gap-6 lg:grid-cols-[1fr_26rem] lg:grid-rows-[auto_1fr] lg:gap-x-12">
          <div className="space-y-5 lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:self-end">
            <h1 className="text-display">Hiring that shows its work.</h1>
            <p className="max-w-md text-small text-text-2">Every score quotes the CV. Low scorers are labelled, never hidden, and nobody is auto-rejected.</p>
          </div>
          <div className="lg:col-start-2 lg:row-start-2">
            <SignInCard showDemo={DEMO_ENABLED && demo} />
          </div>
          <div className="lg:col-start-2 lg:row-start-1">
            <ProofPanel />
          </div>
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
          <li className="flex gap-2"><Info className="mt-0.5 size-4 shrink-0 text-text-1" aria-hidden />A consent entry is recorded for every candidate, and CVs are used for hiring only.</li>
          <li className="flex gap-2"><Info className="mt-0.5 size-4 shrink-0 text-text-1" aria-hidden />On request, we delete the CV file, extracted text and parsed fields. A tombstone (ID and date) is kept.</li>
          <li className="flex gap-2"><Info className="mt-0.5 size-4 shrink-0 text-text-1" aria-hidden />Every view of a profile or CV is logged: who, what and when.</li>
          <li className="flex gap-2"><Info className="mt-0.5 size-4 shrink-0 text-text-1" aria-hidden />Each client sees only the candidates submitted to them, with contact details masked until the interview stage.</li>
        </ul>
      </Dialog>
    </div>
  )
}
