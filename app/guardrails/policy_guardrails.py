from typing import List
from app.config.policy import POLICY_CONFIG
from app.schemas.expense import (
    EmployeeExpenseReport,
    ManagerAuditReport,
    AuditResultItem,
    ComplianceStatus,
    ExpenseCategory,
    ExpenseItem,
)


class PolicyGuardrailEvaluator:
    def evaluate_report(self, report: EmployeeExpenseReport) -> ManagerAuditReport:
        audited_items: List[AuditResultItem] = []
        total_requested = 0.0
        total_compliant = 0.0

        daily_meal_total = 0.0
        has_violations = False

        for item in report.expenses:
            violations = self._validate_item(item)

            if item.category == ExpenseCategory.MEAL:
                daily_meal_total += item.amount

            is_item_compliant = len(violations) == 0

            if is_item_compliant:
                total_compliant += item.amount
            else:
                has_violations = True

            total_requested += item.amount

            audited_items.append(
                AuditResultItem(
                    item=item,
                    is_compliant=is_item_compliant,
                    violations=violations,
                )
            )

        if (
            daily_meal_total
            > POLICY_CONFIG["MEALS"]["DAILY_MEAL_MAX"] * report.trip_duration_days
        ):
            has_violations = True
            for audit in audited_items:
                if audit.item.category == ExpenseCategory.MEAL:
                    audit.is_compliant = False
                    audit.violations.append(
                        f"Total meal expense (${daily_meal_total:.2f}) exceeds cumulative daily limit "
                        f"(${POLICY_CONFIG['MEALS']['DAILY_MEAL_MAX'] * report.trip_duration_days:.2f})."
                    )

        total_compliant = sum(a.item.amount for a in audited_items if a.is_compliant)

        if not has_violations:
            overall_status = ComplianceStatus.APPROVED
        elif total_compliant > 0:
            overall_status = ComplianceStatus.NEEDS_REVIEW
        else:
            overall_status = ComplianceStatus.REJECTED

        summary = self._generate_summary(
            report.employee_name, total_requested, total_compliant, overall_status, audited_items
        )

        return ManagerAuditReport(
            employee_name=report.employee_name,
            employee_email=report.employee_email,
            trip_or_purpose=report.trip_or_purpose,
            total_requested=round(total_requested, 2),
            total_compliant=round(total_compliant, 2),
            overall_status=overall_status,
            itemized_audit=audited_items,
            summary_for_manager=summary,
        )

    def _validate_item(self, item: ExpenseItem) -> List[str]:
        violations: List[str] = []

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
        requested: float,
        compliant: float,
        status: ComplianceStatus,
        audits: List[AuditResultItem],
    ) -> str:
        lines = [
            f"Audit Report for {employee_name}:",
            f"Status: {status.value}",
            f"Requested Total: ${requested:.2f}",
            f"Approved Compliant Amount: ${compliant:.2f}",
        ]

        flagged = [a for a in audits if not a.is_compliant]
        if flagged:
            lines.append("\nFlagged Items:")
            for a in flagged:
                lines.append(f"- {a.item.description} (${a.item.amount:.2f}): {'; '.join(a.violations)}")
        else:
            lines.append("\nAll items strictly comply with POL-2026-EXP policy.")

        return "\n".join(lines)