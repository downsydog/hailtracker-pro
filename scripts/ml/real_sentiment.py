"""
REAL Pre-trained Sentiment Analysis Model

This uses DistilBERT - a real transformer model with 66M parameters,
trained on the Stanford Sentiment Treebank dataset.

NO synthetic data. NO fake training. This is the real deal.
"""

import warnings
warnings.filterwarnings('ignore')

def main():
    print('Loading pre-trained sentiment model...')
    print('This is a REAL model with 66M parameters.')
    print()

    from transformers import pipeline

    # Load pre-trained model (downloads ~270MB on first run)
    sentiment = pipeline(
        'sentiment-analysis',
        model='distilbert-base-uncased-finetuned-sst-2-english'
    )

    print('Model loaded successfully!')
    print()
    print('=' * 70)
    print('TESTING REAL PRE-TRAINED MODEL ON HAIL-RELATED POSTS')
    print('=' * 70)
    print()

    test_posts = [
        'OMG huge hail in OKC right now! My car is getting destroyed!',
        'Just got an estimate for hail damage repair - $2500! Terrible.',
        'Great experience with ABC PDR. Fixed all the dents perfectly!',
        'Warning: Massive hail storm heading toward Dallas. Take cover!',
        'My insurance denied my hail damage claim. So frustrated!',
        'Finally got my car fixed after the storm. Looks brand new!',
        'This is the worst hail damage I have ever seen in my life.',
        'Thank you to the repair team for the quick turnaround!',
        'Hail size of golf balls reported. Stay safe everyone.',
        'Lost my windshield and have dents everywhere. Nightmare.',
    ]

    for post in test_posts:
        result = sentiment(post)[0]
        label = result['label']
        score = result['score']

        indicator = '[+]' if label == 'POSITIVE' else '[-]'
        display_post = post[:52] + '...' if len(post) > 55 else post
        print(f'{indicator} {label:8} ({score:5.1%}) | "{display_post}"')

    print()
    print('=' * 70)
    print('MODEL INFO:')
    print('  - Architecture: DistilBERT (66M parameters)')
    print('  - Training: Stanford Sentiment Treebank (SST-2)')
    print('  - This is TRANSFER LEARNING - real pre-trained weights')
    print('=' * 70)

    return sentiment


if __name__ == '__main__':
    model = main()
