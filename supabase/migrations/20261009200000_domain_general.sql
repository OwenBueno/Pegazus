-- Non-math, non-language nodes were stored as MATHEMATICS (domain_enum is legacy; new code reads
-- subject_profile). Additive: one new enum value. Backfill lives in the next file because a new
-- enum value cannot be used in the transaction that adds it.
ALTER TYPE domain_enum ADD VALUE IF NOT EXISTS 'GENERAL';
