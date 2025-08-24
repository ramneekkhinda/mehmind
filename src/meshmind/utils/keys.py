"""
MeshMind Resource Keys Module

Utilities for generating consistent resource keys and identifiers.
"""

from typing import Optional


class ResourceKeys:
    """Utility class for generating resource keys."""

    @staticmethod
    def contact(contact_id: int) -> "ContactKeys":
        """Create contact-specific keys."""
        return ContactKeys(contact_id)

    @staticmethod
    def ticket(ticket_id: str) -> "TicketKeys":
        """Create ticket-specific keys."""
        return TicketKeys(ticket_id)

    @staticmethod
    def order(order_id: str) -> "OrderKeys":
        """Create order-specific keys."""
        return OrderKeys(order_id)

    @staticmethod
    def calendar(calendar_id: str) -> "CalendarKeys":
        """Create calendar-specific keys."""
        return CalendarKeys(calendar_id)


class ContactKeys:
    """Contact-specific resource keys."""

    def __init__(self, contact_id: int):
        self.contact_id = contact_id

    def email(self, template: Optional[str] = None) -> str:
        """Generate email resource key."""
        if template:
            return f"contact:{self.contact_id}/email/{template}"
        return f"contact:{self.contact_id}/email"

    def sms(self) -> str:
        """Generate SMS resource key."""
        return f"contact:{self.contact_id}/sms"

    def call(self) -> str:
        """Generate call resource key."""
        return f"contact:{self.contact_id}/call"


class TicketKeys:
    """Ticket-specific resource keys."""

    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id

    def process(self) -> str:
        """Generate ticket processing resource key."""
        return f"ticket:{self.ticket_id}/process"

    def response(self) -> str:
        """Generate ticket response resource key."""
        return f"ticket:{self.ticket_id}/response"

    def update(self) -> str:
        """Generate ticket update resource key."""
        return f"ticket:{self.ticket_id}/update"


class OrderKeys:
    """Order-specific resource keys."""

    def __init__(self, order_id: str):
        self.order_id = order_id

    def process(self) -> str:
        """Generate order processing resource key."""
        return f"order:{self.order_id}/process"

    def payment(self) -> str:
        """Generate payment resource key."""
        return f"order:{self.order_id}/payment"

    def inventory(self) -> str:
        """Generate inventory resource key."""
        return f"order:{self.order_id}/inventory"

    def confirmation(self) -> str:
        """Generate confirmation resource key."""
        return f"order:{self.order_id}/confirmation"


class CalendarKeys:
    """Calendar-specific resource keys."""

    def __init__(self, calendar_id: str):
        self.calendar_id = calendar_id

    def book(self, slot: str) -> str:
        """Generate calendar booking resource key."""
        return f"calendar:{self.calendar_id}/book/{slot}"

    def hold(self, slot: str) -> str:
        """Generate calendar hold resource key."""
        return f"calendar:{self.calendar_id}/hold/{slot}"
