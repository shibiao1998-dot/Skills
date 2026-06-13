# Failure: Tool Node Shape

## Symptom

AI Hub rejects the DSL, the canvas fails to open, or runtime tool execution fails because a Tool node is missing required fields, has malformed parameters, lacks an empty configuration map, or references an unavailable private tool/provider.

## Root Cause

Tool node shapes are stricter than prompt text suggests. Old examples may omit fields such as `tool_configurations: {}`. Private AI Hub tools may require exact provider, credential, parameter, and component metadata that cannot be guessed.

External research cannot supply private AI Hub provider IDs or permissions.

## Prevention Rule

Preserve verified tool metadata from user-provided DSL evidence. When no configuration values are needed, still include required empty maps if the platform shape requires them.

Do not invent private tools, provider IDs, credentials, or permissions. Mark missing private metadata as a risk or required AI Hub confirmation.

## Validator Or Test

Static validation should inspect every Tool node for required shape fields, parameter selectors, empty configuration maps, provider/tool references, and unsupported missing values.

Live QA should separately test import, canvas open, and one runtime tool call when credentials and scope are available.
