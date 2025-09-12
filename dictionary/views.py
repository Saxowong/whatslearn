from django.shortcuts import render
from django.db.models import Q
from .models import DictionaryItem
import re

def dictionary_search(request):
    query = request.GET.get('word', '').strip()  # Get raw input
    results = []
    if query:
        # Remove punctuation and split into words
        clean_query = re.sub(r'[^\w\s]', '', query)  # Remove commas, periods, etc.
        words = [word.strip() for word in clean_query.split() if word.strip()]
        input_words = [(word, word.lower()) for word in words]  # Store (original, lowercase) pairs
        
        if words:
            # Build Q objects for case-insensitive lookup per word
            query_filter = Q()
            for _, lowercase_word in input_words:
                query_filter |= Q(word__iexact=lowercase_word)
            # Fetch matching entries
            db_results = DictionaryItem.objects.filter(query_filter).distinct()
            
            # Create a dictionary for quick lookup by lowercase word
            result_dict = {result.word.lower(): result for result in db_results}
            # Order results based on input word order
            results = []
            seen = set()  # Track seen lowercase words to avoid duplicates
            for original_word, lowercase_word in input_words:
                if lowercase_word not in seen and lowercase_word in result_dict:
                    entry = result_dict[lowercase_word]
                    results.append({
                        'input_word': original_word,  # Preserve input case
                        'db_word': entry.word,       # DB word (for reference)
                        'meaning': entry.meaning
                    })
                    seen.add(lowercase_word)
    
    return render(request, 'dictionary/dictionary.html', {'results': results, 'query': query})