import { FairnessPanel } from '@/components/ui/fairness-panel'
import { Dialog } from '@/components/ui/dialog'

export function HowWeScreen({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose} title="How we screen" description="What the AI does, what it does not do, and how we keep it fair.">
      <FairnessPanel />
      <p className="rounded-input bg-surface-1 p-3 text-small text-text-2">
        Scores range 0–100: Strong is 75 and above, Possible is 50–74, Weak is below 50. They help order the reading; they are a guide, not a verdict. Email and phone stay masked until a candidate reaches the interview stage.
      </p>
    </Dialog>
  )
}
