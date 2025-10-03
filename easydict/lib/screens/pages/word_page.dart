import 'package:flutter/material.dart';

class WordPage extends StatefulWidget {
  const WordPage({Key? key}) : super(key: key);

  @override
  State<WordPage> createState() => _WordPageState();
}

class _WordPageState extends State<WordPage> {
  late TextEditingController _controller;
  // double _tileHeight = 70;
  final double _subTitleHeight = 30;
  final int _maxKeys = 1;
  final List<String> _keys = [];

  @override
  void initState() {
    _controller = TextEditingController();
    FocusManager.instance.primaryFocus?.unfocus();
    super.initState();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void showDetails(String key) {
    if (_keys.contains(key)) {
      _keys.remove(key);
    } else if (_keys.length < _maxKeys)
      _keys.add(key);
    else {
      _keys.removeAt(0);
      _keys.add(key);
    }
  }

  @override
  Widget build(BuildContext context) {
    var _textTheme = Theme.of(context).textTheme;
    return Scaffold(
      // floatingActionButton: FloatingActionButton(
      //   onPressed: () {
      //     // Add your onPressed code here!
      //   },
      //   child: const Icon(
      //     Icons.add,
      //     color: Colors.white,
      //   ),
      // ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('字詞', style: _textTheme.displayMedium),
                Container(
                  padding: const EdgeInsets.only(top: 10, bottom: 5),
                  width: double.infinity,
                  child: const Text('你共累積 1230 個字詞，其中 120 個有待複習。'),
                ),
                Container(
                  padding: EdgeInsets.zero,
                  child: ElevatedButton(
                    onPressed: () {},
                    child: const Text('複習'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.amber,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              children: <Widget>[
                Divider(
                  color: Colors.grey.shade300,
                  thickness: 1,
                  height: 3,
                ),
                Container(
                  color: _keys.contains('Apple') ? Colors.yellow.shade50 : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Apple') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Apple');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#12303'),
                    title: Text(
                      'Apple',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height: _keys.contains('Apple') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Apple')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Apple')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.error),
                            color: Colors.red,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  color: _keys.contains('Dance') ? Colors.yellow.shade50 : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Dance') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Dance');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#1229'),
                    title: Text(
                      'Dance',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height: _keys.contains('Dance') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Dance')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Apple')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.error),
                            color: Colors.red,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  color:
                      _keys.contains('Orange') ? Colors.yellow.shade50 : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Orange') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Orange');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#1229'),
                    title: Text(
                      'Orange',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height: _keys.contains('Orange') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Orange')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Orange')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.check_circle),
                            color: Colors.grey,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  color: _keys.contains('Kiwi Fruit')
                      ? Colors.yellow.shade50
                      : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Kiwi Fruit') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Kiwi Fruit');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#1229'),
                    title: Text(
                      'Kiwi Fruit',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height:
                          _keys.contains('Kiwi Fruit') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Kiwi Fruit')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Kiwi Fruit')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.check_circle),
                            color: Colors.grey,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  color: _keys.contains('Pear') ? Colors.yellow.shade50 : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Pear') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Pear');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#1229'),
                    title: Text(
                      'Pear',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height: _keys.contains('Pear') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Pear')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Pear')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.check_circle),
                            color: Colors.grey,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  color: _keys.contains('Melon') ? Colors.yellow.shade50 : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Melon') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Melon');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#1229'),
                    title: Text(
                      'Melon',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height: _keys.contains('Melon') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Melon')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Melon')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.check_circle),
                            color: Colors.grey,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  color:
                      _keys.contains('Banana') ? Colors.yellow.shade50 : null,
                  padding: EdgeInsets.symmetric(
                    vertical: _keys.contains('Banana') ? 10 : 0,
                  ),
                  // constraints: BoxConstraints(
                  //   minHeight: _keys.contains('Apple') ? 150 : 0,
                  // ),
                  child: ListTile(
                    onTap: () {
                      setState(() {
                        showDetails('Banana');
                      });
                    },
                    minLeadingWidth: 55,
                    leading: const Text('#1229'),
                    title: Text(
                      'Banana',
                      style: _textTheme.displayMedium,
                    ),
                    subtitle: SizedBox(
                      height: _keys.contains('Banana') ? null : _subTitleHeight,
                      child: Text(
                        'n. 蘋果，some interesting way of doing things are you sure.  And there is nothing And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is noth  And there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothAnd there is nothright?',
                        overflow: _keys.contains('Banana')
                            ? null
                            : TextOverflow.ellipsis,
                      ),
                    ),
                    trailing: _keys.contains('Banana')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              print('test');
                            },
                          )
                        : IconButton(
                            icon: const Icon(Icons.check_circle),
                            color: Colors.grey,
                            onPressed: () {
                              print('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                const SizedBox(height: 200),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
