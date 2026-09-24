from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from typing import List
from pydantic import TypeAdapter
from app.config.policy import POLICY_CONFIG
from app.schemas.expense import (
    EmployeeExpenseReport,
    ManagerAuditReport,
    AuditResultItem,
    ComplianceStatus,
    ExpenseCategory,
    ExpenseItem,
    Money,
)


class PolicyGuardrailEvaluator:
    def evaluate_report(
        self,
        report: EmployeeExpenseReport,
        *,
        course_spend_by_year: Mapping[int, Decimal | int | str] | None = None,
    ) -> ManagerAuditReport:
        """History must come from a trusted ledger, excluding this submission.

        Missing course history is unknown, not zero. All items in an over-cap
        group are withheld for review; this evaluator does not prorate claims.
        """
        money_adapter = TypeAdapter(Money)
        history = {year: money_adapter.validate_python(amount)
                   for year, amount in (course_spend_by_year or {}).items()}
        audited_items: list[AuditResultItem] = []
        groups: dict[tuple[ExpenseCategory, date | int], list[int]] = {}
        for item in report.expenses:
            violations = self._validate_item(item)
            if item.category in (ExpenseCategory.MEAL, ExpenseCategory.COURSE):
                if item.expense_date is None:
                    violations.append("Expense date is missing; cumulative limits cannot be verified.")
                else:
                    period = item.expense_date if item.category == ExpenseCategory.MEAL else item.expense_date.year
                    groups.setdefault((item.category, period), []).append(len(audited_items))
            audited_items.append(AuditResultItem(item=item, is_compliant=not violations, violations=violations))

        for (category, period), indices in groups.items():
            total = sum((audited_items[i].item.amount for i in indices), Decimal("0"))
            violation = None
            if category == ExpenseCategory.MEAL and total > POLICY_CONFIG["MEALS"]["DAILY_MEAL_MAX"]:
                violation = f"Meal total for {period} (${total:.2f}) exceeds daily limit ($80.00)."
            elif category == ExpenseCategory.COURSE:
                if not isinstance(period, int):
                    raise TypeError("Course spending must be grouped by year.")
                if period not in history:
                    violation = f"Trusted course spending history for {period} is missing."
                elif total + history[period] > POLICY_CONFIG["COURSE"]["YEARLY_MAX"]:
                    violation = f"Cumulative course spending for {period} exceeds annual limit ($1500.00)."
            if violation:
                for i in indices:
                    audited_items[i].violations.append(violation)
                    audited_items[i].is_compliant = False

        total_requested = sum((a.item.amount for a in audited_items), Decimal("0"))
        total_compliant = sum((a.item.amount for a in audited_items if a.is_compliant), Decimal("0"))
        has_violations = any(not a.is_compliant for a in audited_items)
        status = (ComplianceStatus.APPROVED if not has_violations else
                  ComplianceStatus.NEEDS_REVIEW if total_compliant > 0 else ComplianceStatus.REJECTED)
        return ManagerAuditReport(
            employee_name=report.employee_name, employee_email=report.employee_email,
            trip_or_purpose=report.trip_or_purpose, total_requested=total_requested,
            total_compliant=total_compliant, overall_status=status,
            itemized_audit=audited_items,
            summary_for_manager=self._generate_summary(report.employee_name, total_requested, total_compliant, status, audited_items),
        )

    def _validate_item(self, item: ExpenseItem) -> List[str]:
        violations: List[str] = []
        if item.currency != "USD":
            violations.append("Only documented USD expenses can be evaluated; currency requires review.")

        if item.amount > POLICY_CONFIG["RECEIPT_REQUIRED_THRESHOLD"] and not item.has_itemized_receipt:
            violations.append(
                f"Missing itemized receipt for expense over ${POLICY_CONFIG['RECEIPT_REQUIRED_THRESHOLD']:.2f}."
            )

        if item.contains_alcohol:
            violations.append("Alcoholic beverages are strictly prohibited by company policy.")

        if item.category == ExpenseCategory.MEAL:
            if item.amount > POLICY_CONFIG["MEALS"]["SINGLE_MEAL_MAX"]:
                violations.append(
                    f"Single meal cost (${item.amount:.2f}) exceeds maximum limit of "
                    f"${POLICY_CONFIG['MEALS']['SINGLE_MEAL_MAX']:.2f}."
                )

        elif item.category == ExpenseCategory.LODGING:
            if item.amount > POLICY_CONFIG["LODGING"]["NIGHTLY_MAX"]:
                violations.append(
                    f"Lodging cost (${item.amount:.2f}) exceeds nightly limit of "
                    f"${POLICY_CONFIG['LODGING']['NIGHTLY_MAX']:.2f}."
                )

        elif item.category == ExpenseCategory.COURSE:
            if item.amount > POLICY_CONFIG["COURSE"]["YEARLY_MAX"]:
                violations.append(
                    f"Course cost (${item.amount:.2f}) exceeds annual limit of "
                    f"${POLICY_CONFIG['COURSE']['YEARLY_MAX']:.2f}."
                )

        return violations

    def _generate_summary(
        self,
        employee_name: str,
        requested: Decimal,
        compliant: Decimal,
        status: ComplianceStatus,
        audits: List[AuditResultItem],
    ) -> str:
        lines = [
            f"Audit Report for {employee_name}:",
            f"Status: {status.value}",
            f"Requested Total: ${requested:.2f}",
            f"Policy-Compliant Amount: ${compliant:.2f}",
        ]

        flagged = [a for a in audits if not a.is_compliant]
        if flagged:
            lines.append("\nFlagged Items:")
            for a in flagged:
                lines.append(f"- {a.item.description} (${a.item.amount:.2f}): {'; '.join(a.violations)}")
        else:
            lines.append("\nAll items strictly comply with POL-2026-EXP policy.")

        return "\n".join(lines)
