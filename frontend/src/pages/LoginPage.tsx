import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { homeFor, useLogin, useMe } from '@/lib/auth'

const schema = z.object({
  email: z.string().min(1, 'Enter your email').email('Enter a valid email'),
  password: z.string().min(1, 'Enter your password'),
})
type Values = z.infer<typeof schema>

export function LoginPage() {
  const { data: user } = useMe()
  const login = useLogin()
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) })

  if (user) return <Navigate to={homeFor(user.role)} replace />

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col items-start justify-center gap-10 p-6 md:flex-row md:items-center md:justify-between md:gap-16">
      <div className="max-w-xl space-y-5">
        <p className="text-sm tracking-wide text-muted-foreground">FairRank</p>
        <h1 className="text-5xl font-light leading-[1.05] tracking-[-0.03em] sm:text-7xl">
          Hiring that shows its work.
        </h1>
        <p className="max-w-md text-muted-foreground">
          Every score quotes the CV. Low scorers are labelled, never hidden. Nobody is auto-rejected.
        </p>
      </div>
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-xl">Sign in to FairRank</CardTitle>
          <CardDescription>Screening with evidence, never auto-rejection.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-4"
            noValidate
            onSubmit={handleSubmit((values) =>
              login.mutate(values, { onSuccess: (u) => navigate(homeFor(u.role), { replace: true }) }),
            )}
          >
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="username" aria-invalid={!!errors.email} {...register('email')} />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                aria-invalid={!!errors.password}
                {...register('password')}
              />
              {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
            </div>
            {login.isError && (
              <p role="alert" className="text-sm text-destructive">
                {login.error.message}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={login.isPending}>
              {login.isPending ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
