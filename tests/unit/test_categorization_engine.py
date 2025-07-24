"""Tests for document categorization engine"""

import pytest
from dms.categorization.engine import CategorizationEngine
from dms.models import CategoryResult


class TestCategorizationEngine:
    """Test cases for CategorizationEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = CategorizationEngine()
    
    def test_categorize_empty_content(self):
        """Test categorization with empty content"""
        result = self.engine.categorize_document("")
        
        assert result.primary_category == "Unbekannt"
        assert result.confidence == 0.0
        assert result.entities == {}
        assert result.suggested_categories == []
    
    def test_categorize_invoice_document(self):
        """Test categorization of invoice document"""
        invoice_content = """
        RECHNUNG
        
        Musterfirma GmbH
        Musterstraße 123
        12345 Musterstadt
        
        Rechnungsnummer: R-2024-001
        Rechnungsdatum: 15.03.2024
        Fälligkeitsdatum: 15.04.2024
        
        Rechnungsempfänger:
        Max Mustermann
        Beispielweg 456
        67890 Beispielstadt
        
        Pos. Beschreibung                 Menge  Einzelpreis  Gesamtpreis
        1    Beratungsleistung            10h    100,00 €     1.000,00 €
        
        Nettobetrag:                                         1.000,00 €
        MwSt. 19%:                                            190,00 €
        Bruttobetrag:                                       1.190,00 €
        
        Zahlbar bis: 15.04.2024
        """
        
        result = self.engine.categorize_document(invoice_content)
        
        assert result.primary_category == "Rechnung"
        assert result.confidence > 0.5
        assert "rechnungssteller" in result.entities
        assert "rechnungsnummer" in result.entities
        assert "betrag" in result.entities
        assert result.entities["rechnungsnummer"] == "R-2024-001"
        assert "1.190,00" in result.entities["betrag"]
    
    def test_categorize_bank_statement(self):
        """Test categorization of bank statement"""
        bank_statement_content = """
        Deutsche Bank AG
        Kontoauszug Nr. 3/2024
        
        Kontoinhaber: Max Mustermann
        Kontonummer: 1234567890
        IBAN: DE89 3704 0044 0532 0130 00
        BIC: COBADEFFXXX
        
        Auszugszeitraum: 01.03.2024 bis 31.03.2024
        
        Alter Saldo:                                        2.500,00 €
        
        Buchungstag  Wertstellung  Verwendungszweck                    Betrag
        05.03.2024   05.03.2024    Gehalt März 2024                 +3.500,00 €
        10.03.2024   10.03.2024    Miete Wohnung                    -1.200,00 €
        15.03.2024   15.03.2024    Supermarkt Einkauf                 -85,50 €
        20.03.2024   20.03.2024    Lastschrift Strom                 -120,00 €
        
        Neuer Saldo:                                        4.594,50 €
        """
        
        result = self.engine.categorize_document(bank_statement_content)
        
        assert result.primary_category == "Kontoauszug"
        assert result.confidence > 0.5
        assert "bank" in result.entities
        assert "kontonummer" in result.entities
        assert "Deutsche Bank AG" in result.entities["bank"]
        assert result.entities["kontonummer"] in ["1234567890", "DE89 3704 0044 0532 0130 00"]
    
    def test_categorize_contract_document(self):
        """Test categorization of contract document"""
        contract_content = """
        ARBEITSVERTRAG
        
        zwischen
        
        Musterfirma GmbH
        vertreten durch den Geschäftsführer
        Musterstraße 123, 12345 Musterstadt
        
        - nachfolgend "Arbeitgeber" genannt -
        
        und
        
        Herrn Max Mustermann
        Beispielweg 456, 67890 Beispielstadt
        
        - nachfolgend "Arbeitnehmer" genannt -
        
        § 1 Vertragsgegenstand
        Der Arbeitnehmer wird als Softwareentwickler eingestellt.
        
        § 2 Arbeitszeit und Vergütung
        Die regelmäßige Arbeitszeit beträgt 40 Stunden pro Woche.
        
        § 3 Laufzeit
        Das Arbeitsverhältnis beginnt am 01.04.2024 und ist unbefristet.
        
        § 4 Kündigung
        Das Arbeitsverhältnis kann von beiden Seiten mit einer Frist von 
        4 Wochen zum Monatsende gekündigt werden.
        
        Datum der Unterzeichnung: 15.03.2024
        
        ________________                    ________________
        Arbeitgeber                         Arbeitnehmer
        """
        
        result = self.engine.categorize_document(contract_content)
        
        assert result.primary_category == "Vertrag"
        assert result.confidence > 0.5
        assert "vertragspartner" in result.entities
        assert "vertragsart" in result.entities
        assert result.entities["vertragsart"].upper() == "ARBEITSVERTRAG"
    
    def test_extract_entities_invoice(self):
        """Test entity extraction for invoice category"""
        invoice_content = """
        Rechnung Nr. INV-2024-042
        
        Tech Solutions GmbH
        Innovationsstraße 789
        
        Bruttobetrag: 2.380,00 €
        """
        
        entities = self.engine.extract_entities(invoice_content, "Rechnung")
        
        assert "rechnungssteller" in entities
        assert "rechnungsnummer" in entities
        assert "betrag" in entities
        assert entities["rechnungsnummer"] == "INV-2024-042"
        assert "Tech Solutions GmbH" in entities["rechnungssteller"]
        assert "2.380,00" in entities["betrag"]
    
    def test_extract_entities_bank_statement(self):
        """Test entity extraction for bank statement category"""
        bank_content = """
        Sparkasse Musterstadt
        Kontonummer: 9876543210
        IBAN: DE12 3456 7890 1234 5678 90
        """
        
        entities = self.engine.extract_entities(bank_content, "Kontoauszug")
        
        assert "bank" in entities
        assert "kontonummer" in entities
        assert "Sparkasse Musterstadt" in entities["bank"]
        assert entities["kontonummer"] in ["9876543210", "DE12 3456 7890 1234 5678 90"]
    
    def test_extract_entities_contract(self):
        """Test entity extraction for contract category"""
        contract_content = """
        Mietvertrag
        
        Vertragspartner: Immobilien AG
        Laufzeit: unbefristet ab 01.05.2024
        """
        
        entities = self.engine.extract_entities(contract_content, "Vertrag")
        
        assert "vertragspartner" in entities
        assert "vertragsart" in entities
        assert "laufzeit" in entities
        assert "Immobilien AG" in entities["vertragspartner"]
        assert "Mietvertrag" in entities["vertragsart"]
    
    def test_categorize_ambiguous_document(self):
        """Test categorization of document with mixed signals"""
        ambiguous_content = """
        Geschäftsbrief
        
        Sehr geehrte Damen und Herren,
        
        hiermit bestätigen wir den Erhalt Ihrer Rechnung vom 10.03.2024.
        Die Zahlung erfolgt wie vereinbart bis zum 10.04.2024.
        
        Unser Kontoauszug zeigt die Überweisung bereits an.
        
        Mit freundlichen Grüßen
        Musterfirma GmbH
        """
        
        result = self.engine.categorize_document(ambiguous_content)
        
        # Should still categorize but with lower confidence
        assert result.primary_category in ["Rechnung", "Kontoauszug", "Unbekannt"]
        assert len(result.suggested_categories) >= 0
    
    def test_calculate_category_score(self):
        """Test internal category scoring method"""
        content = "rechnung rechnungsnummer fälligkeitsdatum mwst"
        patterns = ["rechnung", "rechnungsnummer", "fälligkeitsdatum", "mwst"]
        
        score = self.engine._calculate_category_score(content, patterns)
        
        assert score > 0
        assert isinstance(score, float)
    
    def test_extract_entities_empty_patterns(self):
        """Test entity extraction with empty patterns"""
        entities = self.engine._extract_entities("test content", {})
        
        assert entities == {}
    
    def test_extract_entities_no_matches(self):
        """Test entity extraction when no patterns match"""
        patterns = {"test_entity": [r"nonexistent_pattern"]}
        entities = self.engine._extract_entities("test content", patterns)
        
        assert entities == {}
    
    def test_multiple_entity_values(self):
        """Test extraction of multiple values for same entity type"""
        content = """
        Rechnung R-001
        Rechnung R-002
        Rechnung R-003
        """
        
        entities = self.engine.extract_entities(content, "Rechnung")
        
        assert "rechnungsnummer" in entities
        # Should return first unique match
        assert entities["rechnungsnummer"] == "R-001"
    
    def test_get_confidence_score(self):
        """Test confidence scoring for specific categories"""
        invoice_content = """
        RECHNUNG
        Rechnungsnummer: R-2024-001
        Bruttobetrag: 1.190,00 €
        """
        
        confidence = self.engine.get_confidence_score(invoice_content, "Rechnung")
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.3  # Should have reasonable confidence for clear invoice
    
    def test_get_confidence_score_empty_content(self):
        """Test confidence scoring with empty content"""
        confidence = self.engine.get_confidence_score("", "Rechnung")
        
        assert confidence == 0.0
    
    def test_get_confidence_score_invalid_category(self):
        """Test confidence scoring with invalid category"""
        confidence = self.engine.get_confidence_score("test content", "InvalidCategory")
        
        assert confidence == 0.0
    
    def test_categorize_document_with_manual_override(self):
        """Test manual category override functionality"""
        ambiguous_content = """
        Geschäftsbrief mit Rechnung erwähnt
        Kontoauszug wird auch erwähnt
        """
        
        # Test automatic categorization
        auto_result = self.engine.categorize_document(ambiguous_content)
        
        # Test manual override
        manual_result = self.engine.categorize_document_with_override(
            ambiguous_content, 
            manual_category="Vertrag"
        )
        
        assert manual_result.primary_category == "Vertrag"
        assert len(manual_result.suggested_categories) > 0
        assert auto_result.primary_category in [cat for cat, _ in manual_result.suggested_categories]
    
    def test_categorize_document_with_invalid_override(self):
        """Test manual override with invalid category falls back to automatic"""
        content = "RECHNUNG Rechnungsnummer: R-001"
        
        result = self.engine.categorize_document_with_override(
            content, 
            manual_category="InvalidCategory"
        )
        
        # Should fall back to automatic categorization
        assert result.primary_category == "Rechnung"
    
    def test_enhanced_confidence_scoring(self):
        """Test enhanced confidence scoring with competition"""
        # Content that could be both invoice and contract
        mixed_content = """
        RECHNUNG für Vertragsleistungen
        
        Vertrag Nr. 123
        Rechnungsnummer: R-2024-001
        Vertragspartner: Test GmbH
        Bruttobetrag: 1.000,00 €
        
        § 1 Vertragsgegenstand
        Laufzeit: unbefristet
        """
        
        result = self.engine.categorize_document(mixed_content)
        
        # Should have lower confidence due to mixed signals
        assert result.confidence < 1.0
        assert len(result.suggested_categories) > 0
        
        # Both categories should appear in results
        all_categories = [result.primary_category] + [cat for cat, _ in result.suggested_categories]
        assert "Rechnung" in all_categories
        assert "Vertrag" in all_categories
    
    def test_suggested_categories_threshold(self):
        """Test that suggested categories meet minimum confidence threshold"""
        content = """
        RECHNUNG
        Rechnungsnummer: R-001
        Bruttobetrag: 1.000,00 €
        """
        
        result = self.engine.categorize_document(content)
        
        # All suggested categories should meet minimum threshold
        for category, confidence in result.suggested_categories:
            assert confidence >= 0.1
        
        # Should not have more than 3 suggestions
        assert len(result.suggested_categories) <= 3
    
    def test_very_ambiguous_document(self):
        """Test categorization of very ambiguous document"""
        ambiguous_content = """
        Sehr geehrte Damen und Herren,
        
        vielen Dank für Ihr Schreiben.
        
        Mit freundlichen Grüßen
        """
        
        result = self.engine.categorize_document(ambiguous_content)
        
        # Should return "Unbekannt" for very ambiguous content
        assert result.primary_category == "Unbekannt"
        assert result.confidence == 0.0
        assert result.suggested_categories == []
    
    def test_strong_signal_confidence_boost(self):
        """Test confidence boost for very strong signals"""
        strong_invoice_content = """
        RECHNUNG RECHNUNG RECHNUNG
        
        Rechnungsnummer: R-2024-001
        Rechnungsdatum: 15.03.2024
        Fälligkeitsdatum: 15.04.2024
        Rechnungsempfänger: Test
        Rechnungssteller: Firma GmbH
        
        Nettobetrag: 1.000,00 €
        MwSt. 19%: 190,00 €
        Bruttobetrag: 1.190,00 €
        
        Zahlbar bis: 15.04.2024
        """
        
        result = self.engine.categorize_document(strong_invoice_content)
        
        # Should have very high confidence for strong signals
        assert result.confidence > 0.8
        assert result.primary_category == "Rechnung"
    
    def test_edge_case_very_short_content(self):
        """Test categorization with very short content"""
        short_content = "Rechnung"
        
        result = self.engine.categorize_document(short_content)
        
        assert result.primary_category == "Rechnung"
        assert result.confidence > 0.0
    
    def test_edge_case_special_characters(self):
        """Test categorization with special characters and encoding"""
        special_content = """
        RËCHÑUNG mit Ümlauten
        
        Rechnungsnummer: R-2024-001
        Beträg: 1.000,00 €
        """
        
        result = self.engine.categorize_document(special_content)
        
        assert result.primary_category == "Rechnung"
        assert result.confidence > 0.0
    
    def test_edge_case_mixed_language(self):
        """Test categorization with mixed German/English content"""
        mixed_content = """
        INVOICE / RECHNUNG
        
        Invoice Number: R-2024-001
        Rechnungsnummer: R-2024-001
        Total Amount: 1.000,00 €
        Bruttobetrag: 1.000,00 €
        """
        
        result = self.engine.categorize_document(mixed_content)
        
        assert result.primary_category == "Rechnung"
        assert result.confidence > 0.0
    
    def test_edge_case_corrupted_text(self):
        """Test categorization with corrupted/garbled text"""
        corrupted_content = """
        R3CHNuNG
        
        R3chnung5numm3r: R-2024-001
        Brutto83tr4g: 1.000,00 €
        """
        
        result = self.engine.categorize_document(corrupted_content)
        
        # Should still detect some patterns despite corruption
        assert result.primary_category in ["Rechnung", "Unbekannt"]
    
    def test_confidence_score_consistency(self):
        """Test that confidence scores are consistent across multiple calls"""
        content = """
        RECHNUNG
        Rechnungsnummer: R-2024-001
        Bruttobetrag: 1.000,00 €
        """
        
        scores = []
        for _ in range(5):
            result = self.engine.categorize_document(content)
            scores.append(result.confidence)
        
        # All scores should be identical
        assert all(score == scores[0] for score in scores)
        assert scores[0] > 0.0