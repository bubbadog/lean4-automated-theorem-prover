import Mathlib
import Aesop

def minOfThree (a : Int) (b : Int) (c : Int) : Int :=
  -- << CODE START >>
  {{code}}
  -- << CODE END >>

def minOfThree_spec_isMin (a : Int) (b : Int) (c : Int) (result : Int) : Prop :=
  -- << SPEC START >>
  (result ≤ a ∧ result ≤ b ∧ result ≤ c) ∧ (result = a ∨ result = b ∨ result = c)
  -- << SPEC END >>

example (a : Int) (b : Int) (c : Int) : minOfThree_spec_isMin a b c (minOfThree a b c) := by
  -- << PROOF START >>
  unfold minOfThree minOfThree_spec_isMin -- helper code
  {{proof}}
  -- << PROOF END >>
