"""
The World's Simplest State Machine
A coffee vending machine with 4 states
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime


# Step 1: Define all possible states
class State(str, Enum):
    IDLE = "IDLE"              # Waiting for money
    HAS_MONEY = "HAS_MONEY"    # Money inserted
    BREWING = "BREWING"        # Making coffee
    COMPLETE = "COMPLETE"      # Coffee ready


# Step 2: Define all possible events (things that can happen)
class Event(str, Enum):
    INSERT_MONEY = "INSERT_MONEY"
    BREW_COFFEE = "BREW_COFFEE"
    BREWING_DONE = "BREWING_DONE"
    TAKE_COFFEE = "TAKE_COFFEE"


# Step 3: Define what moves are legal
TRANSITIONS = {
    # (current_state, event) → next_state
    (State.IDLE, Event.INSERT_MONEY): State.HAS_MONEY,
    (State.HAS_MONEY, Event.BREW_COFFEE): State.BREWING,
    (State.BREWING, Event.BREWING_DONE): State.COMPLETE,
    (State.COMPLETE, Event.TAKE_COFFEE): State.IDLE,
}


# Step 4: The state machine itself
@dataclass
class VendingMachine:
    current_state: State = State.IDLE
    history: list = None  # Track what happened
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
    
    def apply_event(self, event: Event):
        """Try to apply an event. Fails if the move is illegal."""
        
        # Look up: is this move allowed?
        next_state = TRANSITIONS.get((self.current_state, event))
        
        if next_state is None:
            raise ValueError(
                f"Illegal move: {self.current_state} + {event} is not allowed"
            )
        
        # Record what happened (audit trail)
        self.history.append({
            "from": self.current_state,
            "event": event,
            "to": next_state,
            "time": datetime.now().isoformat(),
        })
        
        # Move to new state
        old_state = self.current_state
        self.current_state = next_state
        
        print(f"✅ {old_state} + {event} → {next_state}")
        return next_state


# Step 5: Let's use it!
if __name__ == "__main__":
    machine = VendingMachine()
    
    print("Initial state:", machine.current_state)
    print()
    
    # Happy path - everything works
    machine.apply_event(Event.INSERT_MONEY)
    machine.apply_event(Event.BREW_COFFEE)
    machine.apply_event(Event.BREWING_DONE)
    machine.apply_event(Event.TAKE_COFFEE)
    
    print("\n📜 Full history:")
    for entry in machine.history:
        print(f"  {entry['from']} → {entry['to']} via {entry['event']}")
    
    print("\n❌ Now let's try something illegal:")
    try:
        # You can't brew coffee when machine is idle!
        machine.apply_event(Event.BREW_COFFEE)
    except ValueError as e:
        print(f"  ERROR: {e}")