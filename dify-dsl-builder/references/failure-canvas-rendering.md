# Failure: Canvas Rendering

## Symptom

AI Hub imports the DSL but cannot open the workflow canvas, opens a blank canvas, crashes while rendering, hides child nodes, or shows broken branches.

## Root Cause

Common causes include missing nodes referenced by edges, orphaned edges, invalid parent-child canvas contracts, broken iteration child references, inconsistent iteration item types, malformed canvas positions, duplicate node IDs, or selectors that point to unavailable outputs.

YAML parsing can still pass when the canvas contract is invalid.

## Prevention Rule

Validate graph integrity beyond syntax. Every edge must connect existing nodes. Nested and iteration child nodes must preserve parent references, canvas placement, item contracts, and output selectors expected by the platform.

During repair, preserve business logic first and change only the structural fields required to make the canvas render.

For native AIGC component nodes, "the model appears in the dropdown" is not enough evidence. A video-generation selector that imports but shows `模型信息加载失败` must be quarantined in the component fingerprint and rejected by `--aigc-quality` until a saved canvas export can be re-imported and opened cleanly. Do not convert that uncertainty into a user-facing question such as whether the workflow should stop, downgrade, or use a packaged tool.

If a live QA session can manually select the model and save the canvas, but the export action cannot be completed, treat the result as partial UI evidence only. It confirms that the UI model selector is reachable; it does not confirm the correct YAML representation. Do not use the selected UI label or model-list ID to generate a "fixed" DSL unless a saved export or another verified DSL proves the exact node shape.

After fixing a native AIGC node selector, also inspect downstream Code nodes and packaging prompts. A canvas can run successfully while the returned `diagnostics_json` still reports an obsolete selector. That is still a product-quality defect because business users and future agents may trust the diagnostic field. Keep `selected_model`, `selected_model_note`, and generated asset metadata aligned with the actual exported node selector.

## Validator Or Test

Run a structural check for node ID uniqueness, edge source/target existence, parent references, iteration item type consistency, child canvas nodes, and selectors.

When live QA is available, perform a separate AI Hub canvas-open test and report it independently from static validation.
