-- 1. Count the total number of companies in the master company table.
SELECT COUNT(*) AS total_companies
FROM companies;

-- 2. Show total row counts for every loaded table.
SELECT 'analysis' AS table_name, COUNT(*) AS row_count FROM analysis
UNION ALL SELECT 'companies', COUNT(*) FROM companies
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
ORDER BY table_name;

-- 3. List the top 10 companies by latest available market cap.
WITH latest_market_cap AS (
    SELECT company_id, MAX(year) AS latest_year
    FROM market_cap
    GROUP BY company_id
)
SELECT
    m.company_id,
    c.company_name,
    m.year,
    m.market_cap_crore
FROM market_cap m
JOIN latest_market_cap l
  ON m.company_id = l.company_id
 AND m.year = l.latest_year
LEFT JOIN companies c
  ON m.company_id = c.company_id
ORDER BY m.market_cap_crore DESC
LIMIT 10;

-- 4. List the top 10 companies by latest available sales.
WITH latest_profit AS (
    SELECT company_id, MAX(year) AS latest_year
    FROM profitandloss
    GROUP BY company_id
)
SELECT
    p.company_id,
    c.company_name,
    p.year,
    p.sales
FROM profitandloss p
JOIN latest_profit l
  ON p.company_id = l.company_id
 AND p.year = l.latest_year
LEFT JOIN companies c
  ON p.company_id = c.company_id
ORDER BY p.sales DESC
LIMIT 10;

-- 5. Find companies with the highest latest return on equity.
WITH latest_ratios AS (
    SELECT company_id, MAX(year) AS latest_year
    FROM financial_ratios
    GROUP BY company_id
)
SELECT
    r.company_id,
    c.company_name,
    r.year,
    r.return_on_equity_pct
FROM financial_ratios r
JOIN latest_ratios l
  ON r.company_id = l.company_id
 AND r.year = l.latest_year
LEFT JOIN companies c
  ON r.company_id = c.company_id
ORDER BY r.return_on_equity_pct DESC
LIMIT 10;

-- 6. Find companies with the highest latest operating profit.
WITH latest_profit AS (
    SELECT company_id, MAX(year) AS latest_year
    FROM profitandloss
    GROUP BY company_id
)
SELECT
    p.company_id,
    c.company_name,
    p.year,
    p.operating_profit
FROM profitandloss p
JOIN latest_profit l
  ON p.company_id = l.company_id
 AND p.year = l.latest_year
LEFT JOIN companies c
  ON p.company_id = c.company_id
ORDER BY p.operating_profit DESC
LIMIT 10;

-- 7. Count financial statement records per company across key financial tables.
SELECT
    company_id,
    SUM(record_count) AS total_financial_records
FROM (
    SELECT company_id, COUNT(*) AS record_count FROM balancesheet GROUP BY company_id
    UNION ALL
    SELECT company_id, COUNT(*) FROM cashflow GROUP BY company_id
    UNION ALL
    SELECT company_id, COUNT(*) FROM profitandloss GROUP BY company_id
    UNION ALL
    SELECT company_id, COUNT(*) FROM financial_ratios GROUP BY company_id
    UNION ALL
    SELECT company_id, COUNT(*) FROM market_cap GROUP BY company_id
)
GROUP BY company_id
ORDER BY total_financial_records DESC, company_id
LIMIT 20;

-- 8. Show profit and loss year coverage by company.
SELECT
    company_id,
    COUNT(DISTINCT year) AS years_available,
    MIN(year) AS first_year,
    MAX(year) AS latest_year
FROM profitandloss
WHERE company_id IS NOT NULL
  AND year IS NOT NULL
GROUP BY company_id
ORDER BY years_available, company_id;

-- 9. List companies with fewer than 5 years of profit and loss data.
SELECT
    company_id,
    COUNT(DISTINCT year) AS years_available
FROM profitandloss
WHERE company_id IS NOT NULL
  AND year IS NOT NULL
GROUP BY company_id
HAVING COUNT(DISTINCT year) < 5
ORDER BY years_available, company_id;

-- 10. Find company IDs referenced by financial tables but missing from companies.
SELECT
    source_table,
    company_id,
    COUNT(*) AS occurrence_count
