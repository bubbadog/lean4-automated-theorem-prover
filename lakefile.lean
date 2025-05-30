import Lake
open Lake DSL

package BerkeleyMooc where
  leanOptions := #[
    ⟨`pp.unicode.fun, true⟩,
    ⟨`pp.proofs.withType, false⟩
  ]

lean_lib BerkeleyMooc where
  -- Library configuration

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git"
