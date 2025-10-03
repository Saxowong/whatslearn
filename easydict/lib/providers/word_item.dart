import 'package:flutter/foundation.dart';

class WordItem with ChangeNotifier {
  final String? id;
  final String? chinese;
  final String? english;
  final List<String>? sentences;
  final String? audioUrl;
  final String? imageUrl;

  WordItem({
    @required this.id,
    this.chinese,
    this.english,
    this.sentences,
    this.audioUrl,
    this.imageUrl,
  });

  // void _setFavValue(bool newValue) {
  //   isFavorite = newValue;
  //   notifyListeners();
  // }
}
