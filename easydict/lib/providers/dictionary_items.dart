import 'package:flutter/material.dart';
import './word_item.dart';

class DictionaryItems with ChangeNotifier {
  final List<WordItem> _items = [
    WordItem(
      id: 'apple',
      chinese: 'n. 蘋果, 傢夥\n[醫] 蘋果',
      english:
          'n. fruit with red or yellow or green skin and sweet to tart crisp whitish flesh\nn. native Eurasian tree widely cultivated in many varieties for its firm rounded edible fruits.',
      audioUrl: 'apple.mp3',
    ),
    WordItem(
      id: 'orange',
      chinese: '橙',
      english: 'The fruit from an orange tree',
      audioUrl: 'orange.mp3',
    ),
    WordItem(
      id: 'apply',
      chinese: '應用',
      english: 'The fruit from an orange tree',
      sentences: ['I like apples.', 'Apple is a good fruit.'],
      imageUrl:
          'https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Ambersweet_oranges.jpg/255px-Ambersweet_oranges.jpg',
    ),
    WordItem(
      id: 'Application',
      chinese: '應用',
      english: 'The fruit from an orange tree',
      sentences: ['I like apples.', 'Apple is a good fruit.'],
      imageUrl:
          'https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Ambersweet_oranges.jpg/255px-Ambersweet_oranges.jpg',
    ),
  ];
  List<WordItem> get items {
    return [..._items];
  }

  WordItem findById(String id) {
    return _items.firstWhere((word) => word.id == id);
  }
}
