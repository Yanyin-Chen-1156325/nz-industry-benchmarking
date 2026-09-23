"""Source-backed contracts used by the Phase 5 Silver validation."""

from __future__ import annotations

SILVER_SCHEMA_VERSION = "aes-silver-v1"
VALUE_DECIMAL_PRECISION = 38
VALUE_DECIMAL_SCALE = 18

EXPECTED_AGGREGATION_LEVELS = ("Level 1", "Level 3", "Level 4")

# Exact code/name/category/unit definitions observed and documented in Phase 0.
# Repeated codes are intentional: code alone is not a valid metadata lookup key.
EXPECTED_VARIABLE_DEFINITIONS = (
    ("H01", "Total income", "Financial performance", "Dollars (millions)"),
    (
        "H02",
        "Sales of goods not further processed",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H03",
        "Sales of other goods and services",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H04",
        "Sales of goods and services",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H04",
        "Sales, government funding, grants and subsidies",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H05",
        "Interest, dividends and donations",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H06",
        "Government funding, grants and subsidies",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H06",
        "Sales, government funding, grants and subsidies",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H07",
        "Non-operating income",
        "Financial performance",
        "Dollars (millions)",
    ),
    ("H08", "Total expenditure", "Financial performance", "Dollars (millions)"),
    (
        "H09",
        "Interest and donations",
        "Financial performance",
        "Dollars (millions)",
    ),
    ("H10", "Indirect taxes", "Financial performance", "Dollars (millions)"),
    ("H11", "Depreciation", "Financial performance", "Dollars (millions)"),
    (
        "H12",
        "Salaries and wages paid",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H13",
        "Redundancy and severance",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H14",
        "Salaries and wages to self employed commission agents",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H17",
        "Purchases of goods bought for resale",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H18",
        "Other Purchases and operating expenses",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H18",
        "Other purchases and operating expenses",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H19",
        "Purchases and other operating expenses",
        "Financial performance",
        "Dollars (millions)",
    ),
    (
        "H20",
        "Non-operating expenses",
        "Financial performance",
        "Dollars (millions)",
    ),
    ("H21", "Opening stocks", "Financial performance", "Dollars (millions)"),
    ("H22", "Closing stocks", "Financial performance", "Dollars (millions)"),
    (
        "H23",
        "Surplus before income tax",
        "Financial performance",
        "Dollars (millions)",
    ),
    ("H24", "Total assets", "Financial position", "Dollars (millions)"),
    ("H25", "Current assets", "Financial position", "Dollars (millions)"),
    (
        "H26",
        "Fixed tangible assets",
        "Financial position",
        "Dollars (millions)",
    ),
    (
        "H27",
        "Additions to fixed assets",
        "Financial position",
        "Dollars (millions)",
    ),
    (
        "H28",
        "Disposals of fixed assets",
        "Financial position",
        "Dollars (millions)",
    ),
    ("H29", "Other assets", "Financial position", "Dollars (millions)"),
    (
        "H30",
        "Total equity and liabilities",
        "Financial position",
        "Dollars (millions)",
    ),
    (
        "H31",
        "Shareholders funds or owners equity",
        "Financial position",
        "Dollars (millions)",
    ),
    ("H32", "Current liabilities", "Financial position", "Dollars (millions)"),
    ("H33", "Other liabilities", "Financial position", "Dollars (millions)"),
    (
        "H34",
        "Total income per employee count",
        "Financial ratios",
        "Dollars",
    ),
    ("H35", "Surplus per employee count", "Financial ratios", "Dollars"),
    ("H36", "Current ratio", "Financial ratios", "Percentage"),
    ("H37", "Quick ratio", "Financial ratios", "Percentage"),
    (
        "H38",
        "Margin on sales of goods for resale",
        "Financial ratios",
        "Percentage",
    ),
    ("H39", "Return on equity", "Financial ratios", "Percentage"),
    ("H40", "Return on total assets", "Financial ratios", "Percentage"),
    ("H41", "Liabilities structure", "Financial ratios", "Percentage"),
)
