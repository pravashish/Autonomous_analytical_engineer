-- ── Sample 1: Bad query — SELECT *, no date filter, function on join column ──
SELECT *
FROM ANALYTICS_DEMO.MARTS.ARR_PROGRAM_FACT f
JOIN ANALYTICS_DEMO.MARTS.PROGRAMS_DIM p
    ON TO_NUMBER(p.program_sk) = f.program_sk
JOIN ANALYTICS_DEMO.MARTS.DATES_DIM d
    ON TO_DATE(d.full_date) = f.period_start_date;


-- ── Sample 2: Better query — columns projected, date filter, no functions on join ──
SELECT
    p.program_name,
    p.region,
    f.arr_type,
    f.arr_amount,
    f.period_start_date
FROM ANALYTICS_DEMO.MARTS.ARR_PROGRAM_FACT f
JOIN ANALYTICS_DEMO.MARTS.PROGRAMS_DIM p
    ON p.program_sk = f.program_sk
WHERE f.period_start_date >= '2022-01-01'
  AND f.period_start_date <  '2023-01-01';


-- ── Sample 3: Cartesian join risk ──
SELECT a.program_sk, b.program_name
FROM ANALYTICS_DEMO.MARTS.ARR_PROGRAM_FACT a
CROSS JOIN ANALYTICS_DEMO.MARTS.PROGRAMS_DIM b;
