import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/dictionary_items.dart';
import '../../providers/word_item.dart';
import 'dart:developer' as developer;

String searchString = '';

class DictionaryPage extends StatefulWidget {
  const DictionaryPage({Key? key}) : super(key: key);

  @override
  State<DictionaryPage> createState() => _DictionaryPageState();
}

class _DictionaryPageState extends State<DictionaryPage> {
  late TextEditingController _controller;
  // double _tileHeight = 70;
  final double _subTitleHeight = 30;
  final int _maxKeys = 1;
  final List<String> myKeys = [];

  @override
  void initState() {
    _controller = TextEditingController();
    super.initState();
    _controller.addListener(_processInput);
  }

  void _processInput() {
    setState(() {
      searchString = _controller.text;
    });
    developer.log('Second text field: ${_controller.text}');
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void showDetails(String key) {
    if (myKeys.contains(key)) {
      myKeys.remove(key);
    } else if (myKeys.length < _maxKeys)
      myKeys.add(key);
    else {
      myKeys.removeAt(0);
      myKeys.add(key);
    }
  }

  @override
  Widget build(BuildContext context) {
    var textTheme = Theme.of(context).textTheme;
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('字典', style: textTheme.displayMedium),
              Container(
                padding: const EdgeInsets.only(top: 10, bottom: 10),
                child: TextField(
                  controller: _controller,
                  style: const TextStyle(fontSize: 16),
                  decoration: InputDecoration(
                    hintText: '輸入字詞或句子',
                    filled: true,
                    suffixIcon: IconButton(
                      onPressed: () {
                        _controller.clear();
                      },
                      color: Colors.grey,
                      icon: const Icon(Icons.clear),
                    ),
                  ),
                  onSubmitted: (String value) {},
                ),
              ),
              Container(
                padding: EdgeInsets.zero,
                child: ElevatedButton(
                  onPressed: () {},
                  child: const Text('搜尋'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.amber,
                  ),
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: (_controller.text == '')
              ? const Text('')
              : Consumer<DictionaryItems>(
                  builder: (context, wordData, child) => ListView.builder(
                    itemCount: wordData.items.length,
                    itemBuilder: (BuildContext context, int index) {
                      WordItem word = wordData.items[index];
                      return Column(
                        children: <Widget>[
                          Divider(
                            color: Colors.grey.shade300,
                            thickness: 1,
                            height: 3,
                          ),
                          Container(
                            color: myKeys.contains(word.id)
                                ? Colors.yellow.shade50
                                : null,
                            padding: EdgeInsets.symmetric(
                              vertical: myKeys.contains(word.id) ? 10 : 0,
                            ),
                            child: ListTile(
                              onTap: () {
                                setState(() {
                                  showDetails(word.id!);
                                });
                              },
                              title: Text(
                                word.id!,
                                style: textTheme.displayMedium,
                              ),
                              subtitle: Container(
                                height: myKeys.contains(word.id)
                                    ? null
                                    : _subTitleHeight,
                                padding: const EdgeInsets.only(left: 10),
                                child: Text(
                                  "${word.chinese!.trim()}\n${word.english!.trim()}"
                                      .trim(),
                                  maxLines: myKeys.contains(word.id) ? null : 1,
                                  overflow: myKeys.contains(word.id)
                                      ? null
                                      : TextOverflow.ellipsis,
                                ),
                              ),
                              trailing: IconButton(
                                icon: myKeys.contains(word.id)
                                    ? const Icon(Icons.save)
                                    : const Icon(Icons.chevron_right),
                                onPressed: () {
                                  setState(() {
                                    showDetails(word.id!);
                                  });
                                },
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
        ),
      ],
    );
  }
}
