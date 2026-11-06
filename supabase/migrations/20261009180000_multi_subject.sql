-- Multi-subject (Doc 10 §6): additive columns + backfill so every item has parts/grader.
-- Re-runnable: every backfill only touches rows whose target column is still NULL.
-- Python twin of the item backfill: backend/app/graders/legacy.py (tests keep them equal).

ALTER TABLE public.learning_paths  ADD COLUMN IF NOT EXISTS subject_profile JSONB;
ALTER TABLE public.knowledge_nodes ADD COLUMN IF NOT EXISTS subject_profile JSONB;

ALTER TABLE public.items
  ADD COLUMN IF NOT EXISTS prompt_md      TEXT,
  ADD COLUMN IF NOT EXISTS stimulus       JSONB,          -- visual widgets shown with the item
  ADD COLUMN IF NOT EXISTS answer_spec    JSONB,          -- grader-specific spec (never sent raw to client)
  ADD COLUMN IF NOT EXISTS grader         TEXT,
  ADD COLUMN IF NOT EXISTS parts          JSONB,          -- multi-part items (generalizes steps)
  ADD COLUMN IF NOT EXISTS explanation_md TEXT;
ALTER TABLE public.items ALTER COLUMN statement_latex DROP NOT NULL;

ALTER TABLE public.attempts
  ADD COLUMN IF NOT EXISTS submitted_answer JSONB,
  ADD COLUMN IF NOT EXISTS grader           TEXT,
  ADD COLUMN IF NOT EXISTS score            REAL;
ALTER TABLE public.attempts ALTER COLUMN submitted_latex DROP NOT NULL;

-- Selection-primary items first: one choice / match / numeric part from genui_plan's primary widget.
-- Answer keys move out of props into answer_spec; MatchPairs rights are shuffled by md5(item id).
WITH sel AS (
  SELECT i.id, w->>'type' AS t, w->'props' AS p
  FROM public.items i
  CROSS JOIN LATERAL (
    SELECT w FROM jsonb_array_elements(
      CASE WHEN jsonb_typeof(i.genui_plan->'widgets') = 'array' THEN i.genui_plan->'widgets' ELSE '[]'::jsonb END
    ) w
    WHERE jsonb_typeof(w) = 'object' AND w->>'type' = i.genui_plan->>'primary'
    LIMIT 1
  ) x
  WHERE i.parts IS NULL
    AND i.genui_plan->>'primary' IN ('QuickCheck', 'MatchPairs', 'NumberLine')
    AND jsonb_typeof(w->'props') = 'object'
), built AS (
  SELECT sel.id,
    CASE sel.t
      WHEN 'QuickCheck' THEN jsonb_build_object(
        'component', 'QuickCheck', 'grader', 'choice',
        'props', sel.p - 'correctId' - 'correct_latex' - 'correctLatex' - 'explanation',
        'answer_spec', jsonb_build_object(
          'correctIds', jsonb_build_array(sel.p->'correctId'), 'explanation', sel.p->'explanation'))
      WHEN 'NumberLine' THEN jsonb_build_object(
        'component', 'NumberLine', 'grader', 'numeric',
        'props', sel.p - 'target' - 'tolerance' - 'correct_latex' - 'correctLatex',
        'answer_spec', jsonb_build_object(
          'value', sel.p->'target',
          'abs_tolerance', COALESCE(sel.p->'tolerance', to_jsonb(COALESCE((sel.p->>'step')::float8, 1) / 2))))
      ELSE (
        SELECT jsonb_build_object(
          'component', 'MatchPairs', 'grader', 'match',
          'props', (sel.p - 'pairs' - 'correct_latex' - 'correctLatex') || jsonb_build_object(
            'lefts', jsonb_agg(q.e->'left' ORDER BY q.n),
            'rights', jsonb_agg(q.e->'right' ORDER BY q.r)),
          'answer_spec', jsonb_build_object('pairs', jsonb_agg(jsonb_build_array(q.n - 1, q.r - 1) ORDER BY q.n)))
        FROM (
          SELECT e, n, row_number() OVER (ORDER BY md5(sel.id::text || ':' || (n - 1)) COLLATE "C") AS r
          FROM jsonb_array_elements(sel.p->'pairs') WITH ORDINALITY AS t(e, n)
        ) q
      )
    END AS part
  FROM sel
  WHERE CASE sel.t
    WHEN 'QuickCheck' THEN COALESCE(sel.p->>'correctId', '') <> ''
      AND sel.p->'choices' @> jsonb_build_array(jsonb_build_object('id', sel.p->'correctId'))
    WHEN 'NumberLine' THEN jsonb_typeof(sel.p->'target') = 'number'
    ELSE jsonb_typeof(sel.p->'pairs') = 'array' AND jsonb_array_length(
      CASE WHEN jsonb_typeof(sel.p->'pairs') = 'array' THEN sel.p->'pairs' ELSE '[]'::jsonb END) >= 2
  END
)
UPDATE public.items i SET
  prompt_md = COALESCE(i.prompt_md, i.prompt),
  grader = built.part->>'grader',
  parts = jsonb_build_array(jsonb_strip_nulls(built.part))
FROM built
WHERE i.id = built.id AND i.parts IS NULL;

-- Everything else is math: one sympy part per derivation step.
UPDATE public.items i SET
  prompt_md = COALESCE(i.prompt_md, i.prompt),
  grader = 'sympy',
  parts = (
    SELECT COALESCE(jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
      'component', 'SymbolicStepEditor', 'grader', 'sympy', 'props', '{}'::jsonb,
      'answer_spec', jsonb_build_object('latex', s->'latex', 'sympy', s->'sympy', 'operation', s->'operation'),
      'justification', s->'justification'
    )) ORDER BY n), '[]'::jsonb)
    FROM jsonb_array_elements(CASE WHEN jsonb_typeof(i.steps) = 'array' THEN i.steps ELSE '[]'::jsonb END)
      WITH ORDINALITY AS t(s, n)
  )
WHERE i.parts IS NULL;

UPDATE public.learning_paths SET subject_profile = jsonb_build_object(
  'subject', left(COALESCE(NULLIF(target_goal, ''), title), 120),
  'categories', '["core","math"]'::jsonb, 'notation', 'math')
WHERE subject_profile IS NULL;

UPDATE public.knowledge_nodes n SET subject_profile = jsonb_build_object(
  'subject', left(COALESCE((
    SELECT NULLIF(lp.target_goal, '') FROM public.path_nodes pn
    JOIN public.learning_paths lp ON lp.id = pn.path_id
    WHERE pn.node_id = n.id ORDER BY lp.created_at LIMIT 1
  ), n.title), 120),
  'categories', '["core","math"]'::jsonb, 'notation', 'math')
WHERE subject_profile IS NULL;

UPDATE public.attempts SET grader = 'sympy', submitted_answer = jsonb_build_object('latex', submitted_latex)
WHERE grader IS NULL;
