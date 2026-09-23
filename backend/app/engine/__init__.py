"""The protection engine: detectors -> rule engine -> action engine.

Nothing in this package imports discord.py or the database. It works on the
plain event dataclasses in ``events.py`` and talks to the outside world only
through the protocols in ``ports.py``, so the live bot, the demo simulator and
the tests all run exactly the same code.
"""
