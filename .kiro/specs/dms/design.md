# Design Document

## Overview

Das DMS (Document Management System) ist eine CLI-basierte Anwendung, die lokale PDF-Dateien in ein durchsuchbares, KI-gestütztes Wissenssystem transformiert. Das System kombiniert moderne NLP-Techniken mit Vektordatenbanken, um präzise, kontextbezogene Antworten auf natürlichsprachige Fragen zu liefern.

## Architecture

Das System folgt einer modularen Architektur mit klarer Trennung von Datenverarbeitung, Speicherung und Abfrage:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  Core Services  │────│   Data Layer    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    ┌────▼────┐              ┌───▼───┐              ┌────▼────┐
    │ Import  │              │ RAG   │              │ Vector  │
    │ Export  │              │ Query │              │   DB    │
    │ Manage  │              │ Cat.  │              │ Meta DB │
    └─────────┘              └───────┘              └─────────┘
```

### Core Components

1. **CLI Interface**: Benutzerinteraktion und Kommandoverarbeitung
2. **PDF Processor**: Textextraktion und Chunking
3. **Categorization Engine**: Automatische Inhaltskategorisierung
4. **Vector Store**: Semantische Suche und Embedding-Speicherung
5. **RAG Engine**: Retrieval und Antwortgenerierung
6. **Metadata Manager**: Dateimetadaten und Kategorien

## Components and Interfaces

### PDF Processor
```python
class PDFProcessor:
    def extract_text(self, pdf_path: str) -> DocumentContent
    def needs_ocr(self, pdf_path: str) -> bool
    def extract_with_ocr(self, pdf_path: str) -> DocumentContent
    def create_chunks(self, text: str, chunk_size: int = 1000) -> List[TextChunk]
    def extract_metadata(self, pdf_path: str) -> DocumentMetadata
```

**Intelligente OCR-Erkennung:**
- Primäre Textextraktion mit pdfplumber/PyPDF2
- Automatische Erkennung von bildbasierten PDFs durch Text-zu-Seiten-Verhältnis
- OCR-Fallback mit Tesseract nur bei niedrigem Textanteil (<50 Zeichen/Seite)
- Caching von OCR-Ergebnissen zur Vermeidung von Wiederholung
- Konfigurierbare OCR-Schwellenwerte für verschiedene Dokumenttypen

**Funktionalität:**
- Hybride Textextraktion (Text + OCR bei Bedarf)
- Intelligentes Chunking mit Überlappung zur Kontexterhaltung
- Metadatenextraktion (Seitenzahlen, Dateigröße, Erstellungsdatum, OCR-Status)

### Categorization Engine
```python
class CategorizationEngine:
    def categorize_document(self, content: str) -> CategoryResult
    def extract_entities(self, content: str, category: str) -> Dict[str, Any]
    def get_confidence_score(self, content: str, category: str) -> float
```

**Kategorisierungslogik:**
- Regelbasierte Erkennung für strukturierte Dokumente (Rechnungen, Kontoauszüge)
- NLP-basierte Klassifikation für komplexere Dokumenttypen
- Entity-Extraktion für Rechnungssteller, Bankdaten, Beträge
- Konfidenz-Scores für unsichere Kategorisierungen

### Vector Store
```python
class VectorStore:
    def add_documents(self, chunks: List[TextChunk]) -> None
    def similarity_search(self, query: str, filters: Dict) -> List[SearchResult]
    def delete_documents(self, document_id: str) -> None
```

**Technische Implementierung:**
- ChromaDB als embedded Vektordatenbank (SQLite-ähnlich, keine Server-Installation nötig)
- Lokale Datenspeicherung in ~/.dms/ Verzeichnis
- Sentence-Transformers für deutsche Embeddings (lokal, keine API-Calls)
- Metadaten-Filterung für Zeitraum- und Kategoriesuche
- Hybrid-Suche (semantisch + keyword-basiert)
- Backup/Restore durch einfaches Kopieren der Datenbankdateien

### RAG Engine
```python
class RAGEngine:
    def query(self, question: str, filters: Optional[Dict] = None) -> RAGResponse
    def generate_answer(self, context: List[str], question: str, model: str = None) -> str
    def format_sources(self, results: List[SearchResult]) -> List[Source]

class LLMProvider:
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1")
    def chat_completion(self, messages: List[Dict], model: str) -> str
    def list_available_models(self) -> List[str]
    def get_model_info(self, model: str) -> Dict
```

**Antwortgenerierung:**
- Retrieval der relevantesten Textpassagen
- Kontext-Aggregation mit Quellenangaben
- Flexible LLM-Integration über OpenRouter API
- Konfigurierbare Modellauswahl (GPT-4, Claude, Llama, etc.)
- Fallback-Strategien bei API-Fehlern
- Strukturierte Ausgabe mit Konfidenz-Scores

## Data Models

### DocumentContent
```python
@dataclass
class DocumentContent:
    file_path: str
    text: str
    page_count: int
    file_size: int
    import_date: datetime
    directory_structure: str  # z.B. "2024/03/Rechnungen"
    ocr_used: bool
    text_extraction_method: str  # "direct", "ocr", "hybrid"
    processing_time: float
