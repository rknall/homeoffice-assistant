# Local OCR for Expense Recognition

## Status
Idea - Not Started

## Problem
Paperless-ngx provides general OCR, but expense receipts need specialized parsing to extract structured data: amount, currency, vendor, date, and category hints. A more specialized local OCR model could pre-populate expense form fields.

## Proposed Solution: Ollama + Vision Model

### Why Ollama?
- User may already have Ollama running locally
- Vision models (LLaVA, Qwen2-VL) handle varied receipt formats without fine-tuning
- Prompt engineering is easier than training custom models
- No external API dependencies

### Alternative Models Considered

| Model | Size | Speed | Accuracy | Notes |
|-------|------|-------|----------|-------|
| **Donut** | ~400MB | Medium | High | End-to-end, receipt-trained variants exist |
| **PaddleOCR + Rules** | ~100MB | Fast | Medium | OCR + regex extraction |
| **Ollama + Vision LLM** | 4-8GB | Slow | Very High | LLaVA/Qwen-VL, flexible prompting |
| **docTR** | ~200MB | Fast | High | Good layout understanding |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Upload/Import  │────▶│  OCR Service     │────▶│  Expense Form   │
│  Document       │     │  (Ollama Vision) │     │  (Pre-filled)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## New Components

### Backend
- `OcrProvider` integration type (like Paperless, Immich)
- Config: Ollama URL, model name (e.g., `llava:13b`)
- `OcrService.extract_expense_data(image_bytes) -> ExpenseExtraction`

### Frontend
- Button on expense form: "Extract from Document"
- Loading state during OCR processing
- Pre-fill form fields with extracted data

## Data Schema

```python
class ExpenseExtraction(BaseModel):
    vendor: str | None
    amount: Decimal | None
    currency: str | None
    date: date | None
    category_hint: str | None  # "restaurant", "transport", etc.
    confidence: float
```

## Processing Flow

1. User clicks "Extract from Document" (or auto-triggered on upload)
2. Image/PDF sent to Ollama with structured prompt
3. JSON response parsed into `ExpenseExtraction`
4. Form fields pre-populated with extracted values
5. User reviews, adjusts, and saves

## Example Prompt (for Ollama Vision)

```
Analyze this receipt image and extract the following information as JSON:
- vendor: The store/company name
- amount: The total amount (number only, no currency symbol)
- currency: The currency code (EUR, USD, PLN, etc.)
- date: The transaction date in YYYY-MM-DD format
- category_hint: One of: restaurant, transport, accommodation, equipment, other

Return only valid JSON, no explanation.
```

## Configuration UI

Settings > Integrations > OCR Provider:
- Ollama URL (default: http://localhost:11434)
- Model name (default: llava:13b)
- Auto-extract on upload (toggle)
- Test connection button

## Considerations

- **Performance**: Vision models can be slow (5-15 seconds per image on CPU)
- **Accuracy**: May need prompt tuning for different receipt formats
- **Fallback**: Always allow manual entry if OCR fails
- **Languages**: Consider multilingual receipts (model dependent)

## Related
- Paperless-ngx integration (document source)
- Expense form (target for pre-fill)
