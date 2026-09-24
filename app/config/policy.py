from decimal import Decimal
from typing import Dict, List, Any

POLICY_CONFIG: Dict[str, Any] = {
    "MEALS": {
        "SINGLE_MEAL_MAX": Decimal("40.0"),
        "DAILY_MEAL_MAX": Decimal("80.0"),
    },
    "LODGING": {
        "NIGHTLY_MAX": Decimal("200.0"),
    },
    "COURSE": {
        "YEARLY_MAX": Decimal("1500.0"),
    },
    "RECEIPT_REQUIRED_THRESHOLD": Decimal("10.0"),
}