FROM (
    SELECT 'balancesheet' AS source_table, company_id FROM balancesheet
    UNION ALL SELECT 'cashflow', company_id FROM cashflow
    UNION ALL SELECT 'profitandloss', company_id FROM profitandloss
    UNION ALL SELECT 'financial_ratios', company_id FROM financial_ratios
    UNION ALL SELECT 'market_cap', company_id FROM market_cap
)
WHERE company_id IS NOT NULL
  AND company_id NOT IN (SELECT company_id FROM companies)
GROUP BY source_table, company_id
ORDER BY source_table, company_id;

-- 11. Detect duplicate company/year combinations in profit and loss data.
SELECT
    company_id,
    year,
    COUNT(*) AS duplicate_count
FROM profitandloss
WHERE company_id IS NOT NULL
  AND year IS NOT NULL
GROUP BY company_id, year
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC, company_id, year;

-- 12. Show company distribution by broad sector.
SELECT
    broad_sector,
    COUNT(DISTINCT company_id) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC, broad_sector;

-- 13. Show the latest stock price row for each company.
WITH latest_prices AS (
    SELECT company_id, MAX(date) AS latest_date
    FROM stock_prices
    GROUP BY company_id
)
SELECT
    s.company_id,
    c.company_name,
    s.date,
    s.close_price,
    s.volume
FROM stock_prices s
JOIN latest_prices l
  ON s.company_id = l.company_id
 AND s.date = l.latest_date
LEFT JOIN companies c
  ON s.company_id = c.company_id
ORDER BY s.company_id;

-- 14. Show profit trend for a selected company; replace 'TCS' as needed.
SELECT
    company_id,
    year,
    sales,
    operating_profit,
    net_profit,
    eps
FROM profitandloss
WHERE company_id = 'TCS'
ORDER BY year;

-- 15. Run SQLite foreign key validation.
PRAGMA foreign_key_check;

-- 16. Count null company IDs across FK-bearing tables.
SELECT
    source_table,
    COUNT(*) AS null_company_id_rows
FROM (
    SELECT 'analysis' AS source_table, company_id FROM analysis
    UNION ALL SELECT 'balancesheet', company_id FROM balancesheet
    UNION ALL SELECT 'cashflow', company_id FROM cashflow
    UNION ALL SELECT 'documents', company_id FROM documents
    UNION ALL SELECT 'financial_ratios', company_id FROM financial_ratios
    UNION ALL SELECT 'market_cap', company_id FROM market_cap
    UNION ALL SELECT 'peer_groups', company_id FROM peer_groups
    UNION ALL SELECT 'profitandloss', company_id FROM profitandloss
    UNION ALL SELECT 'prosandcons', company_id FROM prosandcons
    UNION ALL SELECT 'sectors', company_id FROM sectors
    UNION ALL SELECT 'stock_prices', company_id FROM stock_prices
)
WHERE company_id IS NULL
GROUP BY source_table
ORDER BY source_table;

-- 17. Detect malformed or missing years in financial tables.
SELECT 'balancesheet' AS source_table, company_id, COUNT(*) AS malformed_year_rows
FROM balancesheet
WHERE year IS NULL OR year < 1990 OR year > 2100
GROUP BY company_id
UNION ALL
SELECT 'cashflow', company_id, COUNT(*)
FROM cashflow
WHERE year IS NULL OR year < 1990 OR year > 2100
GROUP BY company_id
UNION ALL
SELECT 'profitandloss', company_id, COUNT(*)
FROM profitandloss
WHERE year IS NULL OR year < 1990 OR year > 2100
GROUP BY company_id
UNION ALL
SELECT 'financial_ratios', company_id, COUNT(*)
FROM financial_ratios
WHERE year IS NULL OR year < 1990 OR year > 2100
GROUP BY company_id
UNION ALL
SELECT 'market_cap', company_id, COUNT(*)
FROM market_cap
WHERE year IS NULL OR year < 1990 OR year > 2100
GROUP BY company_id
ORDER BY source_table, company_id;

-- 18. Identify companies present in the master table but missing profit and loss rows.
SELECT
    c.company_id,
    c.company_name
FROM companies c
LEFT JOIN profitandloss p
  ON c.company_id = p.company_id
WHERE p.company_id IS NULL
ORDER BY c.company_id;
