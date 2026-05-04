import { useMemo, useState } from 'react'
import './App.css'

type FamiliarityRating = 'unknown' | 'weak' | 'okay' | 'strong'
type LoadingState = 'analysis' | 'plan' | null

type TargetConcept = {
  id: string
  title: string
  summary: string
  evidence: string[]
}

type PrerequisiteConcept = {
  id: string
  title: string
  why_it_matters: string
  supports: string[]
  evidence: string[]
}

type FamiliarityCheck = {
  concept_id: string
  prompt: string
}

type AnalyzeMaterialResponse = {
  target_concepts: TargetConcept[]
  prerequisites: PrerequisiteConcept[]
  familiarity_checks: FamiliarityCheck[]
}

type Gap = {
  concept_id: string
  title: string
  severity: 'high' | 'medium' | 'low'
  why_it_blocks_learning: string
  next_step: string
}

type ScaffoldPlanResponse = {
  gaps: Gap[]
  study_sequence: string[]
  confidence_notes: string[]
}

const API_BASE = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/\/$/, '')

const sampleMaterial =
  'When differentiating a composite function such as sin(x^2), the chain rule says to take the derivative of the outside function while keeping the inside expression fixed, then multiply by the derivative of the inside expression. This lets us calculate rates of change for nested functions that appear throughout college calculus.'

const ratings: { value: FamiliarityRating; label: string }[] = [
  { value: 'unknown', label: 'Unknown' },
  { value: 'weak', label: 'Weak' },
  { value: 'okay', label: 'Okay' },
  { value: 'strong', label: 'Strong' },
]

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = payload?.detail ? formatErrorDetail(payload.detail) : `Request failed with HTTP ${response.status}`
    throw new Error(detail)
  }

  return (await response.json()) as T
}

function formatErrorDetail(detail: unknown): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'object' && item !== null && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        return String(item)
      })
      .join(' ')
  }
  return String(detail)
}

