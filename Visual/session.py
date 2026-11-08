"""UI state fingerprints; no framework or analysis dependencies."""

import hashlib
import json


def fingerprint(*values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, default=str).encode()).hexdigest()


def file_identity(name, raw):
    return fingerprint(name, hashlib.sha256(raw).hexdigest())


def reset_file_state(state, identity):
    """Clear file-dependent widget/result state when the selected file changes."""
    if state.get('file_identity') != identity:
        for key in list(state):
            if key.startswith(('cfg_', 'parse_', 'result_', 'loaded_')):
                del state[key]
        state['file_identity'] = identity


def results_current(state, signature):
    return state.get('result_signature') == signature and 'result_data' in state
