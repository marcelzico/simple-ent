# quizzes/similarity_utils.py
"""
Ultra-Robust Text Similarity System
Handles 13+ problematic scenarios for educational answer comparison
"""

import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import SequenceMatcher
import re
from typing import Dict, List, Tuple, Set, Optional
from collections import Counter
from itertools import combinations
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextSimilarity:
    def __init__(self, debug_mode: bool = False):
        """
        Initialize the similarity analyzer with comprehensive normalization
        
        Args:
            debug_mode: If True, logs detailed processing steps
        """
        self.debug_mode = debug_mode
        
        # Load French model (works completely offline)
        try:
            self.nlp = spacy.load("fr_core_news_lg")
            if debug_mode:
                logger.info("✓ spaCy model loaded successfully")
        except OSError:
            logger.error("❌ Modèle fr_core_news_lg non trouvé. Utilisez: python -m spacy download fr_core_news_lg")
            self.nlp = None
        
        # Initialize normalization dictionaries
        self._init_synonym_dict()
        self._init_abbreviation_dict()
        self._init_expression_dict()
        self._init_regional_dict()
    
    def _init_synonym_dict(self):
        """Initialize French synonym dictionary"""
        self.synonym_dict = {
            'voiture': {'automobile', 'véhicule', 'auto', 'char'},
            'rapidement': {'vite', 'prestement', 'vivement'},
            'lentement': {'doucement', 'tranquillement'},
            'déplace': {'bouge', 'avance', 'se meut', 'se déplace'},
            'commence': {'débute', 'entame', 'démarre', 'initie'},
            'finit': {'termine', 'achève', 'se conclut', 'complète'},
            'augmente': {'croît', 'monte', 's\'élève', 'progresse'},
            'diminue': {'décroît', 'baisse', 'descend', 'régresse'},
            'maison': {'habitation', 'demeure', 'logement', 'résidence'},
            'grand': {'large', 'vaste', 'immense', 'énorme'},
            'petit': {'minuscule', 'réduit', 'court'},
            'beau': {'joli', 'magnifique', 'splendide'},
            'important': {'essentiel', 'crucial', 'fondamental', 'capital'},
            'produire': {'générer', 'créer', 'fabriquer', 'élaborer'},
            'utiliser': {'employer', 'se servir', 'recourir'},
        }
    
    def _init_abbreviation_dict(self):
        """Initialize scientific abbreviations and acronyms"""
        self.abbreviation_dict = {
            r'\bCO2\b': 'dioxyde de carbone',
            r'\bH2O\b': 'eau',
            r'\bO2\b': 'oxygène',
            r'\bN2\b': 'azote',
            r'\bADN\b': 'acide désoxyribonucléique',
            r'\bARN\b': 'acide ribonucléique',
            r'\bATP\b': 'adénosine triphosphate',
            r'\bUE\b': 'union européenne',
            r'\bONU\b': 'organisation des nations unies',
            r'\bOMS\b': 'organisation mondiale de la santé',
            r'\bUSA\b': 'états-unis',
            r'\bUK\b': 'royaume-uni',
            # Units
            r'\bkm\b': 'kilomètre',
            r'\bcm\b': 'centimètre',
            r'\bmm\b': 'millimètre',
            r'\bkg\b': 'kilogramme',
            r'\bmg\b': 'milligramme',
            r'\bml\b': 'millilitre',
            r'\b°C\b': 'degrés celsius',
            r'\b°F\b': 'degrés fahrenheit',
        }
    
    def _init_expression_dict(self):
        """Initialize idiomatic expressions"""
        self.expression_dict = {
            r'ça a empiré': 'situation détériorée',
            r'ça va mieux': 'situation améliorée',
            r'ça marche': 'ça fonctionne',
            r'en d\'autres termes': 'c\'est-à-dire',
            r'par conséquent': 'donc',
            r'de ce fait': 'donc',
            r'ainsi': 'donc',
            r'c\'est pour cette raison': 'donc',
            r'dès lors': 'donc',
            r'en effet': 'effectivement',
            r'en réalité': 'effectivement',
        }
    
    def _init_regional_dict(self):
        """Initialize regional vocabulary variations"""
        self.regional_dict = {
            'soccer': 'football',
            'char': 'voiture',
            'gsm': 'téléphone portable',
            'natel': 'téléphone portable',
            'septante': 'soixante-dix',
            'nonante': 'quatre-vingt-dix',
            'huitante': 'quatre-vingt',
            'déjeuner': 'petit-déjeuner',
            'dîner': 'déjeuner',
            'souper': 'dîner',
        }
    
    # ========== NORMALIZATION METHODS (Solutions 1-13) ==========
    
    def expand_with_synonyms(self, word: str) -> Set[str]:
        """Solution 1: Expand word with synonyms"""
        synonyms = {word}
        word_lower = word.lower()
        
        if word_lower in self.synonym_dict:
            synonyms.update(self.synonym_dict[word_lower])
        
        # Also check reverse mappings
        for key, values in self.synonym_dict.items():
            if word_lower in values:
                synonyms.add(key)
                synonyms.update(values)
        
        return synonyms
    
    def normalize_abbreviations(self, text: str) -> str:
        """Solution 2: Normalize scientific abbreviations"""
        normalized = text
        
        for pattern, replacement in self.abbreviation_dict.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        if self.debug_mode and normalized != text:
            logger.info(f"Abbreviations normalized: {text[:50]}... → {normalized[:50]}...")
        
        return normalized
    
    def normalize_numbers_and_units(self, text: str) -> str:
        """Solution 3: Normalize numbers and units"""
        # Convert word numbers to digits
        word_to_num = {
            'zéro': '0', 'un': '1', 'une': '1', 'deux': '2', 'trois': '3',
            'quatre': '4', 'cinq': '5', 'six': '6', 'sept': '7',
            'huit': '8', 'neuf': '9', 'dix': '10', 'onze': '11', 'douze': '12',
            'vingt': '20', 'trente': '30', 'quarante': '40', 'cinquante': '50',
            'soixante': '60', 'cent': '100', 'mille': '1000'
        }
        
        normalized = text
        for word, num in word_to_num.items():
            normalized = re.sub(rf'\b{word}\b', num, normalized, flags=re.IGNORECASE)
        
        # Normalize decimal separators
        normalized = re.sub(r'(\d+),(\d+)', r'\1.\2', normalized)  # 3,14 → 3.14
        
        return normalized
    
    def extract_semantic_core(self, text: str) -> Dict:
        """Solution 4: Extract core semantic elements (active/passive independent)"""
        if not self.nlp:
            return {'agents': [], 'actions': [], 'patients': []}
        
        doc = self.nlp(text)
        core = {
            'agents': [],
            'actions': [],
            'patients': []
        }
        
        for token in doc:
            if token.dep_ in ['nsubj', 'nsubjpass']:
                core['agents'].append(token.lemma_.lower())
            elif token.pos_ == 'VERB' and not token.is_stop:
                core['actions'].append(token.lemma_.lower())
            elif token.dep_ in ['dobj', 'obj', 'pobj', 'attr']:
                core['patients'].append(token.lemma_.lower())
        
        return core
    
    def compare_semantic_cores(self, core1: Dict, core2: Dict) -> float:
        """Compare semantic cores (voice-independent)"""
        all1 = set(core1['agents'] + core1['actions'] + core1['patients'])
        all2 = set(core2['agents'] + core2['actions'] + core2['patients'])
        
        if not all2:
            return 0.0
        
        # Expand with synonyms for better matching
        expanded1 = set()
        for word in all1:
            expanded1.update(self.expand_with_synonyms(word))
        
        expanded2 = set()
        for word in all2:
            expanded2.update(self.expand_with_synonyms(word))
        
        overlap = len(expanded1.intersection(expanded2)) / len(expanded2)
        return round(overlap * 100, 2)
    
    def normalize_expressions(self, text: str) -> str:
        """Solution 5: Normalize idiomatic expressions"""
        normalized = text
        
        for pattern, replacement in self.expression_dict.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def calculate_completeness_penalty(self, student_answer: str, model_answer: str) -> float:
        """Solution 6: Penalize incomplete answers"""
        model_concepts = self.extract_key_concepts(model_answer)
        student_concepts = self.extract_key_concepts(student_answer)
        
        if not model_concepts:
            return 1.0
        
        # Expand with synonyms
        student_expanded = set()
        for concept in student_concepts:
            student_expanded.update(self.expand_with_synonyms(concept))
        
        model_expanded = set()
        for concept in model_concepts:
            model_expanded.update(self.expand_with_synonyms(concept))
        
        found = len([c for c in model_expanded if c in student_expanded])
        completeness = found / len(model_concepts)
        
        # Progressive penalty
        if completeness < 0.3:
            return 0.4
        elif completeness < 0.5:
            return 0.6
        elif completeness < 0.7:
            return 0.8
        else:
            return 1.0
    
    def filter_relevant_content(self, student_answer: str, model_answer: str) -> str:
        """Solution 7: Filter out superfluous information"""
        if not self.nlp:
            return student_answer
        
        model_concepts = set(self.extract_key_concepts(model_answer))
        
        # Expand model concepts with synonyms
        expanded_model = set()
        for concept in model_concepts:
            expanded_model.update(self.expand_with_synonyms(concept))
        
        doc = self.nlp(student_answer)
        relevant_sentences = []
        
        for sent in doc.sents:
            sent_concepts = set(self.extract_key_concepts(sent.text))
            expanded_sent = set()
            for concept in sent_concepts:
                expanded_sent.update(self.expand_with_synonyms(concept))
            
            # Keep sentence if it has at least one model concept
            if expanded_sent.intersection(expanded_model):
                relevant_sentences.append(sent.text)
        
        result = ' '.join(relevant_sentences) if relevant_sentences else student_answer
        
        if self.debug_mode and result != student_answer:
            logger.info(f"Filtered content: {len(student_answer)} → {len(result)} chars")
        
        return result
    
    def calculate_phonetic_similarity(self, word1: str, word2: str) -> float:
        """Solution 8: Calculate phonetic similarity for severe typos"""
        def phonetic_normalize(word: str) -> str:
            word = word.lower()
            # French phonetic rules
            word = word.replace('ph', 'f')
            word = word.replace('th', 't')
            word = word.replace('qu', 'k')
            word = word.replace('ch', 'sh')
            word = re.sub(r'[cç]', 'k', word)
            word = word.replace('z', 's')
            word = word.replace('x', 'ks')
            word = re.sub(r'[éèêë]', 'e', word)
            word = re.sub(r'[àâ]', 'a', word)
            word = re.sub(r'[îï]', 'i', word)
            word = re.sub(r'[ôö]', 'o', word)
            word = re.sub(r'[ùûü]', 'u', word)
            # Remove silent letters at end
            word = re.sub(r'[hxstz]$', '', word)
            
            return word
        
        norm1 = phonetic_normalize(word1)
        norm2 = phonetic_normalize(word2)
        
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        return similarity
    
    def enhanced_fuzzy_match(self, word1: str, word2: str, threshold: float = 0.75) -> float:
        """Enhanced fuzzy matching combining edit distance and phonetics"""
        # Regular edit distance
        edit_sim = SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
        
        # Phonetic similarity
        phon_sim = self.calculate_phonetic_similarity(word1, word2)
        
        # Combined score (take maximum)
        combined = max(edit_sim, phon_sim)
        
        return combined if combined >= threshold else 0.0
    
    def detect_and_resolve_double_negation(self, text: str) -> Tuple[bool, str]:
        """Solution 9: Detect and resolve double negations"""
        # Common double negation patterns in French
        patterns = [
            (r'n[e\']?\s*\w+\s*pas\s+impossible', 'possible'),
            (r'n[e\']?\s*\w+\s*pas\s+incorrect', 'correct'),
            (r'n[e\']?\s*\w+\s*pas\s+inutile', 'utile'),
            (r'n[e\']?\s*\w+\s*pas\s+faux', 'vrai'),
            (r'pas\s+impossible', 'possible'),
            (r'pas\s+incorrect', 'correct'),
            (r'pas\s+faux', 'vrai'),
        ]
        
        normalized = text
        has_double_neg = False
        
        for pattern, replacement in patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
                has_double_neg = True
                if self.debug_mode:
                    logger.info(f"Double negation resolved: {pattern} → {replacement}")
        
        return has_double_neg, normalized
    
    def normalize_list_format(self, text: str) -> str:
        """Solution 10: Normalize different list formats"""
        normalized = text
        
        # Remove list markers
        normalized = re.sub(r'\d+[\)\.:\-]\s*', ' ', normalized)
        normalized = re.sub(r'[•\-\*○●]\s*', ' ', normalized)
        normalized = re.sub(r'[a-z][\)\.]\s*', ' ', normalized, flags=re.IGNORECASE)
        
        # Remove common list introducers
        introducers = [
            r'il y a \d+ (?:types?|sortes?|catégories?|éléments?):?',
            r'les? (?:types?|sortes?|catégories?|éléments?) (?:sont|comprennent):?',
            r'on distingue:?',
            r'voici:?',
            r'ce sont:?',
            r'notamment:?',
            r'à savoir:?',
        ]
        
        for pattern in introducers:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
        
        # Normalize separators
        normalized = re.sub(r'[;,]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.strip()
    
    def separate_core_from_examples(self, text: str) -> Tuple[str, List[str]]:
        """Solution 11: Separate core answer from examples"""
        example_patterns = [
            r'((?:,\s*)?(?:comme|par exemple|tel(?:s)? que|notamment)\s+[^\.;]+)',
            r'(\s*exemples?\s*:?\s*[^\.;]+)',
            r'(\s*(?:dont|incluant|y compris)\s+[^\.;]+)',
        ]
        
        core_text = text
        examples = []
        
        for pattern in example_patterns:
            matches = re.findall(pattern, core_text, re.IGNORECASE)
            examples.extend(matches)
            core_text = re.sub(pattern, '', core_text, flags=re.IGNORECASE)
        
        core_text = re.sub(r'\s+', ' ', core_text).strip()
        
        if self.debug_mode and examples:
            logger.info(f"Separated {len(examples)} example(s) from core answer")
        
        return core_text, examples
    
    def normalize_regional_terms(self, text: str) -> str:
        """Solution 12: Normalize regional vocabulary differences"""
        normalized = text
        
        for regional, standard in self.regional_dict.items():
            normalized = re.sub(rf'\b{regional}\b', standard, normalized, flags=re.IGNORECASE)
        
        return normalized
    
    def normalize_mathematical_expressions(self, text: str) -> str:
        """Solution 13: Normalize mathematical expressions (commutative operations)"""
        # Pattern for simple operations
        math_pattern = r'(\d+(?:\.\d+)?)\s*([+*/×÷])\s*(\d+(?:\.\d+)?)\s*=\s*(\d+(?:\.\d+)?)'
        
        def normalize_commutative(match):
            num1, op, num2, result = match.groups()
            
            # For commutative operations, sort operands
            if op in ['+', '*', '×']:
                nums = sorted([float(num1), float(num2)])
                # Convert back to original format
                if '.' not in num1 and '.' not in num2:
                    return f"{int(nums[0])} {op} {int(nums[1])} = {result}"
                else:
                    return f"{nums[0]} {op} {nums[1]} = {result}"
            
            return match.group(0)
        
        normalized = re.sub(math_pattern, normalize_commutative, text)
        
        # Normalize multiplication symbols
        normalized = normalized.replace('×', '*').replace('÷', '/')
        
        return normalized
    
    def apply_all_normalizations(self, text: str) -> str:
        """Apply ALL normalization methods in sequence"""
        if not text:
            return ""
        
        original = text
        
        # Step 1: Regional terms
        text = self.normalize_regional_terms(text)
        
        # Step 2: Abbreviations
        text = self.normalize_abbreviations(text)
        
        # Step 3: Numbers and units
        text = self.normalize_numbers_and_units(text)
        
        # Step 4: List formats
        text = self.normalize_list_format(text)
        
        # Step 5: Expressions
        text = self.normalize_expressions(text)
        
        # Step 6: Mathematical expressions
        text = self.normalize_mathematical_expressions(text)
        
        # Step 7: Double negations
        _, text = self.detect_and_resolve_double_negation(text)
        
        if self.debug_mode and text != original:
            logger.info(f"Full normalization: {original[:50]}... → {text[:50]}...")
        
        return text
    
    # ========== EXISTING METHODS (Enhanced) ==========
    
    def preprocess_text(self, text: str, use_lemmatization: bool = True, keep_numbers: bool = True) -> str:
        """Enhanced preprocessing with all normalizations"""
        if not text or not isinstance(text, str):
            return ""
        
        # Apply all normalizations first
        text = self.apply_all_normalizations(text)
        
        if not self.nlp:
            return text.lower().strip()
        
        # Convert to lowercase and clean whitespace
        text = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Process with spaCy
        doc = self.nlp(text)
        
        # Extract tokens
        processed_tokens = []
        for token in doc:
            if token.is_stop or token.is_punct or token.is_space:
                continue
            
            if keep_numbers and (token.like_num or token.is_digit):
                processed_tokens.append(token.text)
                continue
            
            if token.is_alpha and len(token.text) > 1:
                if use_lemmatization and token.lemma_.strip():
                    processed_tokens.append(token.lemma_)
                else:
                    processed_tokens.append(token.text)
        
        return ' '.join(processed_tokens)
    
    def extract_key_concepts(self, text: str) -> List[str]:
        """Extract important concepts"""
        if not self.nlp or not text:
            return []
        
        # Normalize first
        text = self.apply_all_normalizations(text)
        
        doc = self.nlp(text)
        key_concepts = []
        
        for token in doc:
            if token.pos_ in ['NOUN', 'PROPN', 'VERB', 'ADJ', 'NUM'] and not token.is_stop:
                if token.lemma_.strip():
                    key_concepts.append(token.lemma_.lower())
        
        return key_concepts
    
    def extract_semantic_triplets(self, text: str) -> Set[Tuple[str, str, str]]:
        """Extract semantic triplets (ORDER-INDEPENDENT)"""
        if not self.nlp or not text:
            return set()
        
        text = self.apply_all_normalizations(text)
        doc = self.nlp(text)
        triplets = set()
        
        for token in doc:
            if token.pos_ == 'VERB':
                verb = token.lemma_
                subject = None
                obj = None
                
                for child in token.children:
                    if child.dep_ in ['nsubj', 'nsubjpass']:
                        subject = child.lemma_
                    elif child.dep_ in ['dobj', 'obj', 'iobj', 'attr']:
                        obj = child.lemma_
                
                if subject and obj:
                    triplets.add((subject, verb, obj))
                elif subject:
                    triplets.add((subject, verb, '_'))
                elif obj:
                    triplets.add(('_', verb, obj))
        
        return triplets
    
    def extract_semantic_pairs(self, text: str) -> Set[Tuple[str, str]]:
        """Extract semantic word pairs (ORDER-INDEPENDENT)"""
        concepts = self.extract_key_concepts(text)
        pairs = set()
        
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:i+4]:
                pair = tuple(sorted([c1, c2]))
                pairs.add(pair)
        
        return pairs
    
    def calculate_concept_coverage(self, student_answer: str, model_answer: str) -> float:
        """Calculate concept coverage with synonym expansion"""
        student_concepts = set(self.extract_key_concepts(student_answer))
        model_concepts = set(self.extract_key_concepts(model_answer))
        
        if not model_concepts:
            return 100.0
        
        # Expand with synonyms
        student_expanded = set()
        for concept in student_concepts:
            student_expanded.update(self.expand_with_synonyms(concept))
        
        model_expanded = set()
        for concept in model_concepts:
            model_expanded.update(self.expand_with_synonyms(concept))
        
        covered = student_expanded.intersection(model_expanded)
        coverage = len(covered) / len(model_concepts)
        
        return round(coverage * 100, 2)
    
    def calculate_semantic_structure_similarity(self, student_answer: str, model_answer: str) -> float:
        """Calculate similarity based on semantic relationships"""
        student_triplets = self.extract_semantic_triplets(student_answer)
        model_triplets = self.extract_semantic_triplets(model_answer)
        
        if not model_triplets:
            return 0.0
        
        common_triplets = student_triplets.intersection(model_triplets)
        
        precision = len(common_triplets) / len(student_triplets) if student_triplets else 0
        recall = len(common_triplets) / len(model_triplets) if model_triplets else 0
        
        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0
        
        return round(f1 * 100, 2)
    
    def calculate_bag_of_concepts_similarity(self, student_answer: str, model_answer: str) -> float:
        """Pure bag-of-words approach (ORDER-INDEPENDENT)"""
        student_concepts = self.extract_key_concepts(student_answer)
        model_concepts = self.extract_key_concepts(model_answer)
        
        if not student_concepts or not model_concepts:
            return 0.0
        
        student_freq = Counter(student_concepts)
        model_freq = Counter(model_concepts)
        
        all_concepts = set(student_freq.keys()) | set(model_freq.keys())
        
        vec1 = np.array([student_freq.get(c, 0) for c in all_concepts])
        vec2 = np.array([model_freq.get(c, 0) for c in all_concepts])
        
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return round(similarity * 100, 2)
    
    def calculate_semantic_pair_overlap(self, student_answer: str, model_answer: str) -> float:
        """Calculate overlap of semantic word pairs"""
        student_pairs = self.extract_semantic_pairs(student_answer)
        model_pairs = self.extract_semantic_pairs(model_answer)
        
        if not model_pairs:
            return 0.0
        
        common_pairs = student_pairs.intersection(model_pairs)
        union = student_pairs.union(model_pairs)
        
        similarity = len(common_pairs) / len(union) if union else 0.0
        return round(similarity * 100, 2)
    
    def calculate_tfidf_similarity(self, student_answer: str, model_answer: str) -> float:
        """Enhanced TF-IDF with preprocessing"""
        text1 = self.preprocess_text(student_answer)
        text2 = self.preprocess_text(model_answer)
        
        if not text1.strip() or not text2.strip():
            return 0.0
        
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
            use_idf=True
        )
        
        try:
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return round(similarity * 100, 2)
        except:
            return 0.0
    
    def calculate_spacy_similarity(self, student_answer: str, model_answer: str) -> float:
        """spaCy similarity with normalization"""
        if not self.nlp:
            return 0.0
        
        # Normalize first
        text1 = self.apply_all_normalizations(student_answer)
        text2 = self.apply_all_normalizations(model_answer)
        
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        
        if doc1.vector_norm == 0 or doc2.vector_norm == 0:
            return 0.0
        
        similarity = doc1.similarity(doc2)
        return round(similarity * 100, 2)
    
    def calculate_embedding_similarity(self, student_answer: str, model_answer: str) -> float:
        """Weighted embedding similarity"""
        if not self.nlp:
            return 0.0
        
        text1 = self.apply_all_normalizations(student_answer)
        text2 = self.apply_all_normalizations(model_answer)
        
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        
        def get_weighted_vector(doc):
            vectors = []
            weights = []
            
            for token in doc:
                if not token.is_stop and not token.is_punct and token.has_vector:
                    vectors.append(token.vector)
                    weight = 2.0 if token.pos_ in ['NOUN', 'PROPN', 'VERB'] else 1.0
                    weights.append(weight)
            
            if not vectors:
                return None
            
            vectors = np.array(vectors)
            weights = np.array(weights).reshape(-1, 1)
            weighted_vec = np.average(vectors, axis=0, weights=weights.flatten())
            return weighted_vec
        
        vec1 = get_weighted_vector(doc1)
        vec2 = get_weighted_vector(doc2)
        
        if vec1 is None or vec2 is None:
            return 0.0
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return round(similarity * 100, 2)
    
    def calculate_jaccard_similarity(self, student_answer: str, model_answer: str) -> float:
        """Jaccard similarity (ORDER-INDEPENDENT)"""
        text1 = set(self.preprocess_text(student_answer).split())
        text2 = set(self.preprocess_text(model_answer).split())
        
        if not text1 or not text2:
            return 0.0
        
        intersection = len(text1.intersection(text2))
        union = len(text1.union(text2))
        similarity = intersection / union if union > 0 else 0.0
        return round(similarity * 100, 2)
    
    def calculate_fuzzy_word_overlap(self, student_answer: str, model_answer: str) -> float:
        """Enhanced fuzzy matching with phonetics"""
        words1 = self.preprocess_text(student_answer).split()
        words2 = self.preprocess_text(model_answer).split()
        
        if not words1 or not words2:
            return 0.0
        
        matched_count = 0
        matched_model_words = set()
        
        for w1 in words1:
            best_match = 0
            best_w2 = None
            
            for w2 in words2:
                if w2 not in matched_model_words:
                    # Use enhanced fuzzy matching
                    similarity = self.enhanced_fuzzy_match(w1, w2, threshold=0.75)
                    if similarity > best_match:
                        best_match = similarity
                        best_w2 = w2
            
            if best_match > 0 and best_w2:
                matched_count += 1
                matched_model_words.add(best_w2)
        
        overlap = matched_count / len(words2)
        return round(overlap * 100, 2)
    
    def detect_negation_mismatch(self, student_answer: str, model_answer: str) -> bool:
        """Detect negation mismatches (considering double negations)"""
        if not self.nlp:
            return False
        
        # Resolve double negations first
        _, student_normalized = self.detect_and_resolve_double_negation(student_answer)
        _, model_normalized = self.detect_and_resolve_double_negation(model_answer)
        
        negation_words = {'ne', 'pas', 'non', 'jamais', 'rien', 'aucun', 'sans', 'ni'}
        
        doc1 = self.nlp(student_normalized.lower())
        doc2 = self.nlp(model_normalized.lower())
        
        neg_count1 = sum(1 for token in doc1 if token.text in negation_words)
        neg_count2 = sum(1 for token in doc2 if token.text in negation_words)
        
        if neg_count1 == 0 and neg_count2 == 0:
            return False
        
        if neg_count1 > 0 and neg_count2 > 0:
            return False
        
        return abs(neg_count1 - neg_count2) >= 2
    
    def calculate_length_penalty(self, student_answer: str, model_answer: str) -> float:
        """More lenient length penalty"""
        len1 = len(self.preprocess_text(student_answer).split())
        len2 = len(self.preprocess_text(model_answer).split())
        
        if len2 == 0:
            return 1.0
        
        ratio = len1 / len2
        
        if 0.4 <= ratio <= 2.0:
            penalty = 1.0
        elif ratio < 0.2:
            penalty = 0.5
        elif ratio < 0.4:
            penalty = 0.75
        elif ratio > 3.0:
            penalty = 0.7
        elif ratio > 2.0:
            penalty = 0.85
        else:
            penalty = 1.0
        
        return penalty
    
    def calculate_semantic_similarity(self, student_answer: str, model_answer: str) -> float:
        """
        MASTER SIMILARITY METHOD
        Combines all 13 solutions for ultra-robust comparison
        """
        processed1 = self.preprocess_text(student_answer)
        processed2 = self.preprocess_text(model_answer)
        
        if not processed1.strip() or not processed2.strip():
            return 0.0
        
        # Filter relevant content (Solution 7)
        filtered_student = self.filter_relevant_content(student_answer, model_answer)
        
        # Separate core from examples (Solution 11)
        student_core, _ = self.separate_core_from_examples(filtered_student)
        model_core, _ = self.separate_core_from_examples(model_answer)
        
        # Calculate ORDER-INDEPENDENT metrics
        bag_of_concepts = self.calculate_bag_of_concepts_similarity(student_core, model_core) / 100
        semantic_structure = self.calculate_semantic_structure_similarity(student_core, model_core) / 100
        semantic_pairs = self.calculate_semantic_pair_overlap(student_core, model_core) / 100
        
        # Active/Passive independent (Solution 4)
        core1 = self.extract_semantic_core(student_core)
        core2 = self.extract_semantic_core(model_core)
        voice_independent = self.compare_semantic_cores(core1, core2) / 100
        
        # Traditional metrics (enhanced with normalizations)
        tfidf_score = self.calculate_tfidf_similarity(student_core, model_core) / 100
        spacy_score = self.calculate_spacy_similarity(student_core, model_core) / 100
        embedding_score = self.calculate_embedding_similarity(student_core, model_core) / 100
        jaccard_score = self.calculate_jaccard_similarity(student_core, model_core) / 100
        fuzzy_score = self.calculate_fuzzy_word_overlap(student_core, model_core) / 100
        
        # Concept coverage with synonyms (Solution 1)
        concept_coverage = self.calculate_concept_coverage(student_core, model_core) / 100
        
        # PENALTIES
        length_penalty = self.calculate_length_penalty(student_answer, model_answer)
        completeness_penalty = self.calculate_completeness_penalty(student_answer, model_answer)
        
        negation_mismatch = self.detect_negation_mismatch(student_answer, model_answer)
        negation_penalty = 0.75 if negation_mismatch else 1.0
        
        # WEIGHTED COMBINATION (optimized for robustness)
        base_score = (
            bag_of_concepts * 0.18 +
            semantic_structure * 0.12 +
            semantic_pairs * 0.12 +
            voice_independent * 0.15 +
            embedding_score * 0.15 +
            spacy_score * 0.10 +
            concept_coverage * 0.08 +
            fuzzy_score * 0.05 +
            jaccard_score * 0.03 +
            tfidf_score * 0.02
        )
        
        # Apply all penalties
        final_score = base_score * length_penalty * completeness_penalty * negation_penalty
        
        return round(final_score * 100, 2)
    
    def calculate_similarity(self, student_answer: str, model_answer: str, method: str = 'auto') -> float:
        """
        Main entry point for similarity calculation
        
        Args:
            student_answer: Student's response
            model_answer: Model/correct answer
            method: 'auto' (recommended) or specific method name
        """
        if method == 'auto':
            return self.calculate_semantic_similarity(student_answer, model_answer)
        elif method == 'semantic':
            return self.calculate_semantic_similarity(student_answer, model_answer)
        elif method == 'bag_of_concepts':
            return self.calculate_bag_of_concepts_similarity(student_answer, model_answer)
        elif method == 'structure':
            return self.calculate_semantic_structure_similarity(student_answer, model_answer)
        elif method == 'pairs':
            return self.calculate_semantic_pair_overlap(student_answer, model_answer)
        elif method == 'voice_independent':
            core1 = self.extract_semantic_core(student_answer)
            core2 = self.extract_semantic_core(model_answer)
            return self.compare_semantic_cores(core1, core2)
        else:
            return self.calculate_semantic_similarity(student_answer, model_answer)
    
    def get_detailed_analysis(self, student_answer: str, model_answer: str) -> Dict:
        """
        Comprehensive analysis with ALL metrics and solutions applied
        """
        # Apply normalizations
        normalized_student = self.apply_all_normalizations(student_answer)
        normalized_model = self.apply_all_normalizations(model_answer)
        
        # Separate core from examples
        student_core, student_examples = self.separate_core_from_examples(student_answer)
        model_core, model_examples = self.separate_core_from_examples(model_answer)
        
        # Extract semantic elements
        student_sem_core = self.extract_semantic_core(student_core)
        model_sem_core = self.extract_semantic_core(model_core)
        
        analysis = {
            'overall_similarity': self.calculate_semantic_similarity(student_answer, model_answer),
            
            # ORDER-INDEPENDENT metrics
            'bag_of_concepts_similarity': self.calculate_bag_of_concepts_similarity(student_answer, model_answer),
            'semantic_structure_similarity': self.calculate_semantic_structure_similarity(student_answer, model_answer),
            'semantic_pair_overlap': self.calculate_semantic_pair_overlap(student_answer, model_answer),
            'voice_independent_similarity': self.compare_semantic_cores(student_sem_core, model_sem_core),
            
            # Traditional metrics
            'tfidf_similarity': self.calculate_tfidf_similarity(student_answer, model_answer),
            'spacy_similarity': self.calculate_spacy_similarity(student_answer, model_answer),
            'embedding_similarity': self.calculate_embedding_similarity(student_answer, model_answer),
            'jaccard_similarity': self.calculate_jaccard_similarity(student_answer, model_answer),
            'fuzzy_word_overlap': self.calculate_fuzzy_word_overlap(student_answer, model_answer),
            'concept_coverage': self.calculate_concept_coverage(student_answer, model_answer),
            
            # Penalties and flags
            'length_penalty': round(self.calculate_length_penalty(student_answer, model_answer) * 100, 2),
            'completeness_penalty': round(self.calculate_completeness_penalty(student_answer, model_answer) * 100, 2),
            'has_negation_mismatch': self.detect_negation_mismatch(student_answer, model_answer),
            'has_double_negation': self.detect_and_resolve_double_negation(student_answer)[0],
            
            # Metadata
            'student_word_count': len(self.preprocess_text(student_answer).split()),
            'model_word_count': len(self.preprocess_text(model_answer).split()),
            'student_key_concepts': self.extract_key_concepts(student_answer)[:10],
            'model_key_concepts': self.extract_key_concepts(model_answer)[:10],
            'student_semantic_triplets': list(self.extract_semantic_triplets(student_answer))[:5],
            'model_semantic_triplets': list(self.extract_semantic_triplets(model_answer))[:5],
            'student_has_examples': bool(student_examples),
            'normalized_student': normalized_student[:100],
            'normalized_model': normalized_model[:100],
        }
        
        # Grading
        score = analysis['overall_similarity']
        if score >= 85:
            analysis['interpretation'] = 'Excellente réponse'
            analysis['grade'] = 'A'
        elif score >= 70:
            analysis['interpretation'] = 'Bonne réponse'
            analysis['grade'] = 'B'
        elif score >= 55:
            analysis['interpretation'] = 'Réponse acceptable'
            analysis['grade'] = 'C'
        elif score >= 40:
            analysis['interpretation'] = 'Réponse insuffisante'
            analysis['grade'] = 'D'
        else:
            analysis['interpretation'] = 'Réponse inadéquate'
            analysis['grade'] = 'F'
        
        # Detailed feedback
        feedback_points = []
        
        if analysis['completeness_penalty'] < 70:
            missing = set(analysis['model_key_concepts']) - set(analysis['student_key_concepts'])
            if missing:
                feedback_points.append(f"❌ Concepts manquants: {', '.join(list(missing)[:3])}")
        
        if analysis['concept_coverage'] >= 70:
            feedback_points.append("✓ Bonne couverture des concepts clés")
        
        if analysis['has_negation_mismatch']:
            feedback_points.append("⚠️ Contradiction potentielle avec la réponse modèle")
        
        if analysis['has_double_negation']:
            feedback_points.append("ℹ️ Double négation détectée et résolue")
        
        if analysis['voice_independent_similarity'] > 85:
            feedback_points.append("✓ Structure sémantique correcte (ordre indépendant)")
        
        if analysis['fuzzy_word_overlap'] > 70:
            feedback_points.append("✓ Bon vocabulaire (tolère les fautes mineures)")
        
        if analysis['student_has_examples']:
            feedback_points.append("✓ Exemples fournis")
        
        if analysis['length_penalty'] < 80:
            if analysis['student_word_count'] < analysis['model_word_count'] * 0.5:
                feedback_points.append("⚠️ Réponse trop courte")
            else:
                feedback_points.append("ℹ️ Réponse longue - vérifier pertinence")
        
        analysis['feedback_points'] = feedback_points
        
        return analysis

