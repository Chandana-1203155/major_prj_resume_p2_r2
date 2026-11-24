"""ATS score computation, status classification and weight rebalancing."""

from config import DEFAULT_ATS_WEIGHTS


# -------------------------------------------------
# ATS SCORE
# -------------------------------------------------
def compute_ats_score(ats_breakdown, weights):
    if not ats_breakdown:
        return 0.0
    total = 0.0
    for key, weight in weights.items():
        if key not in DEFAULT_ATS_WEIGHTS:
            continue
        total += ats_breakdown.get(key, 0) * (weight / 100.0)
    return round(total, 2)


def classify_candidate_status(matched_count, min_required, score, shortlist_th, hold_th, reject_th):
    """
    Single source of truth for the Shortlisted / AI Evaluated / Rejected
    classification, based purely on the deterministic score + matched-skill
    count — no LLM involved. Used both at analysis time (evaluate_candidate,
    stored as candidate['status']) and live in the Shortlist Workspace,
    which recomputes this fresh against whatever thresholds are currently
    set (so it stays correct even if the recruiter adjusts thresholds or
    weights after the batch was analyzed, rather than relying on the
    possibly-stale value stored at analysis time).
    """
    if matched_count >= min_required and score >= shortlist_th:
        return "Shortlisted"
    elif matched_count >= min_required and score >= hold_th:
        return "AI Evaluated"
    elif matched_count < min_required and score < reject_th:
        return "Rejected"
    else:
        return "AI Evaluated"


def rebalance_weights(changed_key, new_value, weights):
    """Adjust remaining weights so total stays 100."""
    if changed_key not in DEFAULT_ATS_WEIGHTS:
        raise ValueError(f"Unknown ATS weight component: {changed_key}")

    keys = list(DEFAULT_ATS_WEIGHTS)
    others = [key for key in keys if key != changed_key]
    weights = {
        key: weights.get(key, DEFAULT_ATS_WEIGHTS[key])
        for key in keys
    }
    changed_value = max(0, min(100, float(new_value)))
    other_total = sum(weights[key] for key in others)
    remaining = 100 - changed_value

    if other_total == 0:
        share = remaining / len(others)
        for key in others:
            weights[key] = share
    else:
        for key in others:
            weights[key] = remaining * (weights[key] / other_total)
    weights[changed_key] = changed_value

    weights = {key: round(weights[key], 1) for key in keys}
    remainder = round(100 - sum(weights.values()), 1)
    if remainder:
        adjustment_key = max(
            others,
            key=lambda key: (
                100 - weights[key] if remainder > 0 else weights[key]
            ),
        )
        weights[adjustment_key] = round(weights[adjustment_key] + remainder, 1)
    return weights
