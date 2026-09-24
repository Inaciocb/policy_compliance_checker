from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)]


class ExpenseCategory(str, Enum):
    MEAL = "meal"
    LODGING = "lodging"
    TRANSPORTATION = "transportation"
    COURSE = "course"
    OTHER = "other"


class ExpenseItem(BaseModel):
    description: str = Field(description="Brief description of the purchase")
    category: ExpenseCategory = Field(description="Category of the expense")
    amount: Money = Field(description="USD cost of one whole meal, one lodging night, or one purchase; never include a subtotal twice")
    expense_date: Optional[date] = Field(default=None, description="Actual expense date, or null if unreadable")
    currency: str = Field(default="USD", description="Currency printed on receipt; UNKNOWN if absent")
    has_itemized_receipt: bool = Field(
        description="True if an itemized receipt is provided, False if missing or summary-only"
    )
    contains_alcohol: bool = Field(
        default=False, description="True if alcoholic beverages are present in this item"
    )


class EmployeeExpenseReport(BaseModel):
    employee_name: str = Field(description="Full name of the employee")
    employee_email: str = Field(description="Email of the employee submitting the report")
    trip_or_purpose: str = Field(description="Purpose of trip or course name")
    trip_duration_days: int = Field(
        default=1, ge=1, description="Duration of the trip in days"
    )
    expenses: List[ExpenseItem] = Field(min_length=1, description="List of extracted individual expenses")


class ComplianceStatus(str, Enum):
    APPROVED = "APPROVED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REJECTED = "REJECTED"


class AuditResultItem(BaseModel):
    item: ExpenseItem
    is_compliant: bool
    violations: List[str] = Field(default_factory=list)


class ManagerAuditReport(BaseModel):
    employee_name: str
    employee_email: str
    trip_or_purpose: str
    total_requested: Money
    total_compliant: Money
    overall_status: ComplianceStatus
    itemized_audit: List[AuditResultItem]
    summary_for_manager: str = Field(
        description="Clear, executive summary explaining why items were approved or flagged"
    )
