

def should_diversify(states_since_improvement, patience):
    """Indica quando cambiare la scelta del prossimo stato da esaminare."""
    return states_since_improvement >= patience