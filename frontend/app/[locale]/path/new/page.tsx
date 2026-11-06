"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { Check } from "lucide-react";
import { motion } from "motion/react";
import { AppShell } from "@/components/AppShell";
import { Button, buttonClass } from "@/components/ui/Button";
import { inputClass } from "@/components/ui/FormField";
import { PageHeader } from "@/components/ui/primitives";
import { cn } from "@/lib/cn";
import { PathBuildingStage } from "@/components/path/PathBuildingStage";
import { PlacementPreparing } from "@/components/path/PlacementPreparing";
import { PrimerMarkdown } from "@/components/learn/PrimerMarkdown";
import {
  answerFor,
  generatePlacement,
  getMe,
  gradePlacement,
  inferSubjectProfile,
  ingestPath,
  isProfileComplete,
  needsGuardianConsent,
  parsePathUpload,
  type PlacementQuestion,
  type SubjectCategory,
  type SubjectNotation,
  type SubjectProfile,
} from "@/lib/api";
import { MathField } from "@/components/math/MathField";
import { MathText } from "@/components/math/MathText";
import { createClient, useTokenRefresh } from "@/lib/supabase/client";

type HorizonId = "1m" | "2m" | "3m" | "6m" | "custom";
type WizardStep = 1 | 2 | 3;

const CATEGORIES: SubjectCategory[] = ["core", "math", "science", "language", "humanities", "code", "media"];
const NOTATIONS: SubjectNotation[] = ["none", "math", "chem", "code"];

const HORIZONS: { id: HorizonId; months: number | null }[] = [
  { id: "1m", months: 1 },
  { id: "2m", months: 2 },
  { id: "3m", months: 3 },
  { id: "6m", months: 6 },
  { id: "custom", months: null },
];

const BUDGET_OPTIONS = [15, 20, 30, 45, 60] as const;
const EST_TOTAL_MINS = 240;

