from django.shortcuts import render
from django.db.models import Q
from .models import DictionaryItem
import re


def dictionary_search(request):
    query = request.GET.get("word", "").strip()
    results = []
    match_algorithm = None
    print(f"DEBUG - Input query: '{query}'")

    if query:
        # Remove punctuation and split into words
        clean_query = re.sub(r"[^\w\s]", "", query)
        words = [word.strip() for word in clean_query.split() if word.strip()]
        input_words = [(word, word.lower()) for word in words if word.strip()]
        print(f"DEBUG - Cleaned query: '{clean_query}' | Words: {input_words}")

        if input_words:
            if len(words) == 1:
                # Single-word query
                original_word = input_words[0][0]
                lowercase_word = input_words[0][1]

                # First try exact match (single word only)
                exact_match = DictionaryItem.objects.filter(
                    word__iexact=lowercase_word,
                    word__regex=r"^\w+$",  # Only single words (no spaces)
                ).first()

                if exact_match:
                    # Exact match found - get this word and 9 following single words alphabetically
                    match_algorithm = "exact match"
                    db_results = DictionaryItem.objects.filter(
                        word__gte=exact_match.word,
                        word__regex=r"^\w+$",  # Only single words
                    ).order_by("word")[:10]
                else:
                    # No exact match - use first 4 letters to find similar single words
                    match_algorithm = "similar words"

                    # Get the first 4 letters (or whatever is available)
                    search_prefix = (
                        lowercase_word[:4]
                        if len(lowercase_word) >= 4
                        else lowercase_word
                    )

                    # Find single words that start with the same prefix
                    db_results = DictionaryItem.objects.filter(
                        word__istartswith=search_prefix,
                        word__regex=r"^\w+$",  # Only single words (no spaces)
                    ).order_by("word")[:10]

                    # If we don't get enough results, try with a shorter prefix
                    if len(db_results) < 5 and len(search_prefix) > 2:
                        shorter_prefix = lowercase_word[:3]
                        more_results = DictionaryItem.objects.filter(
                            word__istartswith=shorter_prefix,
                            word__regex=r"^\w+$",  # Only single words
                        ).order_by("word")[:10]
                        # Combine results, removing duplicates
                        combined_results = list(db_results) + [
                            r for r in more_results if r not in db_results
                        ]
                        db_results = combined_results[:10]

                print(
                    f"DEBUG - Single-word results: {[(r.word, r.meaning) for r in db_results]}"
                )

                results = []
                for i, result in enumerate(db_results):
                    results.append(
                        {
                            "input_word": (
                                original_word if i == 0 and exact_match else None
                            ),
                            "db_word": result.word,
                            "meaning": result.meaning,
                        }
                    )

            else:
                # Sentence query: Exact matches in input order - also filter to single words only
                query_filter = Q()
                for _, lowercase_word in input_words:
                    query_filter |= Q(word__iexact=lowercase_word)

                # Only get single word matches
                db_results = DictionaryItem.objects.filter(
                    query_filter, word__regex=r"^\w+$"  # Only single words
                ).distinct()

                print(
                    f"DEBUG - Sentence db results: {[(r.word, r.meaning) for r in db_results]}"
                )

                # Order results by input word order
                result_dict = {result.word.lower(): result for result in db_results}
                seen = set()
                for original_word, lowercase_word in input_words:
                    if lowercase_word not in seen and lowercase_word in result_dict:
                        entry = result_dict[lowercase_word]
                        results.append(
                            {
                                "input_word": original_word,
                                "db_word": entry.word,
                                "meaning": entry.meaning,
                            }
                        )
                        seen.add(lowercase_word)
                print(f"DEBUG - Sentence final results: {results}")

    print(f"DEBUG - Passing to template: query='{query}', results count={len(results)}")
    return render(
        request,
        "dictionary/dictionary.html",
        {"results": results, "query": query, "match_algorithm": match_algorithm},
    )
