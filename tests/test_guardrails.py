import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.guardrails.policy_guardrails import PolicyGuardrailEvaluator
from app.schemas.expense import (
    EmployeeExpenseReport,
    ExpenseItem,
    ExpenseCategory,
    ComplianceStatus,
)

def test_guardrails_flag_prohibited_items() -> None:
    report = EmployeeExpenseReport(
        employee_name="Inácio Buemo",
        employee_email="inacio@example.com",
        trip_or_purpose="Tech Conference 2026",
        trip_duration_days=1,
        expenses=[
            ExpenseItem(
                description="Dinner with Beer",
                category=ExpenseCategory.MEAL,
                amount=Decimal("35.00"),
                expense_date=date(2026, 9, 24),
                has_itemized_receipt=True,
                contains_alcohol=True,
            ),
            ExpenseItem(
                description="Hotel Room",
                category=ExpenseCategory.LODGING,
                amount=Decimal("180.00"),
                has_itemized_receipt=True,
                contains_alcohol=False,
            ),
        ],
    )

    evaluator = PolicyGuardrailEvaluator()
    result = evaluator.evaluate_report(report)

    assert result.overall_status == ComplianceStatus.NEEDS_REVIEW
    assert result.total_compliant == Decimal("180.00")
    assert "Alcoholic beverages are strictly prohibited" in result.itemized_audit[0].violations[0]
    print("\nGuardrail test passed successfully!")


if __name__ == "__main__":
    test_guardrails_flag_prohibited_items()
