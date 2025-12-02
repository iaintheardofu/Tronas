"""
Deadline management service for Texas PIA compliance.
Tracks 10-day response deadlines, AG ruling timelines, and notifications.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum

from loguru import logger

from app.core.config import settings


class DeadlineType(str, Enum):
    INITIAL_RESPONSE = "initial_response"  # 10 business days
    EXTENSION = "extension"  # Additional 10 business days
    AG_SUBMISSION = "ag_submission"  # Must submit to AG within 10 days
    AG_RULING = "ag_ruling"  # 45 days after AG submission


class DeadlineManager:
    """
    Manages PIA request deadlines according to Texas Government Code Chapter 552.

    Key timelines:
    - 10 business days: Initial response deadline
    - Additional 10 business days: With proper notice to requester
    - 10 business days: To request AG ruling after receiving request
    - 45 days: AG has to respond after receiving ruling request
    """

    # Texas state holidays (would be updated annually)
    STATE_HOLIDAYS_2024 = [
        date(2024, 1, 1),    # New Year's Day
        date(2024, 1, 15),   # MLK Day
        date(2024, 2, 19),   # Presidents Day
        date(2024, 3, 2),    # Texas Independence Day
        date(2024, 3, 29),   # Good Friday
        date(2024, 4, 21),   # San Jacinto Day
        date(2024, 5, 27),   # Memorial Day
        date(2024, 6, 19),   # Juneteenth
        date(2024, 7, 4),    # Independence Day
        date(2024, 8, 27),   # LBJ Day
        date(2024, 9, 2),    # Labor Day
        date(2024, 11, 11),  # Veterans Day
        date(2024, 11, 28),  # Thanksgiving
        date(2024, 11, 29),  # Day after Thanksgiving
        date(2024, 12, 24),  # Christmas Eve
        date(2024, 12, 25),  # Christmas Day
        date(2024, 12, 26),  # Day after Christmas
    ]

    def __init__(self):
        self.holidays = set(self.STATE_HOLIDAYS_2024)
        # Generate 2025 holidays (would be maintained)
        self._generate_2025_holidays()

    def _generate_2025_holidays(self):
        """Generate estimated 2025 holidays."""
        holidays_2025 = [
            date(2025, 1, 1),    # New Year's Day
            date(2025, 1, 20),   # MLK Day
            date(2025, 2, 17),   # Presidents Day
            date(2025, 3, 2),    # Texas Independence Day
            date(2025, 4, 18),   # Good Friday
            date(2025, 4, 21),   # San Jacinto Day
            date(2025, 5, 26),   # Memorial Day
            date(2025, 6, 19),   # Juneteenth
            date(2025, 7, 4),    # Independence Day
            date(2025, 8, 27),   # LBJ Day
            date(2025, 9, 1),    # Labor Day
            date(2025, 11, 11),  # Veterans Day
            date(2025, 11, 27),  # Thanksgiving
            date(2025, 11, 28),  # Day after Thanksgiving
            date(2025, 12, 24),  # Christmas Eve
            date(2025, 12, 25),  # Christmas Day
            date(2025, 12, 26),  # Day after Christmas
        ]
        self.holidays.update(holidays_2025)

    def is_business_day(self, check_date: date) -> bool:
        """
        Check if a date is a business day (not weekend or holiday).

        Args:
            check_date: Date to check

        Returns:
            True if business day
        """
        # Check if weekend
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Check if holiday
        if check_date in self.holidays:
            return False

        return True

    def add_business_days(
        self,
        start_date: date,
        business_days: int,
    ) -> date:
        """
        Add business days to a date.

        Args:
            start_date: Starting date
            business_days: Number of business days to add

        Returns:
            Resulting date
        """
        current = start_date
        days_added = 0

        while days_added < business_days:
            current += timedelta(days=1)
            if self.is_business_day(current):
                days_added += 1

        return current

    def calculate_response_deadline(
        self,
        received_date: date,
        expedited: bool = False,
    ) -> date:
        """
        Calculate the PIA response deadline.

        Args:
            received_date: Date request was received
            expedited: Whether this is an expedited request

        Returns:
            Response deadline date
        """
        business_days = settings.PIA_RESPONSE_DEADLINE_DAYS  # 10 by default
        return self.add_business_days(received_date, business_days)

    def calculate_extension_deadline(
        self,
        original_deadline: date,
    ) -> date:
        """
        Calculate extended deadline (10 additional business days).

        Args:
            original_deadline: Original response deadline

        Returns:
            Extended deadline date
        """
        return self.add_business_days(
            original_deadline,
            settings.PIA_EXTENSION_MAX_DAYS
        )

    def calculate_ag_submission_deadline(
        self,
        received_date: date,
    ) -> date:
        """
        Calculate deadline to submit AG ruling request.
        Must be within 10 business days of receiving the PIA request.

        Args:
            received_date: Date request was received

        Returns:
            AG submission deadline
        """
        return self.add_business_days(received_date, 10)

    def calculate_ag_ruling_deadline(
        self,
        submission_date: date,
    ) -> date:
        """
        Calculate when AG ruling is due.
        AG has 45 calendar days to respond.

        Args:
            submission_date: Date submitted to AG

        Returns:
            AG ruling deadline
        """
        return submission_date + timedelta(days=settings.PIA_AG_RULING_DEADLINE_DAYS)

    def get_all_deadlines(
        self,
        received_date: date,
    ) -> Dict[str, date]:
        """
        Calculate all relevant deadlines for a request.

        Args:
            received_date: Date request was received

        Returns:
            Dictionary of all deadline dates
        """
        response_deadline = self.calculate_response_deadline(received_date)
        ag_submission_deadline = self.calculate_ag_submission_deadline(received_date)

        return {
            "response_deadline": response_deadline,
            "extension_deadline": self.calculate_extension_deadline(response_deadline),
            "ag_submission_deadline": ag_submission_deadline,
            "ag_ruling_deadline_if_submitted_today": self.calculate_ag_ruling_deadline(date.today()),
        }

    def get_business_days_remaining(
        self,
        deadline: date,
    ) -> int:
        """
        Calculate business days remaining until deadline.

        Args:
            deadline: Deadline date

        Returns:
            Number of business days remaining (negative if past)
        """
        today = date.today()

        if deadline < today:
            # Count business days past deadline (negative)
            days = 0
            current = deadline
            while current < today:
                current += timedelta(days=1)
                if self.is_business_day(current):
                    days -= 1
            return days
        else:
            # Count business days until deadline
            days = 0
            current = today
            while current < deadline:
                current += timedelta(days=1)
                if self.is_business_day(current):
                    days += 1
            return days

    def get_deadline_status(
        self,
        deadline: date,
    ) -> Dict[str, Any]:
        """
        Get comprehensive deadline status.

        Args:
            deadline: Deadline date

        Returns:
            Status information
        """
        days_remaining = self.get_business_days_remaining(deadline)
        today = date.today()

        if days_remaining < 0:
            status = "overdue"
            urgency = "critical"
        elif days_remaining == 0:
            status = "due_today"
            urgency = "critical"
        elif days_remaining <= 2:
            status = "urgent"
            urgency = "high"
        elif days_remaining <= 5:
            status = "approaching"
            urgency = "medium"
        else:
            status = "on_track"
            urgency = "low"

        return {
            "deadline": deadline.isoformat(),
            "business_days_remaining": days_remaining,
            "calendar_days_remaining": (deadline - today).days,
            "status": status,
            "urgency": urgency,
            "is_overdue": days_remaining < 0,
        }

    def get_notifications_due(
        self,
        requests: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get notification lists for requests approaching deadlines.

        Args:
            requests: List of PIA requests with deadline info

        Returns:
            Grouped notifications by urgency
        """
        notifications = {
            "critical": [],  # Due today or overdue
            "high": [],      # Due in 1-2 business days
            "medium": [],    # Due in 3-5 business days
        }

        for request in requests:
            deadline = request.get("response_deadline")
            if isinstance(deadline, str):
                deadline = date.fromisoformat(deadline)

            status = self.get_deadline_status(deadline)

            if status["urgency"] in notifications:
                notifications[status["urgency"]].append({
                    "request_number": request.get("request_number"),
                    "request_id": request.get("id"),
                    "deadline": deadline.isoformat(),
                    "days_remaining": status["business_days_remaining"],
                    "status": status["status"],
                    "requester_name": request.get("requester_name"),
                })

        return notifications

    def generate_deadline_report(
        self,
        requests: List[Dict[str, Any]],
    ) -> str:
        """
        Generate a deadline status report.

        Args:
            requests: List of PIA requests

        Returns:
            Formatted report string
        """
        notifications = self.get_notifications_due(requests)

        report_lines = [
            "=" * 60,
            "PIA REQUEST DEADLINE STATUS REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            "",
        ]

        # Critical items
        if notifications["critical"]:
            report_lines.extend([
                "🚨 CRITICAL - Immediate Action Required",
                "-" * 40,
            ])
            for item in notifications["critical"]:
                report_lines.append(
                    f"  • {item['request_number']}: {item['status'].upper()} "
                    f"({item['days_remaining']} business days)"
                )
            report_lines.append("")

        # High priority
        if notifications["high"]:
            report_lines.extend([
                "⚠️  HIGH PRIORITY - Due Within 2 Days",
                "-" * 40,
            ])
            for item in notifications["high"]:
                report_lines.append(
                    f"  • {item['request_number']}: Due {item['deadline']} "
                    f"({item['days_remaining']} business days)"
                )
            report_lines.append("")

        # Medium priority
        if notifications["medium"]:
            report_lines.extend([
                "📋 APPROACHING - Due Within 5 Days",
                "-" * 40,
            ])
            for item in notifications["medium"]:
                report_lines.append(
                    f"  • {item['request_number']}: Due {item['deadline']} "
                    f"({item['days_remaining']} business days)"
                )
            report_lines.append("")

        # Summary
        report_lines.extend([
            "=" * 60,
            "SUMMARY",
            f"  Critical: {len(notifications['critical'])}",
            f"  High Priority: {len(notifications['high'])}",
            f"  Approaching: {len(notifications['medium'])}",
            "=" * 60,
        ])

        return "\n".join(report_lines)


# Singleton instance
_deadline_manager: Optional[DeadlineManager] = None


def get_deadline_manager() -> DeadlineManager:
    """Get or create the deadline manager singleton."""
    global _deadline_manager
    if _deadline_manager is None:
        _deadline_manager = DeadlineManager()
    return _deadline_manager
