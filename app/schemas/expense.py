from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ExpenseCategory(str, Enum):
    MEAL = "meal"
    LODGING = "lodging"
    TRANSPORTATION = "transportation"
    COURSE = "course"
    OTHER = "other"


class ExpenseItem(BaseModel):
    description: str = Field(description="Brief description of the purchase")
    category: ExpenseCategory = Field(description="Category of the expense")
    amount: float = Field(description="Total cost of the expense in USD")
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
    trip_duration_days: Optional[int] = Field(
        default=1, description="Duration of the trip in days"
    )
    expenses: List[ExpenseItem] = Field(description="List of extracted individual expenses")


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
    total_requested: float
    total_compliant: float
    overall_status: ComplianceStatus
    itemized_audit: List[AuditResultItem]
    summary_for_manager: str = Field(
        description="Clear, executive summary explaining why items were approved or flagged"
    )