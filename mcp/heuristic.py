import math

class Heuristic:
    """
    Represents a single weighted heuristic used for scoring nodes or channels.

    Calculates a normalized score (0-1) based on a value's position
    within the observed range (lowest to highest seen values), applies
    a directionality (lower values are better or higher values are better),
    and multiplies by a configured weight.
    """
    def __init__(self, weight: float, lower_is_better: bool, initial_lowest=float('inf'), initial_highest=float('-inf')):
        """
        Initializes a Heuristic instance.

        Args:
            weight: The importance factor (multiplier) for this heuristic's score.
            lower_is_better: True if lower values are considered better, False otherwise.
            initial_lowest: Pre-set lowest value (e.g., for binary 0/1 metrics).
            initial_highest: Pre-set highest value (e.g., for binary 0/1 metrics).
        """
        if not isinstance(weight, (int, float)) or weight < 0:
             raise ValueError("Weight must be a non-negative number.")
        if not isinstance(lower_is_better, bool):
             raise ValueError("lower_is_better must be a boolean.")

        self.weight = float(weight)
        self.lower_is_better = lower_is_better
        # Ensure initial bounds are logical floats
        try:
             self.lowest = float(initial_lowest)
        except (ValueError, TypeError):
             self.lowest = float('inf')
        try:
             self.highest = float(initial_highest)
        except (ValueError, TypeError):
             self.highest = float('-inf')

        # Handle cases like binary 0/1 where bounds are fixed and known
        if initial_lowest == 0 and initial_highest == 0:
             self.lowest = 0.0
             self.highest = 0.0
        if initial_lowest == 1 and initial_highest == 1:
             self.lowest = 1.0
             self.highest = 1.0
        # Ensure lowest is not higher than highest if pre-set
        if self.lowest > self.highest:
            # Do not automatically swap, maybe it's intended (though weird). Log a warning.
            print(f"Warning: Initial lowest ({self.lowest}) is greater than initial highest ({self.highest}). Check configuration.")
            # self.lowest, self.highest = self.highest, self.lowest # Avoid auto-swapping

    def update(self, value):
        """
        Updates the observed range (lowest/highest) with a new value.

        Args:
            value: The new value observed for this heuristic.
        """
        if self.weight == 0:
            return # No need to track range if weight is zero

        # Ignore None values during range update
        if value is None:
             return

        # Attempt conversion to float for comparison
        try:
            numeric_value = float(value)
            # Ignore NaN and Inf values as they break comparisons
            if not math.isfinite(numeric_value):
                # Optionally log this
                # print(f"Warning: Non-finite value '{value}' encountered during heuristic update. Skipping.")
                return
        except (ValueError, TypeError):
             # Optionally log this
             # print(f"Warning: Could not convert value '{value}' to float for heuristic update. Skipping.")
             return # Skip non-numeric or non-finite values

        if numeric_value > self.highest:
            self.highest = numeric_value
        if numeric_value < self.lowest:
            self.lowest = numeric_value

    def get_score(self, value) -> float:
        """
        Calculates the normalized and weighted score for a given value.

        Args:
            value: The value for which to calculate the score.

        Returns:
            The calculated score (float), ranging from 0 upwards.
        """
        if self.weight == 0:
            return 0.0

        # Handle None or non-numeric/non-finite values during scoring - return neutral score
        if value is None:
            return 0.0
        try:
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                 # print(f"Warning: Non-finite value '{value}' encountered during heuristic scoring. Returning 0 score.")
                 return 0.0
        except (ValueError, TypeError):
             # print(f"Warning: Could not convert value '{value}' to float for heuristic scoring. Returning 0 score.")
             return 0.0

        # --- Score Calculation Logic ---

        # 1. Handle case where range hasn't been established or is zero
        is_uninitialized = self.highest == float('-inf') or self.lowest == float('inf')
        is_zero_range = self.highest == self.lowest

        if is_uninitialized:
             # Cannot score reliably if no values have been seen
             return 0.0

        if is_zero_range:
            # Range is zero (highest == lowest). Score is full weight *if* value matches,
            # except if the single value is 0 and higher_is_better.
            if numeric_value == self.lowest: # or self.highest
                if self.lowest == 0 and not self.lower_is_better:
                    return 0.0 # Value is 0, range is 0, higher is better -> score 0
                else:
                    # Value matches the only value seen, give full weighted score
                    return 1.0 * self.weight
            else:
                 # Value doesn't match the single value seen? Should not happen if update called. Score 0.
                 return 0.0

        # --- Range is valid (lowest < highest) ---

        # 2. Normalize the value within the observed range [lowest, highest]
        # Clamp the value first to handle values outside the observed range gracefully
        clamped_value = max(self.lowest, min(self.highest, numeric_value))

        # Perform normalization
        score_normalized = (clamped_value - self.lowest) / (self.highest - self.lowest)

        # 3. Apply directionality (lower_is_better)
        if self.lower_is_better:
            final_score_before_weight = 1.0 - score_normalized
        else:
            final_score_before_weight = score_normalized

        # 4. Apply weight
        return final_score_before_weight * self.weight

    def __repr__(self):
        """Provides a developer-friendly representation of the heuristic."""
        direction = "lower_is_better" if self.lower_is_better else "higher_is_better"
        range_str = f"[{self.lowest}, {self.highest}]"
        if self.lowest == float('inf'): # Handle uninitialized case
             range_str = "[uninitialized]"
        return f"Heuristic(weight={self.weight:.3f}, range={range_str}, dir={direction})" 