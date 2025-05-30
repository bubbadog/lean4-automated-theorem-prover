import Mathlib
import Aesop

-- Test cases for minOfThree
example : minOfThree 1 2 3 = 1 := by rfl
example : minOfThree 3 1 2 = 1 := by rfl  
example : minOfThree (-1) 0 1 = (-1) := by rfl
example : minOfThree 5 5 5 = 5 := by rfl
