from typing import Dict, List, Any

POLICY_CONFIG: Dict[str, Any] = {
    "MEALS": {
        "SINGLE_MEAL_MAX": 40.0,
        "DAILY_MEAL_MAX": 80.0,
    },
    "LODGING": {
        "NIGHTLY_MAX": 200.0,
    },
    "COURSE": {
        "YEARLY_MAX": 1500.0,
    },
    "RECEIPT_REQUIRED_THRESHOLD": 10.0,
}