function App() {
  const [material, setMaterial] = useState(sampleMaterial)
  const [subject, setSubject] = useState('Calculus')
  const [level, setLevel] = useState('college')
  const [analysis, setAnalysis] = useState<AnalyzeMaterialResponse | null>(null)
  const [familiarity, setFamiliarity] = useState<Record<string, FamiliarityRating>>({})
  const [plan, setPlan] = useState<ScaffoldPlanResponse | null>(null)
  const [loading, setLoading] = useState<LoadingState>(null)
  const [error, setError] = useState<string | null>(null)

  const materialLength = material.trim().length
  const canAnalyze = materialLength >= 80 && loading === null
  const canPlan = analysis !== null && loading === null

  const conceptTitleById = useMemo(() => {
    const titles: Record<string, string> = {}
    analysis?.target_concepts.forEach((concept) => {
      titles[concept.id] = concept.title
    })
    analysis?.prerequisites.forEach((concept) => {
      titles[concept.id] = concept.title
    })
    return titles
  }, [analysis])

  async function analyzeMaterial() {
    setLoading('analysis')
    setError(null)
    setPlan(null)

    try {
      const nextAnalysis = await postJson<AnalyzeMaterialResponse>('/api/analyze-material', {
        material: material.trim(),
        subject: subject.trim() || undefined,
        level: level.trim() || undefined,
      })
      const nextFamiliarity = Object.fromEntries(
        nextAnalysis.familiarity_checks.map((check) => [check.concept_id, 'unknown' as FamiliarityRating]),
      )

      setAnalysis(nextAnalysis)
      setFamiliarity(nextFamiliarity)
    } catch (err) {
      setAnalysis(null)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(null)
    }
  }

  async function buildPlan() {
    if (!analysis) return
    setLoading('plan')
    setError(null)

    try {
      const nextPlan = await postJson<ScaffoldPlanResponse>('/api/scaffold-plan', {
        analysis,
        ratings: familiarity,
      })
      setPlan(nextPlan)
    } catch (err) {
      setPlan(null)
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(null)
    }
  }

  function setRating(conceptId: string, rating: FamiliarityRating) {
    setFamiliarity((current) => ({ ...current, [conceptId]: rating }))
  }

  return (
    <main className="app-shell">
      <section className="intro-band">
        <div>
          <p className="eyebrow">Keystone AI</p>
          <h1>Find the missing foundations behind hard STEM material.</h1>
        </div>
        <div className="status-pill">Session only</div>
      </section>

      <section className="workspace">
        <form
          className="input-panel"
          onSubmit={(event) => {
            event.preventDefault()
            void analyzeMaterial()
          }}
        >
          <div className="panel-heading">
            <p className="step-label">1. Material</p>
            <span>{materialLength} chars</span>
          </div>

          <label>
            Study material
            <textarea
              value={material}
              onChange={(event) => setMaterial(event.target.value)}
              minLength={80}
              placeholder="Paste a textbook excerpt, lecture note, or problem explanation."
            />
          </label>

          <div className="field-row">
            <label>
              Subject
              <input value={subject} onChange={(event) => setSubject(event.target.value)} />
            </label>
            <label>
              Level
              <input value={level} onChange={(event) => setLevel(event.target.value)} />
            </label>
          </div>

          {materialLength < 80 && (
            <p className="inline-warning">Add a little more material so Keystone has enough context.</p>
          )}

          <button className="primary-action" type="submit" disabled={!canAnalyze}>
            {loading === 'analysis' ? 'Analyzing...' : 'Analyze foundations'}
          </button>
        </form>

        <section className="insight-panel" aria-live="polite">
          <div className="panel-heading">
            <p className="step-label">2. Scaffold</p>
            <span>{analysis ? `${analysis.prerequisites.length} prerequisites` : 'Waiting for material'}</span>
          </div>

          {error && <div className="error-box">{error}</div>}

          {!analysis && !error && (
            <div className="empty-state">
              <h2>Paste material to reveal the prerequisite map.</h2>
              <p>Keystone will extract target ideas, infer foundations, and ask quick self-checks.</p>
            </div>
          )}

          {analysis && (
            <div className="analysis-grid">
              <section>
                <h2>Target concepts</h2>
                <div className="concept-list">
                  {analysis.target_concepts.map((concept) => (
                    <article className="concept-card" key={concept.id}>
                      <h3>{concept.title}</h3>
                      <p>{concept.summary}</p>
                      <small>{concept.evidence.join(' ')}</small>
                    </article>
                  ))}
                </div>
              </section>

              <section>
                <h2>Prerequisite checks</h2>
                <div className="check-list">
                  {analysis.familiarity_checks.map((check) => (
                    <article className="check-row" key={check.concept_id}>
                      <div>
                        <h3>{conceptTitleById[check.concept_id] ?? check.concept_id}</h3>
                        <p>{check.prompt}</p>
                      </div>
                      <div className="rating-group" aria-label={`Rate ${check.concept_id}`}>
                        {ratings.map((rating) => (
                          <button
                            className={familiarity[check.concept_id] === rating.value ? 'selected' : ''}
                            key={rating.value}
                            type="button"
                            onClick={() => setRating(check.concept_id, rating.value)}
                          >
                            {rating.label}
                          </button>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
                <button className="primary-action" type="button" disabled={!canPlan} onClick={() => void buildPlan()}>
                  {loading === 'plan' ? 'Building plan...' : 'Build study scaffold'}
                </button>
              </section>
            </div>
          )}
        </section>
      </section>

      {plan && (
        <section className="results-band">
          <div className="panel-heading">
            <p className="step-label">3. Gap map</p>
            <span>{plan.gaps.length} ranked blockers</span>
          </div>

          <div className="results-grid">
            <section>
              <h2>Likely blockers</h2>
              <div className="gap-list">
                {plan.gaps.map((gap) => (
                  <article className={`gap-card severity-${gap.severity}`} key={gap.concept_id}>
                    <div>
                      <span>{gap.severity}</span>
                      <h3>{gap.title}</h3>
                    </div>
                    <p>{gap.why_it_blocks_learning}</p>
                    <strong>{gap.next_step}</strong>
                  </article>
                ))}
              </div>
            </section>

            <section>
              <h2>Study sequence</h2>
              <ol className="sequence-list">
                {plan.study_sequence.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>

              <h2>Confidence notes</h2>
              <ul className="note-list">
                {plan.confidence_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </section>
          </div>
        </section>
      )}
    </main>
  )
}

export default App
