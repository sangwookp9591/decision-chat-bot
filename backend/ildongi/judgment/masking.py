"""Common external-model boundary, including injected and shadow clients."""
import threading

from ildongi.domain.masking import MaskingSession, mask_for_external

__all__ = ['MaskingClient', 'MaskingSession', 'mask_for_external']


class MaskingClient:
    """Copy and mask every outgoing string with one thread-safe token table.

    State fields and question text share the same table; question IDs and criteria
    keys remain protocol keys. Raw input remains available for internal evidence.
    """

    external_masking = True

    def __init__(self, inner, policy=None, *, session=None, guidance=()):
        self.inner = inner
        self.session = session or MaskingSession()
        self.policy = {**(policy or {}), '_masking_session': self.session}
        self.guidance = tuple(guidance)
        self.lock = threading.Lock()
        # The native client's own transport guard uses the same configured policy.
        if hasattr(inner, 'mask_policy'):
            inner.mask_policy = self.policy

    def _copy(self, value):
        if isinstance(value, str):
            return mask_for_external(value, self.policy)
        if isinstance(value, dict):
            return {key: self._copy(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._copy(item) for item in value]
        return value

    def payload(self, state, question_map):
        with self.lock:
            if self.guidance:
                state = {**state, 'operating_guidance': list(self.guidance)}
            return self._copy(state), self._copy(question_map)

    def ask(self, state, question_map):
        state, question_map = self.payload(state, question_map)
        return self.inner.ask(state, question_map)

    def __getattr__(self, name):
        return getattr(self.inner, name)
