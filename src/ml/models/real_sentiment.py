"""
REAL Sentiment Analyzer using Pre-trained DistilBERT

This is an ACTUAL trained model with 66M parameters.
Uses Hugging Face transformers with transfer learning.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger('RealSentimentAnalyzer')

# Check if transformers is available
try:
    from transformers import pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("transformers not installed. Run: pip install transformers torch")


class RealSentimentAnalyzer:
    """
    Real sentiment analysis using pre-trained DistilBERT.

    Model: distilbert-base-uncased-finetuned-sst-2-english
    Parameters: 66 million
    Training: Stanford Sentiment Treebank (SST-2)
    """

    def __init__(self):
        self.model = None
        self.is_loaded = False

    def load(self) -> bool:
        """Load the pre-trained model."""
        if not TRANSFORMERS_AVAILABLE:
            logger.error("transformers library not available")
            return False

        try:
            logger.info("Loading DistilBERT sentiment model...")
            self.model = pipeline(
                'sentiment-analysis',
                model='distilbert-base-uncased-finetuned-sst-2-english'
            )
            self.is_loaded = True
            logger.info("Real sentiment model loaded (66M parameters)")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def analyze(self, text: str) -> Dict:
        """
        Analyze sentiment of text.

        Args:
            text: Input text to analyze

        Returns:
            Dict with sentiment analysis results
        """
        if not self.is_loaded or self.model is None:
            return {
                'error': 'Model not loaded',
                'sentiment': 'unknown',
                'confidence': 0
            }

        # Run inference
        result = self.model(text[:512])[0]  # Max 512 tokens

        label = result['label'].lower()
        score = result['score']

        # Determine if this is a damage report
        damage_keywords = ['damage', 'dent', 'hail', 'broken', 'destroyed',
                          'repair', 'insurance', 'claim', 'estimate', 'windshield']
        is_damage_report = any(kw in text.lower() for kw in damage_keywords)

        # Determine urgency
        urgent_keywords = ['now', 'right now', 'emergency', 'warning', 'alert',
                          'happening', 'currently', 'live', 'breaking']
        is_urgent = any(kw in text.lower() for kw in urgent_keywords)

        # Actionable if negative damage report
        actionable = is_damage_report and label == 'negative'

        return {
            'sentiment': label,
            'confidence': round(score * 100, 1),
            'is_damage_report': is_damage_report,
            'urgency': 'high' if is_urgent else ('medium' if is_damage_report else 'low'),
            'actionable': actionable,
            'model': 'distilbert-base-uncased-finetuned-sst-2-english',
            'model_type': 'REAL_PRETRAINED',
            'parameters': '66M'
        }


def test_real_sentiment():
    """Test the real sentiment analyzer."""
    print("Testing Real Sentiment Analyzer")
    print("=" * 60)

    analyzer = RealSentimentAnalyzer()
    if not analyzer.load():
        print("Failed to load model")
        return

    test_texts = [
        "My car got destroyed by hail! Need repair ASAP!",
        "Great job fixing my hail damage. Highly recommend!",
        "Storm warning: Large hail expected in the area.",
        "Insurance denied my claim. This is so frustrating.",
    ]

    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"  Sentiment: {result['sentiment']} ({result['confidence']}%)")
        print(f"  Damage Report: {result['is_damage_report']}")
        print(f"  Urgency: {result['urgency']}")
        print(f"  Actionable: {result['actionable']}")


if __name__ == '__main__':
    test_real_sentiment()
