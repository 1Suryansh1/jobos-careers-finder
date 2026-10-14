> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tinyfish.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Structured Output

> Structured-output schema support for the output_schema request field

Use `output_schema` when you want TinyFish to return the final run result in a predictable JSON shape.

The same rules apply across the REST API, SDKs, CLI, Playground, and MCP integrations as they all forward to the same API validator.

## Example

```json theme={null}
{
  "output_schema": {
    "type": "object",
    "properties": {
      "title": { "type": "string" },
      "price": { "type": "number", "minimum": 0 },
      "published_at": {
        "type": "string",
        "format": "date-time",
        "nullable": true
      },
      "tags": {
        "type": "array",
        "items": { "type": "string" },
        "maxItems": 10
      }
    },
    "required": ["title", "price"],
    "propertyOrdering": ["title", "price", "published_at", "tags"]
  }
}
```

## The Schema Is the Contract

`output_schema` defines the exact shape of the result. When your schema and your prompt
disagree about whether to return a single object or a list, **the schema wins** — the
result is shaped to match the schema, not the wording of the prompt.

A schema that describes a single object returns a single object, even if the prompt asks
for "10 results". To return a list, the schema must say so explicitly (see below).

## Returning a List of Items

The top level must always be an object, so a list of results goes in an array field:

```json theme={null}
{
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "url": { "type": "string" }
          },
          "required": ["name", "url"]
        }
      }
    },
    "required": ["results"]
  }
}
```

Without the array field, a prompt like "list 10 tools" returns only the first match,
because the schema describes a single object.

## Top-Level Constraints

| Constraint | Rule |
| - | - |
| Top-level shape | Must be a JSON object. If `type` is present, it must be `object` |
| Top-level `anyOf` | Not supported. Put composition inside object fields instead |
| Size limit | Serialized schema must be 64KB or smaller |
| Nesting depth | Maximum depth is 10 |
| Boolean schema nodes | `true` and `false` schemas are not supported |
| Nullable values | Use `nullable: true`, not `type: ["string", "null"]` |

<Note>
  `type: "boolean"` is supported for fields in your result. What is not supported is using a schema node that is itself
  the literal boolean `true` or `false`.
</Note>

## Supported Types

| Type | Notes |
| - | - |
| `object` | Supports `properties`, `required`, and `propertyOrdering` |
| `array` | Supports `items`, `minItems`, and `maxItems` |
| `string` | Supports `enum` and `format` |
| `number` | Supports `minimum` and `maximum` |
| `integer` | Supports `minimum` and `maximum` |
| `boolean` | Supported as a field type |

## Supported Keywords

Any keyword outside this allowlist is rejected:

* `anyOf`
* `enum`
* `format`
* `items`
* `maxItems`
* `maximum`
* `minItems`
* `minimum`
* `nullable`
* `properties`
* `propertyOrdering`
* `required`
* `type`

## Important Rules

* Use `anyOf` for composition. `oneOf` is not supported.
* `enum` requires `type: "string"`, and every enum value must be a string.
* `format` requires `type: "string"`. Supported formats are `date`, `date-time`, `duration`, and `time`.
* `items`, `minItems`, and `maxItems` require `type: "array"`.
* `minimum` and `maximum` require `type: "number"` or `type: "integer"`.
* `propertyOrdering` requires `properties`, values must be unique, and every referenced field must exist in
  `properties`.
* `required` fields must also exist in `properties`, unless the requirement is being expressed inside an `anyOf` branch.
* Stored runs include the requested schema as `output_schema` on `GET /v1/runs/{id}` and `runs.list()`.

## Common Rewrites

| Instead of | Use |
| - | - |
| `oneOf` | `anyOf` |
| `const: "ready"` | `type: "string", enum: ["ready"]` |
| `type: ["string", "null"]` | `type: "string", nullable: true` |
| `type: ["number", "null"]` | `type: "number", nullable: true` |
| `type: ["integer", "null"]` | `type: "integer", nullable: true` |

## Commonly Rejected Keywords

These are not supported in `output_schema`:

* `additionalProperties`
* `const`
* `example`
* `examples`
* `oneOf`

Any other keyword outside the supported allowlist is also rejected.

## Example Errors

The API returns a `400` error before execution when the schema is invalid. Common validation messages include:

* `output_schema field "oneOf" is not supported at #. Use "anyOf" instead.`
* `output_schema top-level "anyOf" is not supported at #. Top-level schema must declare "type": "object".`
* `output_schema type arrays are not supported at #/properties/title. Use 'type: "string", nullable: true' instead.`
* `output_schema field "additionalProperties" is not supported at #.`
* `output_schema exceeds the maximum nesting depth of 10.`

## Related

* [Agent API Reference](/agent-api/reference)
* [Quick Start](/quick-start)
* [CLI Commands](/cli/commands)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.