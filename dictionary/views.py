from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Subquery, OuterRef, Q
from django.utils import timezone
from .models import StudentWord, DictionaryItem
from user.models import Profile
import json, random, re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse


@login_required
def dictionary_search(request):
    query = request.GET.get("word", "").strip()
    results = []
    match_algorithm = None
    student_word_count = 0
    pending_revise_count = 0

    # Get the current user's profile and count their words
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            student_word_count = StudentWord.objects.filter(student=profile).count()
            # Count words where revise_at is not null and is before current time
            pending_revise_count = StudentWord.objects.filter(
                student=profile, revise_at__isnull=False, revise_at__lte=timezone.now()
            ).count()
        except Profile.DoesNotExist:
            student_word_count = 0
            pending_revise_count = 0
    else:
        student_word_count = 0
        pending_revise_count = 0

    print(f"DEBUG - Input query: '{query}'")
    print(f"DEBUG - Student word count: {student_word_count}")
    print(f"DEBUG - Pending revise count: {pending_revise_count}")

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
                    # Check if the current user already has this word
                    is_owned_by_student = False
                    if request.user.is_authenticated:
                        try:
                            profile = request.user.profile
                            is_owned_by_student = StudentWord.objects.filter(
                                student=profile, word=result.word
                            ).exists()
                        except Profile.DoesNotExist:
                            is_owned_by_student = False

                    results.append(
                        {
                            "input_word": (
                                original_word if i == 0 and exact_match else None
                            ),
                            "db_word": result.word,
                            "meaning": result.meaning,
                            "is_owned_by_student": is_owned_by_student,
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
                results = []
                for original_word, lowercase_word in input_words:
                    if lowercase_word not in seen and lowercase_word in result_dict:
                        entry = result_dict[lowercase_word]

                        # Check if the current user already has this word
                        is_owned_by_student = False
                        if request.user.is_authenticated:
                            try:
                                profile = request.user.profile
                                is_owned_by_student = StudentWord.objects.filter(
                                    student=profile, word=entry.word
                                ).exists()
                            except Profile.DoesNotExist:
                                is_owned_by_student = False

                        results.append(
                            {
                                "input_word": original_word,
                                "db_word": entry.word,
                                "meaning": entry.meaning,
                                "is_owned_by_student": is_owned_by_student,
                            }
                        )
                        seen.add(lowercase_word)
                print(f"DEBUG - Sentence final results: {results}")

    print(f"DEBUG - Passing to template: query='{query}', results count={len(results)}")
    return render(
        request,
        "dictionary/dictionary.html",
        {
            "results": results,
            "query": query,
            "match_algorithm": match_algorithm,
            "student_word_count": student_word_count,
            "pending_revise_count": pending_revise_count,
        },
    )


@csrf_exempt
@require_POST
def save_word(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Authentication required"})

    try:
        data = json.loads(request.body)
        word = data.get("word")
        action = data.get("action")  # 'add' or 'remove'

        if not word:
            return JsonResponse({"success": False, "error": "Word is required"})

        profile = request.user.profile
        dictionary_item = DictionaryItem.objects.filter(word=word).first()

        if not dictionary_item:
            return JsonResponse(
                {"success": False, "error": "Word not found in dictionary"}
            )

        if action == "add":
            # Create new StudentWord if it doesn't exist
            student_word, created = StudentWord.objects.get_or_create(
                student=profile,
                dictionary_item=dictionary_item,
                defaults={
                    "word": dictionary_item.word,
                    "meaning": dictionary_item.meaning,
                },
            )
            if created:
                return JsonResponse({"success": True, "action": "added"})
            else:
                return JsonResponse({"success": True, "action": "already_exists"})

        elif action == "remove":
            # Remove the StudentWord
            deleted_count, _ = StudentWord.objects.filter(
                student=profile, word=word
            ).delete()

            if deleted_count > 0:
                return JsonResponse({"success": True, "action": "removed"})
            else:
                return JsonResponse({"success": True, "action": "not_found"})

        else:
            return JsonResponse({"success": False, "error": "Invalid action"})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def dictionary_revision(request):
    user = request.user.profile
    # Get the count of words due for revision
    revision_items_count = StudentWord.objects.filter(
        student=user,
        revise_at__lte=timezone.now(),
        continue_revision=True,
    ).count()

    # Get items due for revision first
    due_items = (
        StudentWord.objects.filter(
            student=user,
            revise_at__lte=timezone.now(),
            continue_revision=True,
        )
        .values(
            "id",
            "word",
            "meaning",
            "successes",
            "is_master",
            "next_1",
            "next_2",
            "revise_at",
            "continue_revision",
        )
        .order_by("revise_at")
    )

    # If less than 10 due items, get additional items with fewest successes
    items = list(due_items)
    if len(items) < 10:
        remaining_count = 10 - len(items)
        additional_items = (
            StudentWord.objects.filter(
                student=user,
                continue_revision=True,
            )
            .exclude(id__in=[item["id"] for item in items])
            .values(
                "id",
                "word",
                "meaning",
                "successes",
                "is_master",
                "next_1",
                "next_2",
                "revise_at",
                "continue_revision",
            )
            .order_by("successes", "id")[:remaining_count]
        )
        items.extend(additional_items)

    # Prepare revision items with options
    revision_items = []
    all_meanings = list(
        StudentWord.objects.filter(student=user)
        .values_list("meaning", flat=True)
        .distinct()
    )

    for item in items:
        # Generate audio URL
        word_lower = item["word"].lower()
        first_letter = word_lower[0] if word_lower else ""
        audio_url = (
            f"/media/mp3/{first_letter}/{word_lower}.mp3"
            if first_letter and word_lower
            else None
        )

        # Generate multiple-choice options
        correct_answer = item["meaning"]
        options = [correct_answer]
        # Select up to 3 distractors from other words' meanings
        other_meanings = [m for m in all_meanings if m != correct_answer]
        distractors = (
            random.sample(other_meanings, min(3, len(other_meanings)))
            if other_meanings
            else []
        )
        options.extend(distractors)
        # Pad with generic options if needed
        while len(options) < 4:
            options.append(f"Option {len(options)}")
        random.shuffle(options)

        item_data = {
            "id": item["id"],
            "item_type": "mc",  # Treat as multiple-choice
            "word": item["word"],
            "meaning": item["meaning"],
            "successes": item["successes"],
            "is_master": item["is_master"],
            "next_1": item["next_1"],
            "next_2": item["next_2"],
            "revise_at": (item["revise_at"].isoformat() if item["revise_at"] else None),
            "continue_revision": item["continue_revision"],
            "options": options,
            "correct_answer": correct_answer,
            "correct_sequence_json": json.dumps([correct_answer]),
            "audio": audio_url,
            "audio_play": "start",
        }
        revision_items.append(item_data)

    context = {
        "revision_items": revision_items,
        "revision_items_count": revision_items_count,
        "student_word_count": StudentWord.objects.filter(student=user).count(),
    }
    return render(request, "dictionary/revision.html", context)


@csrf_exempt
@require_POST
@login_required
def dictionary_revision_submit(request):
    try:
        data = json.loads(request.POST.get("responses", "[]"))
        is_completed = request.POST.get("is_completed", "false").lower() == "true"

        if not data:
            return JsonResponse({"status": "error", "message": "No responses provided"})

        profile = request.user.profile
        updated_items = []

        for response in data:
            student_word_id = response.get("student_word_id")
            successes = response.get("successes")
            next_1 = response.get("next_1")
            next_2 = response.get("next_2")
            revise_at = response.get("revise_at")
            continue_revision = response.get("continue_revision", True)

            try:
                student_word = StudentWord.objects.get(
                    id=student_word_id, student=profile
                )
                student_word.successes = successes
                student_word.next_1 = next_1
                student_word.next_2 = next_2
                student_word.revise_at = revise_at
                student_word.continue_revision = continue_revision
                student_word.is_master = successes >= 3
                student_word.save()
                updated_items.append(student_word_id)
            except StudentWord.DoesNotExist:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"StudentWord with ID {student_word_id} not found",
                    }
                )

        # Count remaining items due for revision
        remaining_items = StudentWord.objects.filter(
            student=profile,
            revise_at__lte=timezone.now(),
            continue_revision=True,
        ).count()

        response_data = {
            "status": "success",
            "message": "Progress saved successfully!",
            "stats": {"remaining_items": remaining_items},
        }

        if is_completed:
            response_data["redirect_url"] = reverse("dictionary:dictionary_search")

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
