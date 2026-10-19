-- ------------------------------
-- SECTION 1: DATA QUALITY CHECKS
-- ------------------------------
-- 1.1 Check row count for employees table
SELECT COUNT(*) AS employee_count 
FROM employees;

-- 1.2 Check row count for customers table
SELECT COUNT(*) AS customers_count 
FROM customers;

-- 1.3 Check row count for projects table
SELECT COUNT(*) AS projects_count
FROM projects;

-- 1.4 Check row count for assignments table
SELECT COUNT(*) AS assignments_count
FROM assignments;

-- 1.5 Check row count for budgtes table
SELECT COUNT(*) AS budgets_count
FROM budgets;

-- 1.6 Check row count for bench_history table
SELECT COUNT(*) AS bench_history_count
FROM bench_history;


-- ------------------------------------------
-- SECTION 2: Employee and Attrition Analysis
-- ------------------------------------------

-- 2.1 Total active employees 
SELECT *
FROM employees
WHERE employment_status = 'Active';

-- 2.2 Total exited employees 
SELECT 
    grade,
    COUNT(employee_id) AS total_employees,
    COUNT(CASE WHEN exit_date IS NOT NULL THEN employee_id END) leavers
FROM employees
GROUP BY grade
ORDER BY leavers DESC;

-- 2.3 Attrition by grade 
SELECT 
    grade,
    COUNT(employee_id) AS total_employees,
    COUNT(CASE WHEN exit_date IS NOT NULL THEN employee_id END) AS leavers,
/* Attrition Rate = (No. of employees left/Total no. of employees)*100 */   
    CAST(
        COUNT(CASE WHEN exit_date IS NOT NULL THEN employee_id END) * 100.0
        / NULLIF(COUNT(employee_id), 0)
    AS DECIMAL(5,2)) AS attrition_rate
FROM employees
GROUP BY grade
ORDER BY attrition_rate DESC;

-- 2.4 Attrition by skill    
    SELECT 
    skill,
    COUNT(employee_id) AS total_employees,
    COUNT(CASE WHEN exit_date IS NOT NULL THEN employee_id END) AS leavers,
    CAST(
        COUNT(CASE WHEN exit_date IS NOT NULL THEN employee_id END) * 100.0
        / NULLIF(COUNT(employee_id), 0)
    AS DECIMAL(5,2)) AS attrition_rate
FROM employees
GROUP BY skill
ORDER BY attrition_rate DESC;

-- Attrition by customer
WITH last_customer AS (
    SELECT 
        employee_id,
        customer_id,
        ROW_NUMBER() OVER (
            PARTITION BY employee_id 
            ORDER BY assignment_end_date DESC,
                     assignment_start_date DESC
        ) AS rn
    FROM assignments
)
SELECT 
    c.customer_name,
    COUNT(DISTINCT e.employee_id) AS total_employees,
    COUNT(DISTINCT CASE 
        WHEN e.exit_date IS NOT NULL THEN e.employee_id 
    END) AS attrition_count
FROM employees e
LEFT JOIN last_customer lc
    ON e.employee_id = lc.employee_id
   AND lc.rn = 1
LEFT JOIN customers c
    ON lc.customer_id = c.customer_id
GROUP BY c.customer_name
ORDER BY attrition_count DESC;

-- 2.5 Monthly attrition trend
SELECT 
    strftime('%Y', exit_date) AS exit_year,
    strftime('%m', exit_date) AS exit_month,
    COUNT(employee_id) AS leavers
FROM employees
WHERE exit_date IS NOT NULL
GROUP BY 
    strftime('%Y', exit_date),
    strftime('%m', exit_date)
ORDER BY 
    exit_year,
    exit_month;

-- ----------------------------------------
-- SECTION 3: DEPLOYMENT AND BENCH ANALYSIS
-- ----------------------------------------

-- 3.1 Current deployment status of active employees
WITH current_assignment AS (
    SELECT 
        employee_id,
        customer_id,
        project_id,
        assignment_start_date,
        assignment_end_date,
        ROW_NUMBER() OVER (
            PARTITION BY employee_id 
            ORDER BY assignment_end_date DESC
        ) AS rn
    FROM assignments
    WHERE assignment_start_date <= CURRENT_DATE
      AND (
          assignment_end_date IS NULL
          OR assignment_end_date >= CURRENT_DATE
      )
)
SELECT 
    e.employee_id,
    e.grade,
    e.skill,
    e.location,
    CASE 
        WHEN ca.employee_id IS NOT NULL THEN 'Deployed'
        ELSE 'Bench'
    END AS deployment_status,
    ca.customer_id,
    ca.project_id
FROM employees e
LEFT JOIN current_assignment ca
    ON e.employee_id = ca.employee_id
   AND ca.rn = 1
WHERE e.employment_status = 'Active';

-- 3.2 Current bench employees
SELECT 
    b.employee_id,
    e.grade,
    e.skill,
    e.location,
    b.bench_start_date,
    CAST(JULIANDAY(CURRENT_DATE) - JULIANDAY(b.bench_start_date) AS INTEGER) AS bench_days,
    b.bench_reason
FROM bench_history b
JOIN employees e
    ON b.employee_id = e.employee_id
WHERE b.bench_end_date IS NULL
  AND e.employment_status = 'Active'
