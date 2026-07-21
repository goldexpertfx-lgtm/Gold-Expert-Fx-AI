from aiogram.fsm.storage.memory import MemoryStorage

# Shared across main.py (Dispatcher) and admin_handlers.py (manual state resets),
# so both refer to the same in-memory FSM state.
storage = MemoryStorage()
