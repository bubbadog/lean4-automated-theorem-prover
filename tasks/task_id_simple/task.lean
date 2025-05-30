import Mathlib

def addTwo (a : Int) (b : Int) : Int :=
  {{code}}

def addTwo_spec (a : Int) (b : Int) (result : Int) : Prop :=
  result = a + b

example (a : Int) (b : Int) : addTwo_spec a b (addTwo a b) := by
  unfold addTwo addTwo_spec
  {{proof}}
