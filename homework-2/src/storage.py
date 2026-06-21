from __future__ import annotations

import threading
from typing import Optional

from .models import Category, Priority, Status, Ticket


class TicketStore:
    def __init__(self) -> None:
        self._data: dict[str, Ticket] = {}
        self._lock = threading.Lock()

    def add(self, ticket: Ticket) -> Ticket:
        with self._lock:
            self._data[ticket.id] = ticket
        return ticket

    def get(self, ticket_id: str) -> Optional[Ticket]:
        return self._data.get(ticket_id)

    def list(
        self,
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
        status: Optional[Status] = None,
    ) -> list[Ticket]:
        tickets = list(self._data.values())
        if category is not None:
            tickets = [t for t in tickets if t.category == category]
        if priority is not None:
            tickets = [t for t in tickets if t.priority == priority]
        if status is not None:
            tickets = [t for t in tickets if t.status == status]
        return tickets

    def update(self, ticket: Ticket) -> Ticket:
        with self._lock:
            self._data[ticket.id] = ticket
        return ticket

    def delete(self, ticket_id: str) -> bool:
        with self._lock:
            if ticket_id not in self._data:
                return False
            del self._data[ticket_id]
        return True

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


store = TicketStore()
