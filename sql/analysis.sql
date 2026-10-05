-- DuckDB queries over data/processed/sales_daily.parquet  (run: python sql/run_sql.py)

-- name: store_monthly_demand
SELECT store_id, date_trunc('month', date) AS month, SUM(sales) AS units, ROUND(SUM(sales * sell_price), 0) AS revenue
FROM 'data/processed/sales_daily.parquet'
GROUP BY 1, 2 ORDER BY 1, 2 LIMIT 12;

-- name: product_rank_within_category
WITH item_tot AS (
  SELECT cat_id, item_id, SUM(sales) AS units FROM 'data/processed/sales_daily.parquet' GROUP BY 1, 2)
SELECT cat_id, item_id, units, RANK() OVER (PARTITION BY cat_id ORDER BY units DESC) AS rank_in_category,
       ROUND(100.0 * units / SUM(units) OVER (PARTITION BY cat_id), 1) AS pct_of_category
FROM item_tot QUALIFY rank_in_category <= 3 ORDER BY cat_id, rank_in_category;

-- name: weekly_demand_with_rolling_avg
WITH wk AS (
  SELECT date_trunc('week', date) AS week, SUM(sales) AS units FROM 'data/processed/sales_daily.parquet' GROUP BY 1)
SELECT week, units, ROUND(AVG(units) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 1) AS rolling_4wk_avg
FROM wk ORDER BY week DESC LIMIT 8;

-- name: top_stockout_risk_candidates
-- risk proxy: demand accelerating (last 28d vs previous 28d) AND volatile (coefficient of variation)
WITH bounds AS (SELECT MAX(date) AS last_d FROM 'data/processed/sales_daily.parquet'),
s AS (
  SELECT item_id, store_id,
         AVG(CASE WHEN date >  last_d - INTERVAL 28 DAY THEN sales END) AS recent_avg,
         AVG(CASE WHEN date <= last_d - INTERVAL 28 DAY AND date > last_d - INTERVAL 56 DAY THEN sales END) AS prior_avg,
         STDDEV(CASE WHEN date > last_d - INTERVAL 56 DAY THEN sales END) / NULLIF(AVG(CASE WHEN date > last_d - INTERVAL 56 DAY THEN sales END), 0) AS cv
  FROM 'data/processed/sales_daily.parquet', bounds GROUP BY 1, 2)
SELECT item_id, store_id, ROUND(recent_avg, 2) AS recent_avg, ROUND(prior_avg, 2) AS prior_avg,
       ROUND(recent_avg / NULLIF(prior_avg, 0) - 1, 3) AS growth, ROUND(cv, 2) AS cv
FROM s WHERE prior_avg > 0 ORDER BY growth * cv DESC LIMIT 10;

-- name: promo_price_effect_by_category
WITH p AS (
  SELECT cat_id, sales, CASE WHEN sell_price < 0.92 * AVG(sell_price) OVER (PARTITION BY item_id, store_id) THEN 'promo' ELSE 'regular' END AS price_state
  FROM 'data/processed/sales_daily.parquet')
SELECT cat_id, price_state, ROUND(AVG(sales), 3) AS avg_units, COUNT(*) AS days FROM p GROUP BY 1, 2 ORDER BY 1, 2;
