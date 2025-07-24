"""Document categorization engine with rule-based pattern matching"""

import re
from typing import Dict, Any, List, Tuple
from ..models import CategoryResult


class CategorizationEngine:
    """Engine for categorizing documents based on content patterns"""
    
    def __init__(self):
        """Initialize the categorization engine with predefined patterns"""
        self.category_patterns = {
            'Rechnung': {
                'patterns': [
                    r'rechnung(?:snummer)?',
                    r'invoice(?:\s+number)?',
                    r'rechnungsdatum',
                    r'fälligkeitsdatum',
                    r'zahlbar\s+bis',
                    r'netto\s*betrag',
                    r'brutto\s*betrag',
                    r'mehrwertsteuer',
                    r'mwst\.?',
                    r'ust\.?\s*id',
                    r'steuer(?:nummer|nr\.?)',
                    r'lieferant(?:en)?',
                    r'rechnungsempfänger'
                ],
                'entity_patterns': {
                    'rechnungssteller': [
                        r'(?:von|from|rechnungssteller):\s*([^\n\r]+)',
                        r'([A-Z][^\n\r]*(?:GmbH|AG|KG|OHG|e\.K\.|UG))',
                        r'lieferant(?:en)?:\s*([^\n\r]+)'
                    ],
                    'rechnungsnummer': [
                        r'rechnungsnummer:\s*([A-Z0-9-]+)',
                        r'rechnung\s+nr\.?\s*([A-Z0-9-]+)',
                        r'rechnung\s+([A-Z0-9-]+)',
                        r'invoice(?:\s+number)?[:\s#-]*([A-Z0-9-]+)'
                    ],
                    'betrag': [
                        r'(?:gesamt|total|summe)[:\s]*([0-9.,]+)\s*€',
                        r'([0-9.,]+)\s*€\s*(?:gesamt|total)',
                        r'bruttobetrag[:\s]*([0-9.,]+)\s*€'
                    ]
                }
            },
            'Kontoauszug': {
                'patterns': [
                    r'kontoauszug',
                    r'bank\s*statement',
                    r'konto(?:nummer|nr\.?)',
                    r'iban',
                    r'bic',
                    r'saldo',
                    r'buchung(?:stag|sdatum)',
                    r'verwendungszweck',
                    r'empfänger',
                    r'überweisungsauftrag',
                    r'lastschrift',
                    r'gutschrift'
                ],
                'entity_patterns': {
                    'bank': [
                        r'([A-Z][^\n\r]*(?:Bank|Sparkasse|Volksbank|Raiffeisenbank)(?:\s+AG)?)',
                        r'((?:Sparkasse|Volksbank|Raiffeisenbank)[^\n\r]*)',
                        r'bank:\s*([^\n\r]+)'
                    ],
                    'kontonummer': [
                        r'konto(?:nummer|nr\.?)[:\s]*([0-9\s]+)',
                        r'iban[:\s]*([A-Z0-9\s]+)'
                    ],
                    'zeitraum': [
                        r'(?:vom|von)\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})\s*(?:bis|zum)\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})',
                        r'auszug\s*([0-9]{1,2}/[0-9]{4})'
                    ]
                }
            },
            'Vertrag': {
                'patterns': [
                    r'vertrag',
                    r'contract',
                    r'vereinbarung',
                    r'agreement',
                    r'vertragspartner',
                    r'laufzeit',
                    r'kündigung(?:sfrist)?',
                    r'vertragsgegenstand',
                    r'§\s*[0-9]+',
                    r'artikel\s*[0-9]+',
                    r'unterschrift(?:en)?',
                    r'datum\s*der\s*unterzeichnung'
                ],
                'entity_patterns': {
                    'vertragspartner': [
                        r'vertragspartner[:\s]*([^\n\r]+)',
                        r'zwischen\s*([^\n\r]+?)\s*vertreten',
                        r'auftraggeber[:\s]*([^\n\r]+)'
                    ],
                    'vertragsart': [
                        r'([A-Za-z]+vertrag)',
                        r'vertrag\s*(?:über|für)\s*([^\n\r]+)',
                        r'vertragsgegenstand[:\s]*([^\n\r]+)'
                    ],
                    'laufzeit': [
                        r'laufzeit[:\s]*([^\n\r]+)',
                        r'(?:beginnt|gültig)\s*(?:am|vom|ab)\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})',
                        r'bis\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})'
                    ]
                }
            }
        }
    
    def categorize_document(self, content: str) -> CategoryResult:
        """
        Categorize a document based on its content using rule-based pattern matching
        
        Args:
            content: The text content of the document
            
        Returns:
            CategoryResult with primary category, confidence, entities, and suggestions
        """
        if not content or not content.strip():
            return CategoryResult(
                primary_category="Unbekannt",
                confidence=0.0,
                entities={},
                suggested_categories=[]
            )
        
        # Normalize content for pattern matching
        normalized_content = content.lower()
        
        # Calculate scores for each category
        category_scores = {}
        category_entities = {}
        
        for category, config in self.category_patterns.items():
            score = self._calculate_category_score(normalized_content, config['patterns'])
            entities = self._extract_entities(content, config['entity_patterns'])
            
            category_scores[category] = score
            category_entities[category] = entities
        
        # Find primary category and create suggestions
        if not category_scores or max(category_scores.values()) == 0:
            return CategoryResult(
                primary_category="Unbekannt",
                confidence=0.0,
                entities={},
                suggested_categories=[]
            )
        
        # Sort categories by score
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        primary_category = sorted_categories[0][0]
        primary_score = sorted_categories[0][1]
        
        # Enhanced confidence scoring
        confidence = self._calculate_enhanced_confidence(primary_score, sorted_categories)
        
        # Create suggested categories with improved scoring
        suggested_categories = self._create_suggested_categories(sorted_categories)
        
        return CategoryResult(
            primary_category=primary_category,
            confidence=confidence,
            entities=category_entities[primary_category],
            suggested_categories=suggested_categories
        )
    
    def _calculate_category_score(self, content: str, patterns: List[str]) -> float:
        """Calculate score for a category based on pattern matches"""
        score = 0.0
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Weight by number of matches and pattern specificity
                pattern_score = len(matches) * (1.0 + len(pattern) / 100.0)
                score += pattern_score
        
        return score
    
    def _extract_entities(self, content: str, entity_patterns: Dict[str, List[str]]) -> Dict[str, Any]:
        """Extract entities from content using regex patterns"""
        entities = {}
        
        for entity_type, patterns in entity_patterns.items():
            entity_values = []
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Handle tuple matches (groups) vs single matches
                    if isinstance(matches[0], tuple):
                        entity_values.extend([match for group in matches for match in group if match.strip()])
                    else:
                        entity_values.extend([match.strip() for match in matches if match.strip()])
            
            if entity_values:
                # Remove duplicates while preserving order
                unique_values = []
                seen = set()
                for value in entity_values:
                    if value not in seen:
                        unique_values.append(value)
                        seen.add(value)
                
                # Always return the first (most relevant) match for consistency
                entities[entity_type] = unique_values[0]
        
        return entities
    
    def _calculate_enhanced_confidence(self, primary_score: float, sorted_categories: List[Tuple[str, float]]) -> float:
        """Calculate enhanced confidence score based on primary score and competition"""
        if primary_score == 0:
            return 0.0
        
        # Base confidence from primary score
        base_confidence = min(primary_score / 10.0, 1.0)
        
        # Adjust confidence based on competition from other categories
        if len(sorted_categories) > 1:
            second_score = sorted_categories[1][1]
            if second_score > 0:
                # Reduce confidence if there's strong competition
                competition_factor = 1.0 - (second_score / (primary_score + second_score))
                base_confidence *= competition_factor
        
        # Boost confidence for very strong signals
        if primary_score > 15:  # Strong signal threshold
            base_confidence = min(base_confidence * 1.2, 1.0)
        
        return base_confidence
    
    def _create_suggested_categories(self, sorted_categories: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
        """Create suggested categories with confidence thresholds"""
        suggested_categories = []
        
        for cat, score in sorted_categories[1:]:  # Skip primary category
            if score > 0:
                confidence = min(score / 10.0, 1.0)
                # Only suggest categories with reasonable confidence
                if confidence >= 0.1:  # Minimum threshold for suggestions
                    suggested_categories.append((cat, confidence))
        
        # Limit to top 3 suggestions
        return suggested_categories[:3]
    
    def get_confidence_score(self, content: str, category: str) -> float:
        """
        Get confidence score for a specific category
        
        Args:
            content: The text content of the document
            category: The category to calculate confidence for
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not content or not content.strip() or category not in self.category_patterns:
            return 0.0
        
        normalized_content = content.lower()
        patterns = self.category_patterns[category]['patterns']
        score = self._calculate_category_score(normalized_content, patterns)
        
        # Normalize confidence score (0-1 range)
        confidence = min(score / 10.0, 1.0)  # Assuming max ~10 pattern matches
        return confidence
    
    def categorize_document_with_override(self, content: str, manual_category: str = None) -> CategoryResult:
        """
        Categorize a document with optional manual category override
        
        Args:
            content: The text content of the document
            manual_category: Optional manual category to override automatic detection
            
        Returns:
            CategoryResult with primary category, confidence, entities, and suggestions
        """
        if manual_category and manual_category in self.category_patterns:
            # Use manual override
            entities = self.extract_entities(content, manual_category)
            confidence = self.get_confidence_score(content, manual_category)
            
            # Still provide automatic suggestions for comparison
            auto_result = self.categorize_document(content)
            suggested_categories = [(auto_result.primary_category, auto_result.confidence)]
            suggested_categories.extend(auto_result.suggested_categories)
            
            # Remove the manual category from suggestions if it appears
            suggested_categories = [
                (cat, conf) for cat, conf in suggested_categories 
                if cat != manual_category
            ]
            
            return CategoryResult(
                primary_category=manual_category,
                confidence=confidence,
                entities=entities,
                suggested_categories=suggested_categories
            )
        else:
            # Use automatic categorization
            return self.categorize_document(content)
    
    def extract_entities(self, content: str, category: str) -> Dict[str, Any]:
        """
        Extract entities for a specific category
        
        Args:
            content: The text content of the document
            category: The category to extract entities for
            
        Returns:
            Dictionary of extracted entities
        """
        if category not in self.category_patterns:
            return {}
        
        entity_patterns = self.category_patterns[category]['entity_patterns']
        return self._extract_entities(content, entity_patterns)