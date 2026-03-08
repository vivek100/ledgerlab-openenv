#!/usr/bin/env python3
"""
Create the FinBench dataset: 10 data-analysis tasks with reference files
and structured deterministic checks (unit tests).

Each check is a machine-verifiable spec — no NL parsing.

Check types:
  file_exists  — file at path exists
  sheet_exists — Excel workbook has named sheet
  cell_value   — value in a specific cell/row matches expected (with tolerance)
  contains_text— text file contains a string (case-insensitive)
  row_count    — table/sheet has expected number of rows
  column_exists— sheet has a named column

Run:
    source .venv/bin/activate
    python scripts/create_test_data.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "tasks")
WORKSPACES = os.path.join(DATA, "workspaces")

TASKS = []


def ws(task_id):
    p = os.path.join(WORKSPACES, task_id, "reference")
    os.makedirs(p, exist_ok=True)
    return p


# ═══════════════════════════════════════════════════════════════
# Task 1: Quarterly Sales Summary
# ═══════════════════════════════════════════════════════════════
def task_sales():
    ref = ws("task_sales")
    north = pd.DataFrame({
        "Quarter": ["Q1", "Q2", "Q3", "Q4"],
        "Region": ["North"] * 4,
        "Revenue": [120000, 145000, 132000, 158000],
        "Costs": [80000, 92000, 88000, 95000],
    })
    south = pd.DataFrame({
        "Quarter": ["Q1", "Q2", "Q3", "Q4"],
        "Region": ["South"] * 4,
        "Revenue": [95000, 110000, 105000, 125000],
        "Costs": [70000, 78000, 75000, 82000],
    })
    with pd.ExcelWriter(os.path.join(ref, "sales_data.xlsx")) as w:
        north.to_excel(w, sheet_name="North", index=False)
        south.to_excel(w, sheet_name="South", index=False)

    return {
        "task_id": "task_sales",
        "prompt": (
            "Analyze the quarterly sales data in reference/sales_data.xlsx. "
            "For each region (North, South), calculate total annual revenue "
            "and total annual profit (Revenue - Costs). "
            "Create output/sales_report.xlsx with a sheet named 'Summary' "
            "containing columns: Region, Total Revenue, Total Profit."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/sales_report.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/sales_report.xlsx", "sheet": "Summary", "score": 1},
            {"check": "cell_value", "file": "output/sales_report.xlsx", "sheet": "Summary",
             "lookup": {"Region": "North"}, "column": "Total Revenue", "expected": 555000, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/sales_report.xlsx", "sheet": "Summary",
             "lookup": {"Region": "South"}, "column": "Total Revenue", "expected": 435000, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/sales_report.xlsx", "sheet": "Summary",
             "lookup": {"Region": "North"}, "column": "Total Profit", "expected": 200000, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/sales_report.xlsx", "sheet": "Summary",
             "lookup": {"Region": "South"}, "column": "Total Profit", "expected": 130000, "tolerance": 1, "score": 2},
        ],
        "expected_deliverables": ["sales_report.xlsx"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 2: Budget Variance Analysis
# ═══════════════════════════════════════════════════════════════
def task_budget():
    ref = ws("task_budget")
    df = pd.DataFrame({
        "Department": ["Engineering", "Marketing", "Sales", "HR", "Operations"],
        "Budget": [500000, 200000, 300000, 150000, 250000],
        "Actual": [520000, 180000, 310000, 145000, 270000],
    })
    df.to_csv(os.path.join(ref, "budget_vs_actual.csv"), index=False)

    return {
        "task_id": "task_budget",
        "prompt": (
            "Analyze reference/budget_vs_actual.csv. "
            "Calculate variance (Actual - Budget) per department. "
            "Write output/budget_report.txt listing each department, "
            "its variance, and whether over/under budget. "
            "Include total company variance at the end."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/budget_report.txt", "score": 1},
            {"check": "contains_text", "file": "output/budget_report.txt", "text": "20000", "score": 2},
            {"check": "contains_text", "file": "output/budget_report.txt", "text": "-20000", "score": 2},
            {"check": "contains_text", "file": "output/budget_report.txt", "text": "25000", "score": 2},
            {"check": "contains_text", "file": "output/budget_report.txt", "text": "over", "score": 1},
            {"check": "contains_text", "file": "output/budget_report.txt", "text": "under", "score": 1},
        ],
        "expected_deliverables": ["budget_report.txt"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 3: Employee Headcount & Salary
# ═══════════════════════════════════════════════════════════════
def task_employees():
    ref = ws("task_employees")
    df = pd.DataFrame({
        "Name": ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"],
        "Department": ["Engineering", "Engineering", "Marketing", "Marketing",
                       "Sales", "Sales", "Engineering", "Sales"],
        "Salary": [120000, 110000, 95000, 88000, 75000, 82000, 105000, 78000],
        "Years": [5, 3, 7, 2, 4, 6, 1, 8],
    })
    df.to_excel(os.path.join(ref, "employees.xlsx"), index=False)

    return {
        "task_id": "task_employees",
        "prompt": (
            "Analyze reference/employees.xlsx. Calculate headcount and average "
            "salary per department. Create output/employee_analysis.xlsx "
            "with sheet 'Department Stats' showing Department, Headcount, Avg Salary."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/employee_analysis.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/employee_analysis.xlsx", "sheet": "Department Stats", "score": 1},
            {"check": "cell_value", "file": "output/employee_analysis.xlsx", "sheet": "Department Stats",
             "lookup": {"Department": "Engineering"}, "column": "Headcount", "expected": 3, "tolerance": 0, "score": 2},
            {"check": "cell_value", "file": "output/employee_analysis.xlsx", "sheet": "Department Stats",
             "lookup": {"Department": "Marketing"}, "column": "Headcount", "expected": 2, "tolerance": 0, "score": 2},
            {"check": "cell_value", "file": "output/employee_analysis.xlsx", "sheet": "Department Stats",
             "lookup": {"Department": "Sales"}, "column": "Headcount", "expected": 3, "tolerance": 0, "score": 2},
            {"check": "cell_value", "file": "output/employee_analysis.xlsx", "sheet": "Department Stats",
             "lookup": {"Department": "Engineering"}, "column": "Avg Salary",
             "expected": 111666.67, "tolerance": 1, "score": 1},
        ],
        "expected_deliverables": ["employee_analysis.xlsx"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 4: Monthly Revenue Trend
# ═══════════════════════════════════════════════════════════════
def task_revenue_trend():
    ref = ws("task_revenue_trend")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    np.random.seed(42)
    revenue = [50000 + i * 3000 + int(np.random.normal(0, 2000)) for i in range(12)]
    df = pd.DataFrame({"Month": months, "Revenue": revenue})
    df.to_csv(os.path.join(ref, "monthly_revenue.csv"), index=False)

    total = sum(revenue)
    avg = total / 12
    max_month = months[revenue.index(max(revenue))]
    min_month = months[revenue.index(min(revenue))]

    return {
        "task_id": "task_revenue_trend",
        "prompt": (
            "Analyze reference/monthly_revenue.csv. Calculate: "
            "(1) total annual revenue, (2) average monthly revenue, "
            "(3) highest revenue month, (4) lowest revenue month. "
            "Write results to output/revenue_summary.txt."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/revenue_summary.txt", "score": 1},
            {"check": "contains_text", "file": "output/revenue_summary.txt", "text": str(total), "score": 3},
            {"check": "contains_text", "file": "output/revenue_summary.txt", "text": max_month, "score": 2},
            {"check": "contains_text", "file": "output/revenue_summary.txt", "text": min_month, "score": 2},
        ],
        "expected_deliverables": ["revenue_summary.txt"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 5: Product Profitability Ranking
# ═══════════════════════════════════════════════════════════════
def task_product_profit():
    ref = ws("task_product_profit")
    df = pd.DataFrame({
        "Product": ["Widget A", "Widget B", "Gadget X", "Gadget Y", "Service Z"],
        "Units Sold": [1200, 800, 2000, 500, 3000],
        "Unit Price": [25.00, 45.00, 15.00, 80.00, 10.00],
        "Unit Cost": [12.00, 20.00, 8.00, 35.00, 3.00],
    })
    df.to_excel(os.path.join(ref, "products.xlsx"), index=False)

    # Pre-compute expected values
    # Profit = Units * (Price - Cost)
    # Widget A: 1200 * 13 = 15600
    # Widget B: 800 * 25 = 20000
    # Gadget X: 2000 * 7 = 14000
    # Gadget Y: 500 * 45 = 22500
    # Service Z: 3000 * 7 = 21000

    return {
        "task_id": "task_product_profit",
        "prompt": (
            "Analyze reference/products.xlsx. For each product calculate "
            "total profit = Units Sold * (Unit Price - Unit Cost). "
            "Create output/product_ranking.xlsx with sheet 'Ranking' "
            "showing Product, Total Profit sorted by profit descending."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/product_ranking.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/product_ranking.xlsx", "sheet": "Ranking", "score": 1},
            {"check": "cell_value", "file": "output/product_ranking.xlsx", "sheet": "Ranking",
             "lookup": {"Product": "Gadget Y"}, "column": "Total Profit", "expected": 22500, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/product_ranking.xlsx", "sheet": "Ranking",
             "lookup": {"Product": "Service Z"}, "column": "Total Profit", "expected": 21000, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/product_ranking.xlsx", "sheet": "Ranking",
             "lookup": {"Product": "Widget A"}, "column": "Total Profit", "expected": 15600, "tolerance": 1, "score": 2},
            {"check": "row_count", "file": "output/product_ranking.xlsx", "sheet": "Ranking",
             "expected": 5, "score": 1},
        ],
        "expected_deliverables": ["product_ranking.xlsx"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 6: Invoice Reconciliation (multi-file)
# ═══════════════════════════════════════════════════════════════
def task_invoice_recon():
    ref = ws("task_invoice_recon")
    invoices = pd.DataFrame({
        "Invoice ID": ["INV-001", "INV-002", "INV-003", "INV-004", "INV-005"],
        "Client": ["Acme Corp", "Globex", "Initech", "Acme Corp", "Globex"],
        "Amount": [15000, 22000, 8500, 12000, 18000],
    })
    payments = pd.DataFrame({
        "Invoice ID": ["INV-001", "INV-002", "INV-004", "INV-005"],
        "Amount Paid": [15000, 20000, 12000, 18000],
        "Date": ["2024-01-15", "2024-02-01", "2024-02-20", "2024-03-01"],
    })
    invoices.to_csv(os.path.join(ref, "invoices.csv"), index=False)
    payments.to_csv(os.path.join(ref, "payments.csv"), index=False)

    # Expected: INV-003 unpaid (8500), INV-002 underpaid by 2000
    # Total outstanding = 8500 + 2000 = 10500

    return {
        "task_id": "task_invoice_recon",
        "prompt": (
            "Reconcile invoices and payments from reference/invoices.csv and "
            "reference/payments.csv. Match by Invoice ID. Find: "
            "(1) unpaid invoices, (2) partially paid invoices (Amount Paid < Amount), "
            "(3) total outstanding amount. "
            "Write output/reconciliation.txt with the findings."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/reconciliation.txt", "score": 1},
            {"check": "contains_text", "file": "output/reconciliation.txt", "text": "INV-003", "score": 2},
            {"check": "contains_text", "file": "output/reconciliation.txt", "text": "INV-002", "score": 2},
            {"check": "contains_text", "file": "output/reconciliation.txt", "text": "8500", "score": 2},
            {"check": "contains_text", "file": "output/reconciliation.txt", "text": "10500", "score": 2},
        ],
        "expected_deliverables": ["reconciliation.txt"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 7: Customer Segmentation
# ═══════════════════════════════════════════════════════════════
def task_customer_segments():
    ref = ws("task_customer_segments")
    np.random.seed(7)
    n = 20
    df = pd.DataFrame({
        "Customer ID": [f"C{i:03d}" for i in range(1, n + 1)],
        "Total Purchases": np.random.choice([1, 2, 3, 5, 8, 12, 15, 20], n),
        "Total Spend": [0] * n,
        "Last Purchase Days Ago": np.random.choice([5, 15, 30, 60, 90, 180, 365], n),
    })
    df["Total Spend"] = df["Total Purchases"] * np.random.choice([50, 100, 200, 500], n)
    df.to_excel(os.path.join(ref, "customers.xlsx"), index=False)

    # Segment: High (>=10 purchases), Medium (5-9), Low (<5)
    high = len(df[df["Total Purchases"] >= 10])
    medium = len(df[(df["Total Purchases"] >= 5) & (df["Total Purchases"] < 10)])
    low = len(df[df["Total Purchases"] < 5])

    return {
        "task_id": "task_customer_segments",
        "prompt": (
            "Analyze reference/customers.xlsx. Segment customers into: "
            "High (10+ purchases), Medium (5-9 purchases), Low (<5 purchases). "
            "Create output/segments.xlsx with sheet 'Summary' showing "
            "Segment, Count, Avg Spend."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/segments.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/segments.xlsx", "sheet": "Summary", "score": 1},
            {"check": "cell_value", "file": "output/segments.xlsx", "sheet": "Summary",
             "lookup": {"Segment": "High"}, "column": "Count", "expected": high, "tolerance": 0, "score": 2},
            {"check": "cell_value", "file": "output/segments.xlsx", "sheet": "Summary",
             "lookup": {"Segment": "Medium"}, "column": "Count", "expected": medium, "tolerance": 0, "score": 2},
            {"check": "cell_value", "file": "output/segments.xlsx", "sheet": "Summary",
             "lookup": {"Segment": "Low"}, "column": "Count", "expected": low, "tolerance": 0, "score": 2},
        ],
        "expected_deliverables": ["segments.xlsx"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 8: Expense Categorization
# ═══════════════════════════════════════════════════════════════
def task_expenses():
    ref = ws("task_expenses")
    df = pd.DataFrame({
        "Date": ["2024-01-05", "2024-01-12", "2024-01-15", "2024-01-20",
                 "2024-02-01", "2024-02-10", "2024-02-15", "2024-02-28",
                 "2024-03-05", "2024-03-15"],
        "Description": ["Office Supplies", "Client Dinner", "Software License",
                        "Travel - NYC", "Office Supplies", "Team Lunch",
                        "Cloud Hosting", "Travel - LA", "Printer Paper", "Conference"],
        "Category": ["Supplies", "Meals", "Software", "Travel", "Supplies",
                     "Meals", "Software", "Travel", "Supplies", "Travel"],
        "Amount": [250, 320, 1200, 850, 180, 210, 1500, 920, 95, 2500],
    })
    df.to_csv(os.path.join(ref, "expenses.csv"), index=False)

    # Supplies: 250+180+95 = 525
    # Meals: 320+210 = 530
    # Software: 1200+1500 = 2700
    # Travel: 850+920+2500 = 4270
    # Total: 8025

    return {
        "task_id": "task_expenses",
        "prompt": (
            "Analyze reference/expenses.csv. Group by Category and calculate "
            "total spending per category and overall total. "
            "Create output/expense_summary.xlsx with sheet 'By Category' "
            "showing Category, Total Amount, and a row for Grand Total."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/expense_summary.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/expense_summary.xlsx", "sheet": "By Category", "score": 1},
            {"check": "cell_value", "file": "output/expense_summary.xlsx", "sheet": "By Category",
             "lookup": {"Category": "Travel"}, "column": "Total Amount", "expected": 4270, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/expense_summary.xlsx", "sheet": "By Category",
             "lookup": {"Category": "Software"}, "column": "Total Amount", "expected": 2700, "tolerance": 1, "score": 2},
            {"check": "contains_text", "file": "output/expense_summary.xlsx", "text": "8025", "score": 2},
        ],
        "expected_deliverables": ["expense_summary.xlsx"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 9: Loan Amortization
# ═══════════════════════════════════════════════════════════════
def task_loan():
    ref = ws("task_loan")
    df = pd.DataFrame({
        "Loan ID": ["L001", "L002", "L003"],
        "Principal": [100000, 250000, 50000],
        "Annual Rate (%)": [5.0, 4.5, 6.0],
        "Term (Years)": [10, 15, 5],
    })
    df.to_excel(os.path.join(ref, "loans.xlsx"), index=False)

    # Monthly payment for L001: P=100000, r=0.05/12, n=120
    # M = P * r(1+r)^n / ((1+r)^n - 1)
    def monthly(p, rate, years):
        r = rate / 100 / 12
        n = years * 12
        return p * r * (1 + r) ** n / ((1 + r) ** n - 1)

    m1 = round(monthly(100000, 5.0, 10), 2)  # ~1060.66
    m2 = round(monthly(250000, 4.5, 15), 2)  # ~1912.48
    m3 = round(monthly(50000, 6.0, 5), 2)    # ~966.64

    return {
        "task_id": "task_loan",
        "prompt": (
            "Analyze reference/loans.xlsx. For each loan, calculate the "
            "monthly payment using the standard amortization formula: "
            "M = P * r(1+r)^n / ((1+r)^n - 1) where r = annual rate / 12, "
            "n = term in months. "
            "Create output/loan_payments.xlsx with sheet 'Payments' "
            "showing Loan ID, Principal, Monthly Payment."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/loan_payments.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/loan_payments.xlsx", "sheet": "Payments", "score": 1},
            {"check": "cell_value", "file": "output/loan_payments.xlsx", "sheet": "Payments",
             "lookup": {"Loan ID": "L001"}, "column": "Monthly Payment", "expected": m1, "tolerance": 5, "score": 2},
            {"check": "cell_value", "file": "output/loan_payments.xlsx", "sheet": "Payments",
             "lookup": {"Loan ID": "L002"}, "column": "Monthly Payment", "expected": m2, "tolerance": 5, "score": 2},
            {"check": "cell_value", "file": "output/loan_payments.xlsx", "sheet": "Payments",
             "lookup": {"Loan ID": "L003"}, "column": "Monthly Payment", "expected": m3, "tolerance": 5, "score": 2},
        ],
        "expected_deliverables": ["loan_payments.xlsx"],
    }


# ═══════════════════════════════════════════════════════════════
# Task 10: Multi-sheet Consolidation
# ═══════════════════════════════════════════════════════════════
def task_consolidation():
    ref = ws("task_consolidation")
    q1 = pd.DataFrame({
        "Product": ["Alpha", "Beta", "Gamma"],
        "Units": [100, 200, 150],
        "Revenue": [5000, 12000, 7500],
    })
    q2 = pd.DataFrame({
        "Product": ["Alpha", "Beta", "Gamma"],
        "Units": [120, 180, 200],
        "Revenue": [6000, 10800, 10000],
    })
    q3 = pd.DataFrame({
        "Product": ["Alpha", "Beta", "Gamma"],
        "Units": [90, 220, 170],
        "Revenue": [4500, 13200, 8500],
    })
    with pd.ExcelWriter(os.path.join(ref, "quarterly_data.xlsx")) as w:
        q1.to_excel(w, sheet_name="Q1", index=False)
        q2.to_excel(w, sheet_name="Q2", index=False)
        q3.to_excel(w, sheet_name="Q3", index=False)

    # Alpha total: 100+120+90=310 units, 5000+6000+4500=15500 revenue
    # Beta total:  200+180+220=600 units, 12000+10800+13200=36000 revenue
    # Gamma total: 150+200+170=520 units, 7500+10000+8500=26000 revenue

    return {
        "task_id": "task_consolidation",
        "prompt": (
            "Consolidate quarterly data from reference/quarterly_data.xlsx "
            "(sheets Q1, Q2, Q3). For each product, sum Units and Revenue "
            "across all quarters. Create output/consolidated.xlsx with "
            "sheet 'Annual' showing Product, Total Units, Total Revenue."
        ),
        "checks": [
            {"check": "file_exists", "file": "output/consolidated.xlsx", "score": 1},
            {"check": "sheet_exists", "file": "output/consolidated.xlsx", "sheet": "Annual", "score": 1},
            {"check": "cell_value", "file": "output/consolidated.xlsx", "sheet": "Annual",
             "lookup": {"Product": "Alpha"}, "column": "Total Units", "expected": 310, "tolerance": 0, "score": 2},
            {"check": "cell_value", "file": "output/consolidated.xlsx", "sheet": "Annual",
             "lookup": {"Product": "Beta"}, "column": "Total Revenue", "expected": 36000, "tolerance": 1, "score": 2},
            {"check": "cell_value", "file": "output/consolidated.xlsx", "sheet": "Annual",
             "lookup": {"Product": "Gamma"}, "column": "Total Revenue", "expected": 26000, "tolerance": 1, "score": 2},
            {"check": "row_count", "file": "output/consolidated.xlsx", "sheet": "Annual",
             "expected": 3, "score": 1},
        ],
        "expected_deliverables": ["consolidated.xlsx"],
    }


def main():
    tasks = [
        task_sales(),
        task_budget(),
        task_employees(),
        task_revenue_trend(),
        task_product_profit(),
        task_invoice_recon(),
        task_customer_segments(),
        task_expenses(),
        task_loan(),
        task_consolidation(),
    ]

    manifest_path = os.path.join(DATA, "task_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(tasks, f, indent=2)

    print(f"Created {len(tasks)} tasks:\n")
    for t in tasks:
        ref_dir = os.path.join(WORKSPACES, t["task_id"], "reference")
        files = os.listdir(ref_dir)
        n_checks = len(t["checks"])
        max_score = sum(c["score"] for c in t["checks"])
        print(f"  {t['task_id']:25s}  files={files}  checks={n_checks}  max_score={max_score}")

    print(f"\nManifest: {manifest_path}")


if __name__ == "__main__":
    main()