# Singleton instance
similarity_analyzer = TextSimilarity(debug_mode=False)


# ============= COMPREHENSIVE TESTS =============
if __name__ == '__main__':
    print("="*80)
    print("TESTS COMPLETS - 13 SCÉNARIOS PROBLÉMATIQUES")
    print("="*80)
    
    analyzer = TextSimilarity(debug_mode=True)
    
    # TEST 1: SYNONYMES
    print("\n📌 TEST 1: Synonymes")
    print("-" * 80)
    model = "La voiture se déplace rapidement"
    student = "L'automobile avance vite"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}% ({result['grade']})")
    print(f"Feedback: {', '.join(result['feedback_points'])}")
    
    # TEST 2: ABRÉVIATIONS
    print("\n📌 TEST 2: Abréviations scientifiques")
    print("-" * 80)
    model = "Le dioxyde de carbone et l'eau produisent du glucose"
    student = "Le CO2 et H2O produisent du glucose"
    score = analyzer.calculate_similarity(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {score}%")
    
    # TEST 3: NOMBRES
    print("\n📌 TEST 3: Nombres et unités")
    print("-" * 80)
    model = "La température est de cent degrés Celsius"
    student = "100°C"
    score = analyzer.calculate_similarity(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {score}%")
    
    # TEST 4: ACTIF/PASSIF
    print("\n📌 TEST 4: Voix active vs passive")
    print("-" * 80)
    model = "Le professeur explique la leçon"
    student = "La leçon est expliquée par le professeur"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}%")
    print(f"Voice-independent: {result['voice_independent_similarity']}%")
    
    # TEST 5: EXPRESSIONS
    print("\n📌 TEST 5: Expressions idiomatiques")
    print("-" * 80)
    model = "La situation s'est détériorée"
    student = "Ça a empiré"
    score = analyzer.calculate_similarity(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {score}%")
    
    # TEST 6: RÉPONSE PARTIELLE
    print("\n📌 TEST 6: Réponse partielle")
    print("-" * 80)
    model = "La photosynthèse produit du glucose et de l'oxygène"
    student = "La photosynthèse produit de l'oxygène"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}%")
    print(f"Complétude: {result['completeness_penalty']}%")
    
    # TEST 7: INFO SUPERFLUE
    print("\n📌 TEST 7: Informations superflues")
    print("-" * 80)
    model = "La capitale de la France est Paris"
    student = "La capitale de la France est Paris, une ville magnifique fondée par les Romains"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}%")
    
    # TEST 8: FAUTES GRAVES
    print("\n📌 TEST 8: Fautes d'orthographe graves")
    print("-" * 80)
    model = "La photosynthèse est importante"
    student = "La fotosinteze est importente"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}%")
    print(f"Fuzzy match: {result['fuzzy_word_overlap']}%")
    
    # TEST 9: DOUBLE NÉGATION
    print("\n📌 TEST 9: Double négation")
    print("-" * 80)
    model = "C'est possible"
    student = "Ce n'est pas impossible"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}%")
    print(f"Double négation: {result['has_double_negation']}")
    
    # TEST 10: FORMATS LISTES
    print("\n📌 TEST 10: Formats de listes différents")
    print("-" * 80)
    model = "Les types de roches: ignées, sédimentaires, métamorphiques"
    student = "Il y a 3 types: 1) ignées 2) sédimentaires 3) métamorphiques"
    score = analyzer.calculate_similarity(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {score}%")
    
    # TEST 11: AVEC EXEMPLES
    print("\n📌 TEST 11: Réponse avec exemples")
    print("-" * 80)
    model = "Les mammifères sont des animaux vertébrés"
    student = "Les mammifères sont des vertébrés, comme le chien, le chat"
    result = analyzer.get_detailed_analysis(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {result['overall_similarity']}%")
    print(f"A des exemples: {result['student_has_examples']}")
    
    # TEST 12: TERMES RÉGIONAUX
    print("\n📌 TEST 12: Termes régionaux")
    print("-" * 80)
    model = "Le football se joue avec 11 joueurs"
    student = "Le soccer se joue avec 11 joueurs"
    score = analyzer.calculate_similarity(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {score}%")
    
    # TEST 13: MATHS COMMUTATIVES
    print("\n📌 TEST 13: Opérations mathématiques commutatives")
    print("-" * 80)
    model = "2 + 3 = 5"
    student = "3 + 2 = 5"
    score = analyzer.calculate_similarity(student, model)
    print(f"Modèle: {model}")
    print(f"Étudiant: {student}")
    print(f"Score: {score}%")
    
    print("\n" + "="*80)
    print("TESTS TERMINÉS ✓")
    print("="*80)