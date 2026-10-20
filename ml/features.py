"""Feature definitions shared by data preparation and training.

The application tracks five indicators per student per semester. The model
artifact records which of them it was trained on, so inference only uses
features the model actually knows about.
"""

APP_FEATURES = ["cgpa", "sgpa", "attendance_pct", "backlogs", "fee_paid"]

FEATURE_LABELS = {
    "cgpa": "CGPA",
    "sgpa": "SGPA (latest semester)",
    "attendance_pct": "Attendance %",
    "backlogs": "Active backlogs",
    "fee_paid": "Fee payment status",
}