ORDER BY bench_days DESC;

-- Bench aging bucket
WITH bench_calc AS (
    SELECT 
        b.employee_id,
        e.skill,
        e.grade,
        CAST(JULIANDAY(CURRENT_DATE) - JULIANDAY(b.bench_start_date) AS INTEGER) AS bench_days
    FROM bench_history b
    JOIN employees e ON b.employee_id = e.employee_id
    WHERE CURRENT_DATE >= b.bench_start_date
      AND (b.bench_end_date IS NULL OR CURRENT_DATE <= b.bench_end_date)
      AND e.employment_status = 'Active'
)
SELECT 
    employee_id,
    skill,
    grade,
    bench_days,
    CASE 
        WHEN bench_days <= 15 THEN '0-15 Days'
        WHEN bench_days <= 30 THEN '16-30 Days'
        WHEN bench_days <= 60 THEN '31-60 Days'
        WHEN bench_days <= 90 THEN '61-90 Days'
        ELSE '90+ Days'
    END AS bench_aging_bucket
FROM bench_calc;
  
  -- Employees on bench for more than 30 days
  SELECT 
    e.employee_id,
    e.skill,
    e.grade,
    e.location,
    b.bench_start_date,
    CAST(JULIANDAY(CURRENT_DATE) - JULIANDAY(b.bench_start_date) AS INTEGER) AS bench_days
FROM bench_history b
JOIN employees e
    ON b.employee_id = e.employee_id
WHERE CURRENT_DATE >= b.bench_start_date
  AND (b.bench_end_date IS NULL OR CURRENT_DATE <= b.bench_end_date)
  AND e.employment_status = 'Active'
  AND CAST(JULIANDAY(CURRENT_DATE) - JULIANDAY(b.bench_start_date) AS INTEGER) > 30
ORDER BY bench_days DESC;

-- ----------------------------
-- SECTION 3: ROTATION ANALYSIS
-- ----------------------------

-- 4.1 Rotation count in last 12 months 
SELECT 
    a.employee_id,
    COUNT(a.assignment_id) AS rotations_last_12_months
FROM assignments a
WHERE a.assignment_start_date >= DATE(CURRENT_DATE, '-12 months')
GROUP BY a.employee_id
ORDER BY rotations_last_12_months DESC;

-- 4.2 Employees with no rotation in last 12 months
WITH recent_assignments AS (
    SELECT 
        employee_id,
        COUNT(assignment_id) AS assignment_count
    FROM assignments
    WHERE assignment_start_date >= DATE(CURRENT_DATE, '-12 months')
    GROUP BY employee_id
)
SELECT 
    e.employee_id,
    e.skill,
    e.grade,
    e.location,
    IFNULL(ra.assignment_count, 0) AS rotations_last_12_months
FROM employees e
LEFT JOIN recent_assignments ra
    ON e.employee_id = ra.employee_id
WHERE e.employment_status = 'Active'
  AND IFNULL(ra.assignment_count, 0) <= 1
ORDER BY rotations_last_12_months ASC;

-- 4.3 Upcoming assignments ending in next 60 days
SELECT 
    a.employee_id,
    e.skill,
    e.grade,
    c.customer_name,
    p.project_name,
    a.assignment_end_date,
    CAST(JULIANDAY(a.assignment_end_date) - JULIANDAY(CURRENT_DATE) AS INTEGER) AS days_to_end
FROM assignments a
JOIN employees e
    ON a.employee_id = e.employee_id
JOIN customers c
    ON a.customer_id = c.customer_id
JOIN projects p
    ON a.project_id = p.project_id
WHERE e.employment_status = 'Active'
  AND a.assignment_end_date BETWEEN CURRENT_DATE AND DATE(CURRENT_DATE, '+60 days')
ORDER BY a.assignment_end_date;

-- -----------------------------------
-- SECTION 5: CUSTOMER BUDGET ANALYSIS
-- -----------------------------------

-- 5.1 Customer budget utilization
SELECT 
    c.customer_name,
    SUM(b.budget_amount) AS total_budget,
    SUM(b.actual_amount) AS total_actual,
    SUM(b.budget_amount) - SUM(b.actual_amount) AS remaining_budget,
    CAST(
        SUM(b.actual_amount) * 100.0 / NULLIF(SUM(b.budget_amount), 0)
    AS DECIMAL(5,2)) AS burn_rate
FROM budgets b
JOIN customers c
    ON b.customer_id = c.customer_id
GROUP BY c.customer_name
ORDER BY burn_rate DESC;

-- 5.2 Project level budget overrun
SELECT 
    c.customer_name,
    p.project_name,
    SUM(b.budget_amount) AS budget_amount,
    SUM(b.actual_amount) AS actual_amount,
    SUM(b.actual_amount) - SUM(b.budget_amount) AS variance,
    CASE 
        WHEN SUM(b.actual_amount) > SUM(b.budget_amount) THEN 'Over Budget'
        ELSE 'Within Budget'
    END AS budget_status
FROM budgets b
JOIN customers c
    ON b.customer_id = c.customer_id
JOIN projects p
    ON b.project_id = p.project_id
GROUP BY 
    c.customer_name,
    p.project_name
ORDER BY variance DESC;