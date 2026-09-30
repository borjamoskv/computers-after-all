"""
Harmonic Curator: Camelot Wheel toroidal distance, Simulated Annealing sequencing,
and 5-Act Narrative Architecture.
"""

import math
import random
from typing import List, Tuple
from .models import Track


def camelot_distance(k1: str, k2: str) -> float:
    """
    Computes harmonic distance on the Camelot wheel.
    Lower score = higher harmonic compatibility.
    """
    if not k1 or not k2:
        return 2.0

    try:
        num1, letter1 = int(k1[:-1]), k1[-1].upper()
        num2, letter2 = int(k2[:-1]), k2[-1].upper()
    except (ValueError, IndexError):
        return 3.0

    # Toroidal circular distance on 12-hour clock
    delta_num = min(abs(num1 - num2), 12 - abs(num1 - num2))

    if delta_num == 0 and letter1 == letter2:
        return 0.0  # Exact match
    if delta_num == 0 and letter1 != letter2:
        return 0.5  # Relative Major/Minor
    if delta_num == 1 and letter1 == letter2:
        return 1.0  # Perfect Fourth / Fifth
    if delta_num == 1 and letter1 != letter2:
        return 2.0  # Diagonal step
    if delta_num == 2 and letter1 == letter2:
        return 2.5  # Energy Boost (+2 tones)
    
    # Dissonant steps
    return 3.0 + delta_num * 1.2


class SetlistCurator:
    """Optimizes track sequence using TSP / Simulated Annealing with Camelot cost."""

    def __init__(self, weight_harmonic: float = 2.0, weight_bpm: float = 1.5, weight_energy: float = 1.0):
        self.w_h = weight_harmonic
        self.w_b = weight_bpm
        self.w_e = weight_energy

    def transition_cost(self, t1: Track, t2: Track) -> float:
        """Cost of transitioning from t1 to t2."""
        h_cost = camelot_distance(t1.camelot_key, t2.camelot_key)
        bpm_diff = abs(t1.bpm - t2.bpm)
        bpm_cost = (bpm_diff / max(t1.bpm, t2.bpm, 1.0)) * 100.0
        energy_cost = abs(t1.energy - t2.energy) * 5.0
        return self.w_h * h_cost + self.w_b * bpm_cost + self.w_e * energy_cost

    def total_cost(self, sequence: List[Track]) -> float:
        """Computes aggregate cost of entire track sequence."""
        return sum(self.transition_cost(sequence[i], sequence[i + 1]) for i in range(len(sequence) - 1))

    def optimize_sequence(self, tracks: List[Track], iterations: int = 1000) -> List[Track]:
        """
        Orders tracks to minimize harmonic friction and abrupt tempo jumps.
        Uses 2-opt simulated annealing.
        """
        n = len(tracks)
        if n <= 2:
            return tracks

        current = list(tracks)
        best = list(current)
        best_cost = self.total_cost(current)
        current_cost = best_cost

        temp = 10.0
        cooling = 0.995

        for _ in range(iterations):
            # Propose 2-opt reverse segment
            i, j = sorted(random.sample(range(n), 2))
            neighbor = current[:i] + current[i:j + 1][::-1] + current[j + 1:]
            neighbor_cost = self.total_cost(neighbor)

            delta = neighbor_cost - current_cost
            if delta < 0 or math.exp(-delta / max(temp, 1e-6)) > random.random():
                current = neighbor
                current_cost = neighbor_cost
                if current_cost < best_cost:
                    best = list(current)
                    best_cost = current_cost

            temp *= cooling

        return best
