-- Twin of research_job._domain: math notation → MATHEMATICS, a target language → LANGUAGE, else GENERAL.
-- Re-runnable: only rows whose profile says they are not math are touched.
UPDATE knowledge_nodes
SET domain = CASE
    WHEN subject_profile->>'target_language' IS NOT NULL OR subject_profile->'categories' ? 'language'
      THEN 'LANGUAGE'::domain_enum
    ELSE 'GENERAL'::domain_enum
  END
WHERE subject_profile IS NOT NULL
  AND COALESCE(subject_profile->>'notation', 'math') <> 'math'
  AND domain = 'MATHEMATICS';
