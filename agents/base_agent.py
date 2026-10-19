from __future__ import annotations


class BaseAgent:
    """Every agent in this project follows the same shape:
    decide() looks at the state and proposes actions.
    act() applies those actions.
    run() does both, in order, and logs what happened."""
    name = "BaseAgent"

    def decide(self, state):
        raise NotImplementedError

    def act(self, state, actions):
        raise NotImplementedError

    def run(self, state):
        actions = self.decide(state)
        if actions:
            self.act(state, actions)
            state.log_actions(self.name, actions)
        return actions

    @staticmethod
    def _new_id(prefix, state):
        state.counter += 1
        return f"{prefix}{state.counter}"