```

### TextChunk
```python
@dataclass
class TextChunk:
    id: str
    document_id: str
    content: str
    page_number: int
    chunk_index: int
    embedding: Optional[List[float]]
```

### CategoryResult
```python
@dataclass
class CategoryResult:
    primary_category: str  # "Rechnung", "Kontoauszug", etc.
    confidence: float
    entities: Dict[str, Any]  # Rechnungssteller, Bank, Beträge
    suggested_categories: List[Tuple[str, float]]
```

### RAGResponse
```python
@dataclass
class RAGResponse:
    answer: str
    sources: List[Source]
    confidence: float
    search_results_count: int
```

## Error Handling

### PDF Processing Errors
- **Corrupted PDFs**: Überspringen mit Logging, Fortsetzung mit nächster Datei
- **Password-protected PDFs**: Warnung ausgeben, Benutzer informieren
- **Large Files**: Chunking-Strategien für Speicher-effiziente Verarbeitung
- **OCR Failures**: Fallback auf verfügbaren Text, Warnung bei komplettem OCR-Fehler
- **Mixed Content PDFs**: Intelligente Kombination von direktem Text und OCR-Text

### Search and Query Errors
- **No Results Found**: Klare Kommunikation, Suchvorschläge anbieten
- **LLM API Failures**: Automatischer Fallback auf alternative Modelle via OpenRouter
- **Vector DB Errors**: Graceful degradation auf keyword-basierte Suche

### CLI Error Handling
- **Invalid Paths**: Pfadvalidierung mit hilfreichen Fehlermeldungen
- **Permission Errors**: Klare Anweisungen für Berechtigungsprobleme
- **Disk Space**: Warnung bei niedrigem Speicherplatz

## Testing Strategy

### Unit Tests
- PDF-Textextraktion mit verschiedenen PDF-Formaten
- Chunking-Algorithmen mit Edge Cases
- Kategorisierungslogik mit Beispieldokumenten
- Vector Store Operationen (CRUD)

### Integration Tests
- End-to-End Import-Prozess mit Testverzeichnissen
- RAG-Pipeline mit bekannten Frage-Antwort-Paaren
- CLI-Kommandos mit verschiedenen Parameterkombinationen

### Performance Tests
- Bulk-Import von großen PDF-Sammlungen
- Suchgeschwindigkeit bei verschiedenen Datenbankgrößen
- Memory-Usage bei großen Dokumenten

### Test Data
- Beispiel-PDFs verschiedener Kategorien (Rechnungen, Kontoauszüge, Verträge)
- Synthetische Verzeichnisstrukturen (JAHR/MONAT/Kategorie)
- Testfragen mit erwarteten Antworten

### Database Architecture

**Lokale Datenspeicherung:**
```
~/.dms/
├── chroma.db/          # ChromaDB Vektordatenbank (embedded)
├── metadata.sqlite     # SQLite für Metadaten und Kategorien
├── config.json         # Konfigurationsdatei (inkl. OpenRouter Settings)
├── models.json         # Verfügbare Modelle und Präferenzen
└── logs/              # Anwendungslogs
```

**Konfigurationsbeispiel (config.json):**
```json
{
  "openrouter": {
    "api_key": "your-api-key",
    "default_model": "anthropic/claude-3-sonnet",
    "fallback_models": ["openai/gpt-4", "meta-llama/llama-2-70b-chat"]
  },
  "embedding": {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  },
  "ocr": {
    "threshold": 50,
    "language": "deu"
  }
}
```

**Vorteile dieser Architektur:**
- Keine Server-Installation oder -wartung erforderlich
- Vollständig offline funktionsfähig
- Einfache Backups durch Dateikopie
- Portabel zwischen verschiedenen Systemen
- Keine Netzwerkabhängigkeiten für Core-Funktionalität### 
OCR Processing Strategy

**Intelligente OCR-Entscheidung:**
1. **Erste Analyse**: Extrahiere Text mit pdfplumber
2. **Qualitätsprüfung**: Berechne Text-Dichte pro Seite
3. **OCR-Trigger**: Wenn <50 Zeichen/Seite → OCR aktivieren
4. **Hybride Verarbeitung**: Kombiniere verfügbaren Text mit OCR-Text
5. **Caching**: Speichere OCR-Ergebnisse zur Wiederverwendung

**OCR-Konfiguration:**
- Tesseract mit deutschen Sprachpaketen
- Bildvorverarbeitung für bessere Erkennung
- Konfidenz-Scores für OCR-Qualität
- Batch-Verarbeitung für Performance### L
LM Integration Strategy

**OpenRouter Integration:**
- Einheitliche API für verschiedene Modellprovider
- Dynamische Modellauswahl basierend auf Verfügbarkeit und Kosten
- Automatische Fallback-Kette bei API-Fehlern
- Rate-Limiting und Kostenüberwachung
- Modell-spezifische Prompt-Optimierung

**CLI-Kommandos für Modellverwaltung:**
```bash
dms models list                    # Verfügbare Modelle anzeigen
dms models set claude-3-sonnet     # Standard-Modell setzen
dms query "Frage" --model gpt-4    # Spezifisches Modell für Abfrage
dms models test                    # Modell-Konnektivität testen
```