# API Discoveries

Documented quirks found through systematic probing of the Elyos interview APIs.

## Weather API (`/weather`)

### 1. Variable Response Shape
Some cities return a flat object, others return an array of conditions.

**Flat format (e.g., London, Paris, Tokyo):**
```json
{"location": "London", "temperature_c": 8.1, "condition": "Clear", "humidity": 81}
```

**Array format (e.g., Berlin, New York, Beijing):**
```json
{"location": "Berlin", "conditions": [{"temperature_c": 7.2, "condition": "Clear", "humidity": 61}, ...], "note": "Multiple conditions reported"}
```

The pattern is not predictable by city name length or word count. Code must handle both shapes.

### 2. Rate Limiting Returns HTTP 200 (not 429)
Rapid successive calls trigger rate limiting, but the response is HTTP 200 with:
```json
{"status": "throttled", "message": "Rate limit exceeded. Please wait.", "retry_after_seconds": 1, "data": null}
```

This is dangerous because `raise_for_status()` won't catch it. Must check for `status: "throttled"` in the response body.

### 3. Standard Error Responses
- Missing `location` param: HTTP 422 (FastAPI validation)
- Empty `location=""`: HTTP 404, `{"error": "Location \"\" not found"}`
- Invalid API key: HTTP 401, `{"error": "Invalid or missing API key"}`
- Unknown location: HTTP 404, `{"error": "Location \"xyz\" not found"}`

## Research API (`/research`)

### 4. Intermittent Empty JSON Responses
Sometimes returns `{}` (empty object) with HTTP 200. This appears to happen intermittently, possibly on first request for a topic. Retrying after a delay typically returns a valid response.

### 5. Stale Cached Responses
Some topics return cached data with extra fields:
```json
{"topic": "climate change", "summary": "Research on 'climate change' from early 2024...", "cached": true, "cache_age_seconds": 26784000, "generated_at": "2024-03-15T09:00:00Z"}
```

The `cache_age_seconds` can be extremely large (months). Code should surface the staleness to the user.

### 6. Empty Topic Accepted
An empty string topic (`?topic=`) returns a valid-looking response with an empty topic field. Not an error, but nonsensical.

### 7. Standard Error Responses
- Missing `topic` param: HTTP 422 (FastAPI validation)
- Invalid API key: HTTP 401

## Handling Strategy

1. **Variable shape**: Normalize weather responses to always present a consistent format
2. **Throttling**: Check for `status: "throttled"` in body, retry after `retry_after_seconds`
3. **Empty responses**: Detect `{}` and retry once after a short delay
4. **Stale cache**: Include staleness warning when `cached: true` and age is large
