# Requirements Document

## Introduction

Dieses Feature implementiert ein RAG (Retrieval-Augmented Generation) System, das PDF-Dateien verarbeitet, durchsuchbar macht und KI-gestützte Antworten auf Basis der PDF-Inhalte ermöglicht. Das System soll PDFs automatisch indexieren, relevante Textpassagen finden und diese für präzise, kontextbezogene Antworten nutzen.

## Requirements

### Requirement 1

**User Story:** Als Benutzer möchte ich PDF-Dateien über ein CLI importieren können, damit diese für KI-Suchen verfügbar werden.

#### Acceptance Criteria

1. WHEN ein Benutzer eine einzelne PDF-Datei über CLI importiert THEN soll das System die Datei verarbeiten und indexieren
2. WHEN ein Benutzer ein ganzes Verzeichnis (z.B. JAHR/MONAT) importiert THEN soll das System alle PDFs rekursiv verarbeiten
3. WHEN PDFs importiert werden THEN soll das System den Text extrahieren und in durchsuchbare Chunks aufteilen
4. WHEN der Text extrahiert wird THEN soll das System Metadaten wie Dateipfad, Verzeichnisstruktur, Dateiname und Seitenzahlen speichern
5. IF eine PDF-Datei beschädigt oder nicht lesbar ist THEN soll das System eine aussagekräftige Fehlermeldung anzeigen und mit den nächsten Dateien fortfahren

### Requirement 2

**User Story:** Als Benutzer möchte ich natürlichsprachige Fragen zu den PDF-Inhalten stellen können, damit ich schnell relevante Informationen finde.

#### Acceptance Criteria

1. WHEN ein Benutzer eine Frage stellt THEN soll das System relevante Textpassagen aus den PDFs finden
2. WHEN relevante Passagen gefunden werden THEN soll das System eine KI-generierte Antwort mit Quellenangaben liefern
3. WHEN keine relevanten Informationen gefunden werden THEN soll das System dies klar kommunizieren
4. WHEN eine Antwort generiert wird THEN soll das System die verwendeten PDF-Quellen und Seitenzahlen anzeigen

### Requirement 3

**User Story:** Als Benutzer möchte ich meine importierten PDFs über CLI verwalten können, damit ich den Überblick über meine Dokumente behalte.

#### Acceptance Criteria

1. WHEN ein Benutzer seine PDFs über CLI anzeigen möchte THEN soll das System eine Liste aller importierten Dokumente mit Verzeichnisstruktur zeigen
2. WHEN ein Benutzer ein PDF oder ganzes Verzeichnis über CLI löschen möchte THEN soll das System die Dokumente und alle zugehörigen Daten entfernen
3. WHEN ein Benutzer PDF-Details über CLI anzeigen möchte THEN soll das System Metadaten wie Dateipfad, Größe, Import-Datum und Seitenzahl anzeigen
4. WHEN ein Benutzer nach Verzeichnisstruktur (z.B. 2024/03/Rechnungen) filtern möchte THEN soll das System nur relevante PDFs anzeigen
5. IF ein PDF gelöscht wird THEN soll das System alle zugehörigen Vektordaten aus dem Index entfernen

### Requirement 4

**User Story:** Als Benutzer möchte ich die Suchqualität durch verschiedene Suchstrategien verbessern können, damit ich präzisere Ergebnisse erhalte.

#### Acceptance Criteria

1. WHEN das System Textchunks erstellt THEN soll es verschiedene Chunk-Größen und Überlappungen unterstützen
2. WHEN eine Suche durchgeführt wird THEN soll das System sowohl semantische als auch Keyword-basierte Suche kombinieren
3. WHEN Suchergebnisse angezeigt werden THEN soll das System Relevanz-Scores für gefundene Passagen anzeigen
4. IF mehrere ähnliche Passagen gefunden werden THEN soll das System diese nach Relevanz sortieren

### Requirement 5

**User Story:** Als Benutzer möchte ich das System über eine benutzerfreundliche Web-Oberfläche nutzen können, damit die Bedienung intuitiv ist.

#### Acceptance Criteria

1. WHEN ein Benutzer die Anwendung öffnet THEN soll eine übersichtliche Benutzeroberfläche angezeigt werden
2. WHEN ein Benutzer PDFs hochlädt THEN soll der Upload-Fortschritt visuell dargestellt werden
3. WHEN eine Frage gestellt wird THEN soll das System den Verarbeitungsstatus anzeigen
4. WHEN Antworten angezeigt werden THEN sollen diese formatiert und mit klickbaren Quellenverweisen versehen sein
### Re
quirement 6

**User Story:** Als Benutzer möchte ich die Verzeichnisstruktur (JAHR/MONAT/Kategorie) in meinen Suchen nutzen können, damit ich gezielt in bestimmten Zeiträumen oder Kategorien suchen kann.

#### Acceptance Criteria

1. WHEN ein Benutzer eine Frage stellt THEN soll das System optional Zeitraum- oder Kategoriefilter unterstützen
2. WHEN ein Benutzer nach "Rechnungen 2024/03" sucht THEN soll das System nur in PDFs aus diesem Verzeichnis suchen
3. WHEN Suchergebnisse angezeigt werden THEN soll das System die Verzeichnisstruktur als Kontext mit anzeigen
4. WHEN ein Benutzer alle verfügbaren Kategorien/Verzeichnisse anzeigen möchte THEN soll das System eine strukturierte Übersicht liefern#
## Requirement 7

**User Story:** Als Benutzer möchte ich, dass das System PDFs automatisch basierend auf ihrem Inhalt kategorisiert, damit ich bessere Suchfilter und Organisation habe.

#### Acceptance Criteria

1. WHEN ein PDF importiert wird THEN soll das System den Inhalt analysieren und automatisch Kategorien zuweisen (z.B. Rechnung, Kontoauszug, Vertrag)
2. WHEN eine Rechnung erkannt wird THEN soll das System zusätzlich den Rechnungssteller extrahieren und als Metadatum speichern
3. WHEN ein Kontoauszug erkannt wird THEN soll das System die Bank/das Konto identifizieren und als Metadatum speichern
4. WHEN Kategorien zugewiesen werden THEN soll das System diese als durchsuchbare Tags speichern
5. WHEN ein Benutzer sucht THEN soll das System Filterung nach automatisch erkannten Kategorien ermöglichen
6. WHEN ein Benutzer alle Kategorien anzeigen möchte THEN soll das System eine Übersicht mit Anzahl der Dokumente pro Kategorie zeigen
7. IF die automatische Kategorisierung unsicher ist THEN soll das System mehrere mögliche Kategorien mit Konfidenz-Scores vorschlagen