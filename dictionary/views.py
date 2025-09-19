from django.shortcuts import render
from django.db.models import Q
from .models import DictionaryItem
import re

def dictionary_search(request):
    query = request.GET.get('word', '').strip()  # Get raw input
    results = []
    print(f"DEBUG - Input query: '{query}'")  # Debug: Log raw input
    
    if query:
        # Remove punctuation and split into words
        clean_query = re.sub(r'[^\w\s]', '', query)  # Remove commas, periods, etc.
        words = [word.strip() for word in clean_query.split() if word.strip()]
        input_words = [(word, word.lower()) for word in words if word.strip()]
        print(f"DEBUG - Cleaned query: '{clean_query}' | Words: {input_words}")  # Debug: Log processed input
        
        if input_words:
            if len(words) == 1:
                # Single-word query: Find up to 10 similar matches with __istartswith
                lowercase_word = input_words[0][1]
                db_results = DictionaryItem.objects.filter(
                    Q(word__iexact=lowercase_word) | Q(word__istartswith=lowercase_word)
                ).distinct()[:10]
                print(f"DEBUG - Single-word results: {[(r.word, r.meaning) for r in db_results]}")  # Debug
                results = [
                    {
                        'input_word': result.word,  # Use DB word for display
                        'db_word': result.word,
                        'meaning': result.meaning
                    } for result in db_results
                ]
            else:
                # Sentence query: Exact matches in input order
                query_filter = Q()
                for _, lowercase_word in input_words:
                    query_filter |= Q(word__iexact=lowercase_word)
                db_results = DictionaryItem.objects.filter(query_filter).distinct()
                print(f"DEBUG - Sentence db results: {[(r.word, r.meaning) for r in db_results]}")  # Debug
                
                # Order results by input word order
                result_dict = {result.word.lower(): result for result in db_results}
                seen = set()
                for original_word, lowercase_word in input_words:
                    if lowercase_word not in seen and lowercase_word in result_dict:
                        entry = result_dict[lowercase_word]
                        results.append({
                            'input_word': original_word,
                            'db_word': entry.word,
                            'meaning': entry.meaning
                        })
                        seen.add(lowercase_word)
                print(f"DEBUG - Sentence final results: {results}")  # Debug
    
    print(f"DEBUG - Passing to template: query='{query}', results count={len(results)}")  # Debug
    return render(request, 'dictionary/dictionary.html', {'results': results, 'query': query})