function addMonthsISO(months: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

function recommendBudget(deadlineISO: string | null): number {
  if (!deadlineISO) return 30;
  const days = Math.max(
    7,
    Math.ceil((new Date(deadlineISO).getTime() - Date.now()) / 86_400_000),
  );
  const raw = Math.ceil(EST_TOTAL_MINS / days);
  const rounded = Math.round(raw / 5) * 5;
  return Math.min(60, Math.max(15, rounded));
}

function budgetTone(mins: number): "light" | "steady" | "deep" {
  if (mins <= 20) return "light";
  if (mins <= 35) return "steady";
  return "deep";
}

export default function PathNewPage() {
  const t = useTranslations("pathNew");
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  useTokenRefresh(setToken);
  const [step, setStep] = useState<WizardStep>(1);
  const [goal, setGoal] = useState("");
  const [horizon, setHorizon] = useState<HorizonId>("2m");
  const [customDate, setCustomDate] = useState("");
  const [pickedBudget, setBudget] = useState(30);
  const [usedRecommend, setUsedRecommend] = useState(false);
  const [examText, setExamText] = useState("");
  const [placementNotes, setPlacementNotes] = useState("");
  const [placementQs, setPlacementQs] = useState<PlacementQuestion[]>([]);
  const [placementAnswers, setPlacementAnswers] = useState<Record<string, string>>({});
  const [placementScore, setPlacementScore] = useState<string | null>(null);
  const [placementWeak, setPlacementWeak] = useState<string[]>([]);
  const [sourceTexts, setSourceTexts] = useState<string[]>([]);
  const [useCorpus, setUseCorpus] = useState(true);
  const [busy, setBusy] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [examBusy, setExamBusy] = useState(false);
  const [examPhase, setExamPhase] = useState<"idle" | "generating" | "grading">("idle");
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<SubjectProfile | null>(null);
  const [profileState, setProfileState] = useState<"idle" | "loading" | "error">("idle");
  const profileRef = useRef<HTMLElement>(null);
  const autoStarted = useRef(false);
  const confirmedProfile =
    profile?.allowed ? { ...profile, subject: profile.subject.trim() } : null;

  // Move keyboard focus to the "We think this is…" card when a fresh profile lands.
  useEffect(() => {
    if (profileState === "idle") profileRef.current?.focus();
  }, [profileState]);

  const deadlineISO = useMemo(() => {
    const h = HORIZONS.find((x) => x.id === horizon);
    if (h?.months) return addMonthsISO(h.months);
    return customDate || null;
  }, [horizon, customDate]);

  const recommended = useMemo(() => recommendBudget(deadlineISO), [deadlineISO]);
  // Follows the recommendation until the learner picks a budget.
  const budget = usedRecommend ? pickedBudget : recommended;

  useEffect(() => {
    (async () => {
      const supabase = createClient();
      const { data } = await supabase.auth.getSession();
      const tok = data.session?.access_token;
      if (!tok) {
        router.replace("/signin");
        return;
      }
      try {
        const me = await getMe(tok);
        if (!isProfileComplete(me)) {
          router.replace("/age");
          return;
        }
        if (needsGuardianConsent(me)) {
          router.replace("/consent");
          return;
        }
        setToken(tok);
      } catch (e) {
        setError(e instanceof Error ? e.message : t("error"));
      }
    })();
  }, [router, t]);

  async function startPlacement() {
    if (!token || !goal.trim() || examBusy) return;
    setExamBusy(true);
    setExamPhase("generating");
    setError(null);
    setPlacementScore(null);
    setPlacementWeak([]);
    setExamText("");
    try {
      const res = await generatePlacement(token, goal.trim(), confirmedProfile);
      setPlacementQs(res.questions);
      setPlacementAnswers({});
    } catch (e) {
      setError(e instanceof Error ? e.message : t("examError"));
      autoStarted.current = false;
    } finally {
      setExamBusy(false);
      setExamPhase("idle");
    }
  }

  // Auto-start when entering exam step (once per visit to step 2)
  useEffect(() => {
    if (step !== 2 || !token || !goal.trim()) return;
    if (placementQs.length || examText || examBusy || autoStarted.current) return;
    autoStarted.current = true;
    void startPlacement();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally once on step enter
  }, [step, token]);

  async function onParseFile(file: File | null) {
    if (!file || !token) return;
    setParsing(true);
    setError(null);
    try {
      const res = await parsePathUpload(token, file);
      setSourceTexts((prev) => [...prev, res.text].slice(0, 5));
    } catch (e) {
      setError(e instanceof Error ? e.message : t("parseError"));
    } finally {
      setParsing(false);
    }
  }

  async function finishPlacement() {
    if (!token || !placementQs.length) return;
    setExamBusy(true);
    setExamPhase("grading");
    setError(null);
    try {
      const graded = await gradePlacement(token, {
        questions: placementQs,
        answers: placementQs.map((q) => ({
          id: q.id,
          answer: answerFor(q.parts[0]?.grader, placementAnswers[q.id] ?? ""),
        })),
      });
      setExamText(graded.summary_markdown);
      setPlacementScore(
        t("examScore", { correct: graded.correct_count, total: graded.total }),
      );
      setPlacementWeak(graded.weak_skills || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("examError"));
    } finally {
      setExamBusy(false);
      setExamPhase("idle");
    }
  }

  function validateStep1(): boolean {
    if (goal.trim().length < 3) {
      setError(t("needGoal"));
      return false;
    }
    if (!deadlineISO && !budget) {
      setError(t("needConstraint"));
      return false;
    }
    if (horizon === "custom" && !customDate) {
      setError(t("needDate"));
      return false;
    }
    setError(null);
    return true;
  }

  async function inferProfile() {
    if (!token || profileState === "loading" || !validateStep1()) return;
    setProfileState("loading");
    try {
      setProfile(await inferSubjectProfile(token, { goal_text: goal.trim() }));
      setProfileState("idle");
    } catch {
      setProfileState("error");
    }
  }

  function goToExam() {
    autoStarted.current = false;
    setStep(2);
  }

  async function onSubmit() {
    if (!token || busy) return;
    if (!validateStep1()) {
      setStep(1);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const notes = placementNotes.trim();
      const examParts = [
        examText.trim(),
        notes ? `## Learner notes\n${notes}` : "",
      ].filter(Boolean);
      const res = await ingestPath(token, {
        goal_text: goal.trim(),
        deadline_date: deadlineISO,
        daily_budget_mins: budget,
        exam_markdown: examParts.length ? examParts.join("\n\n") : null,
        source_markdowns: sourceTexts.filter((s) => s.trim()),
        use_corpus: useCorpus,
        subject_profile: confirmedProfile,
      });
      router.push(`/path/${res.path_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("error"));
      setBusy(false);
    }
  }

  const deadlineLabel = deadlineISO
    ? new Date(deadlineISO + "T12:00:00").toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : null;

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-xl">
        <PageHeader title={t("title")} description={t("subtitle")} className="mb-6 sm:mb-6" />

        <ol className="mb-6 grid grid-cols-3 gap-2">
          {([1, 2, 3] as WizardStep[]).map((s) => (
            <li key={s} aria-current={step === s ? "step" : undefined} className="space-y-2">
              <div className={cn("h-1 rounded-full transition-colors", s <= step ? "bg-neuro-indigo" : "bg-white/5")} />
              <p
                className={cn(
                  "flex items-center gap-1 font-mono text-micro uppercase tracking-wider",
                  step === s ? "text-slate-100" : s < step ? "text-neuro-teal" : "text-slate-600",
                )}
              >
                {s < step && <Check className="h-3 w-3" aria-hidden />}
                {t(`step${s}`)}
              </p>
            </li>
          ))}
        </ol>

        {!busy ? (
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
            className="space-y-8 rounded-panel border border-line bg-surface-glass p-5 backdrop-blur-xl sm:p-7"
          >
            {step === 1 && (
              <>
                <section className="space-y-2">
                  <label htmlFor="goal" className="block font-display text-base font-semibold text-slate-100">
                    {t("goal")}
                  </label>
                  <p className="text-xs text-slate-500">{t("goalHint")}</p>
                  <textarea
                    id="goal"
                    value={goal}
                    onChange={(e) => {
                      setGoal(e.target.value);
                      setProfile(null);
                      setProfileState("idle");
                    }}
                    rows={3}
                    maxLength={500}
                    placeholder={t("goalPlaceholder")}
                    className="w-full resize-none rounded-control border border-line-strong bg-background/60 px-3.5 py-3 text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-neuro-indigo focus:ring-2 focus:ring-neuro-indigo/40"
                    required
                  />
                </section>

                <section className="space-y-3">
                  <div>
                    <h2 className="font-display text-base font-semibold text-slate-100">{t("horizonTitle")}</h2>
                    <p className="mt-1 text-xs text-slate-500">{t("horizonHint")}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {HORIZONS.map((h) => {
                      const selected = horizon === h.id;
                      return (
                        <button
                          key={h.id}
                          type="button"
                          onClick={() => {
                            setHorizon(h.id);
                            setUsedRecommend(false);
                          }}
                          className={`min-h-12 rounded-control border px-3 py-2.5 text-left text-sm transition ${
                            selected
                              ? "border-indigo-400/60 bg-neuro-indigo/15 text-slate-50 ring-1 ring-indigo-400/40"
                              : "border-line-strong bg-surface-raised text-slate-300 hover:border-slate-500"
                          }`}
                        >
                          <span className="block font-medium">{t(`horizon_${h.id}`)}</span>
                        </button>
                      );
                    })}
                  </div>
                  {horizon === "custom" && (
                    <label className="block text-xs text-slate-400">
                      {t("customDate")}
                      <input
                        type="date"
                        value={customDate}
                        min={new Date().toISOString().slice(0, 10)}
                        onChange={(e) => {
                          setCustomDate(e.target.value);
                          setUsedRecommend(false);
                        }}
                        className="mt-1.5 w-full rounded-control border border-line-strong bg-background/60 px-3 py-2.5 text-sm text-slate-100 outline-none focus:border-neuro-indigo"
                      />
                    </label>
                  )}
                </section>

                <section className="space-y-3">
                  <div className="flex flex-wrap items-end justify-between gap-2">
                    <div>
                      <h2 className="font-display text-base font-semibold text-slate-100">{t("budgetTitle")}</h2>
                      <p className="mt-1 text-xs text-slate-500">{t("budgetHint")}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        setBudget(recommended);
                        setUsedRecommend(true);
                      }}
                      className="min-h-10 rounded-full border border-teal-400/30 bg-teal-500/10 px-3.5 py-1.5 text-xs font-medium text-teal-200 hover:bg-teal-500/15"
                    >
                      {t("useRecommend", { mins: recommended })}
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {BUDGET_OPTIONS.map((mins) => {
                      const selected = budget === mins;
                      const tone = budgetTone(mins);
                      return (
                        <button
                          key={mins}
                          type="button"
                          onClick={() => {
                            setBudget(mins);
                            setUsedRecommend(true);
                          }}
                          className={`min-h-12 min-w-[4.5rem] flex-1 rounded-control border px-3 py-2 transition text-center sm:flex-none ${
                            selected
                              ? "border-indigo-400/60 bg-neuro-indigo/15 text-slate-50 ring-1 ring-indigo-400/40"
                              : "border-line-strong bg-surface-raised text-slate-300 hover:border-slate-500"
                          }`}
                        >
                          <span className="block font-mono text-base font-semibold">{mins}</span>
                          <span className="block text-[10px] uppercase tracking-wider text-slate-500">
                            {t("mins")}
                          </span>
                          <span className="mt-0.5 block text-xs text-slate-400">
                            {t(`pace_${tone}`)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </section>

                {profile ? (
                  <section
                    ref={profileRef}
                    tabIndex={-1}
                    aria-labelledby="profile-title"
                    className="space-y-4 rounded-control border border-indigo-400/30 bg-neuro-indigo/5 p-4 outline-none focus-visible:ring-2 focus-visible:ring-neuro-indigo/40"
                  >
                    <h2 id="profile-title" className="font-display text-base font-semibold text-slate-100">
                      {t("profileTitle")}
                    </h2>
                    {!profile.allowed ? (
                      <p role="alert" className="text-sm text-neuro-alert">
                        {profile.reason || t("profileRefused")}
                      </p>
                    ) : (
                      <>
                        <p className="text-xs text-slate-500">{t("profileHint")}</p>
                        <label className="block space-y-1.5 text-sm text-slate-300">
                          <span>{t("profileSubject")}</span>
                          <input
                            value={profile.subject}
                            maxLength={120}
                            required
                            onChange={(e) => setProfile({ ...profile, subject: e.target.value })}
                            className={inputClass}
                          />
                        </label>
                        <div role="group" aria-labelledby="profile-categories" className="space-y-1.5">
                          <p id="profile-categories" className="text-sm text-slate-300">
                            {t("profileCategories")}
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {CATEGORIES.map((c) => {
                              const on = c === "core" || profile.categories.includes(c);
                              return (
                                <button
                                  key={c}
                                  type="button"
                                  aria-pressed={on}
                                  disabled={c === "core"}
                                  onClick={() =>
                                    setProfile({
                                      ...profile,
                                      categories: on
                                        ? profile.categories.filter((x) => x !== c)
                                        : [...profile.categories, c],
                                    })
                                  }
                                  className={cn(
                                    "min-h-10 rounded-full border px-3.5 py-1.5 text-xs font-medium transition disabled:cursor-default",
                                    on
                                      ? "border-indigo-400/60 bg-neuro-indigo/15 text-slate-50"
                                      : "border-line-strong bg-surface-raised text-slate-300 hover:border-slate-500",
                                  )}
                                >
                                  {on && <Check className="mr-1 inline h-3 w-3" aria-hidden />}
                                  {t(`profileCat_${c}`)}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                        <fieldset className="space-y-1.5">
                          <legend className="mb-1.5 text-sm text-slate-300">{t("profileNotation")}</legend>
                          <div className="grid grid-cols-2 gap-1 rounded-control border border-line-strong bg-background/60 p-1 sm:grid-cols-4">
                            {NOTATIONS.map((n) => (
                              <label
                                key={n}
                                className="flex min-h-10 cursor-pointer items-center justify-center rounded-[calc(var(--radius-control)-4px)] px-2 text-sm text-slate-300 transition has-checked:bg-neuro-indigo/20 has-checked:text-slate-50 has-focus-visible:ring-2 has-focus-visible:ring-neuro-indigo/60"
                              >
                                <input
                                  type="radio"
                                  name="profile-notation"
                                  value={n}
                                  checked={profile.notation === n}
                                  onChange={() => setProfile({ ...profile, notation: n })}
                                  className="sr-only"
                                />
                                {t(`profileNotation_${n}`)}
                              </label>
                            ))}
                          </div>
                        </fieldset>
                      </>
                    )}
                    <Button
                      block
                      disabled={!profile.allowed || !profile.subject.trim()}
                      onClick={goToExam}
                    >
                      {t("profileAccept")}
                    </Button>
                  </section>
                ) : profileState === "error" ? (
                  <div className="space-y-3 rounded-control border border-rose-400/30 bg-rose-500/5 p-4">
                    <p role="alert" className="text-sm text-slate-300">
                      {t("profileError")}
                    </p>
                    <div className="flex gap-2">
                      <Button variant="secondary" className="flex-1" onClick={() => void inferProfile()}>
                        {t("profileRetry")}
                      </Button>
                      <Button variant="ghost" className="flex-1" onClick={goToExam}>
                        {t("profileSkip")}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <Button block loading={profileState === "loading"} onClick={() => void inferProfile()}>
                    {profileState === "loading" ? t("profileLoading") : t("next")}
                  </Button>
                )}
              </>
            )}

            {step === 2 && (
              <>
                <section className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-display text-base font-semibold text-slate-100">{t("examTitle")}</h2>
                    <span className="rounded-full border border-teal-400/30 bg-teal-500/10 px-2 py-0.5 font-mono text-micro uppercase tracking-wider text-teal-200">
                      {t("recommended")}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500">{t("examHint")}</p>

                  {(examPhase === "generating" ||
                    (examBusy && !placementQs.length && !examText)) && (
                    <PlacementPreparing label={t("examGenerating")} />
                  )}

                  {examPhase === "grading" && (
                    <PlacementPreparing label={t("examGrading")} />
                  )}

                  {placementQs.length > 0 && !examText && examPhase !== "grading" && (
                    <div className="space-y-4">
                      <p className="text-xs text-slate-500">{t("examRampHint")}</p>
                      {placementQs.map((q, i) => {
                        const part = q.parts[0];
                        const grader = part?.grader;
                        const choices = Array.isArray(part?.props.choices)
                          ? (part?.props.choices as { id: string; label: string }[])
                          : [];
                        const unit = typeof part?.props.unit === "string" ? part?.props.unit : null;
                        const value = placementAnswers[q.id] ?? "";
                        const setValue = (v: string) =>
                          setPlacementAnswers((prev) => ({ ...prev, [q.id]: v }));
                        return (
                          <div
                            key={q.id}
                            className="rounded-control border border-line bg-surface-raised p-4"
                          >
                            <p className="mb-1 text-[11px] text-slate-500">
                              {t("examQ", { n: i + 1 })}
                              {q.skill_hint ? (
                                <span className="text-slate-600"> · {q.skill_hint}</span>
                              ) : null}
                            </p>
                            {/* ponytail: PrimerMarkdown treats `$…$` as KaTeX, so a currency "$5 … $10" prompt mis-renders; upgrade = notation-aware markdown (MS-3.1). */}
                            {q.prompt_md ? (
                              <div className="mb-2">
                                <PrimerMarkdown source={q.prompt_md} />
                              </div>
                            ) : null}
                            {q.statement_latex ? (
                              <MathText
                                latex={q.statement_latex}
                                display
                                className="mb-3 block text-slate-100"
                              />
                            ) : null}
                            {grader === "choice" ? (
                              <fieldset className="space-y-2">
                                <legend className="sr-only">{t("examQ", { n: i + 1 })}</legend>
                                {choices.map((c) => (
                                  <label
                                    key={c.id}
                                    className="flex min-h-11 cursor-pointer items-center gap-3 rounded-control border border-line-strong bg-background/60 px-3 py-2 text-sm text-slate-200 has-checked:border-indigo-400/60 has-checked:bg-neuro-indigo/15"
                                  >
                                    <input
                                      type="radio"
                                      name={`placement-${q.id}`}
                                      value={c.id}
                                      checked={value === c.id}
                                      onChange={() => setValue(c.id)}
                                      className="h-4 w-4 accent-neuro-indigo"
                                    />
                                    {part?.props.labelsAreLatex ? <MathText latex={c.label} /> : c.label}
                                  </label>
                                ))}
                              </fieldset>
                            ) : grader === "sympy" ? (
                              <MathField value={value} onChange={setValue} virtualKeyboardMode="onfocus" />
                            ) : (
                              <label className="block space-y-1.5 text-xs text-slate-400">
                                <span>{unit ? `${t("examAnswerPlaceholder")} (${unit})` : t("examAnswerPlaceholder")}</span>
                                <input
                                  value={value}
                                  onChange={(e) => setValue(e.target.value)}
                                  inputMode={grader === "numeric" ? "decimal" : undefined}
                                  maxLength={500}
                                  autoComplete="off"
                                  className={cn(inputClass, "text-sm")}
                                />
                              </label>
                            )}
                          </div>
                        );
                      })}
                      <button
                        type="button"
                        disabled={examBusy}
                        onClick={() => void finishPlacement()}
                        className={buttonClass("success", "md", true)}
                      >
                        {t("examSubmit")}
                      </button>
                    </div>
                  )}

                  {examText && examPhase === "idle" && (
                    <div className="rounded-control border border-teal-500/25 bg-teal-500/5 p-4 text-sm text-slate-300">
                      {placementScore && (
                        <p className="mb-2 font-medium text-neuro-teal">{placementScore}</p>
                      )}
                      {placementWeak.length > 0 && (
                        <p className="mb-2 text-xs text-slate-400">
                          {t("examWeak", { skills: placementWeak.join(", ") })}
                        </p>
                      )}
                      <p className="text-xs text-slate-500">{t("examDoneHint")}</p>
                    </div>
                  )}

                  {!placementQs.length && !examText && examPhase === "idle" && !examBusy && (
                    <button
                      type="button"
                      disabled={!goal.trim()}
                      onClick={() => {
                        autoStarted.current = true;
                        void startPlacement();
                      }}
                      className={buttonClass("primary", "md", true)}
                    >
                      {error ? t("examRetry") : t("examStart")}
                    </button>
                  )}

                  {examPhase !== "generating" && examPhase !== "grading" && (
                    <div className="space-y-1.5 border-t border-line pt-4">
                      <label
                        htmlFor="placement-notes"
                        className="block font-display text-base font-semibold text-slate-100"
                      >
                        {t("examNotesTitle")}
                      </label>
                      <p className="text-xs text-slate-500">{t("examNotesHint")}</p>
                      <textarea
                        id="placement-notes"
                        value={placementNotes}
                        onChange={(e) => setPlacementNotes(e.target.value)}
                        rows={3}
                        maxLength={2000}
                        placeholder={t("examNotesPlaceholder")}
                        className="w-full resize-y rounded-control border border-line-strong bg-background/60 px-3.5 py-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-neuro-indigo"
                      />
                    </div>
                  )}
                </section>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setStep(1)}
                    className={cn(buttonClass("secondary"), "flex-1")}
                  >
                    {t("back")}
                  </button>
                  <button
                    type="button"
                    disabled={examBusy}
                    onClick={() => setStep(3)}
                    className={cn(buttonClass(), "flex-1")}
                  >
                    {examText.trim() || placementNotes.trim()
                      ? t("next")
                      : t("skipExam")}
                  </button>
                </div>
              </>
            )}

            {step === 3 && (
              <>
                <section className="space-y-3">
                  <h2 className="font-display text-base font-semibold text-slate-100">{t("sourcesTitle")}</h2>
                  <p className="text-xs text-slate-500">{t("sourcesHint")}</p>
                  <label className="flex min-h-12 cursor-pointer items-center gap-3 rounded-control border border-line-strong bg-surface-raised px-3 py-2 text-sm text-slate-200">
                    <input
                      type="checkbox"
                      checked={useCorpus}
                      onChange={(e) => setUseCorpus(e.target.checked)}
                      className="h-4 w-4 accent-neuro-indigo"
                    />
                    {t("useCorpus")}
                  </label>
                  <label className="block text-xs text-slate-400">
                    {t("uploadFile")}
                    <input
                      type="file"
                      accept=".pdf,.txt,.md,text/plain,application/pdf"
                      disabled={parsing || sourceTexts.length >= 5}
                      onChange={(e) => onParseFile(e.target.files?.[0] ?? null)}
                      className="mt-1.5 block w-full text-sm text-slate-300 file:mr-3 file:min-h-10 file:rounded-control file:border-0 file:bg-surface-raised file:px-3.5 file:text-sm file:text-slate-100 hover:file:bg-surface-subtle"
                    />
                  </label>
                  {sourceTexts.length > 0 && (
                    <ul className="space-y-1 text-xs text-slate-400">
                      {sourceTexts.map((s, i) => (
                        <li key={i} className="flex items-center justify-between gap-2">
                          <span>{t("sourceItem", { n: i + 1, chars: s.length })}</span>
                          <button
                            type="button"
                            className="min-h-10 px-2 text-slate-400 underline-offset-2 hover:text-slate-100 hover:underline"
                            onClick={() =>
                              setSourceTexts((prev) => prev.filter((_, j) => j !== i))
                            }
                          >
                            {t("remove")}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <textarea
                    placeholder={t("sourcePaste")}
                    rows={4}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (!v) return;
                      setSourceTexts((prev) => [...prev, v].slice(0, 5));
                      e.target.value = "";
                    }}
                    className="w-full resize-y rounded-control border border-line-strong bg-background/60 px-3.5 py-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus:border-neuro-indigo"
                  />
                </section>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setStep(2)}
                    className={cn(buttonClass("secondary"), "flex-1")}
                  >
                    {t("back")}
                  </button>
                  <button
                    type="button"
                    onClick={() => void onSubmit()}
                    disabled={busy || parsing}
                    className={cn(buttonClass(), "flex-1")}
                  >
                    {t("create")}
                  </button>
                </div>
              </>
            )}
          </motion.div>
        ) : (
          <PathBuildingStage
            goal={goal.trim()}
            paceLine={
              deadlineLabel
                ? t("paceSummary", {
                    mins: budget,
                    date: deadlineLabel,
                    tip: t("recommendTip", { mins: recommended }),
                  })
                : t("paceSummary", {
                    mins: budget,
                    date: t("openEnded"),
                    tip: t("recommendTip", { mins: recommended }),
                  })
            }
          />
        )}

        {error && (
          <p role="alert" className="mt-4 text-sm text-neuro-alert">
            {error}
          </p>
        )}
      </div>
    </AppShell>
  );
}
