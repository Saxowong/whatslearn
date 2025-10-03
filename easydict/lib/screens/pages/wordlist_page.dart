import 'package:flutter/material.dart';
import '../../widgets/progress.dart';
import 'dart:developer' as developer;

class WordlistPage extends StatefulWidget {
  const WordlistPage({Key? key}) : super(key: key);

  @override
  State<WordlistPage> createState() => _WordlistPageState();
}

class _WordlistPageState extends State<WordlistPage> {
  late TextEditingController _controller;
  final int _maxKeys = 1;
  final List<String> myKeys = [];

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
    if (myKeys.contains(key)) {
      myKeys.remove(key);
    } else if (myKeys.length < _maxKeys)
      // ignore: curly_braces_in_flow_control_structures
      myKeys.add(key);
    else {
      myKeys.removeAt(0);
      myKeys.add(key);
    }
  }

  @override
  Widget build(BuildContext context) {
    var textTheme = Theme.of(context).textTheme;
    return Scaffold(
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('學習', style: textTheme.displayMedium),
                Container(
                  padding: const EdgeInsets.only(top: 10, bottom: 5),
                  width: double.infinity,
                  child: const Text('你共學習 1230 個字彙，其中 120 個有待複習。'),
                ),
                Container(
                  padding: EdgeInsets.zero,
                  child: ElevatedButton(
                    onPressed: () {},
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.amber,
                    ),
                    child: const Text('複習'),
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
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: ListTile(
                    onTap: () {},
                    leading: CircleAvatar(
                      foregroundColor: Colors.white,
                      backgroundColor: Colors.grey.shade400,
                      child: const Icon(Icons.local_library),
                    ),
                    title: Text(
                      'Dictionary (24 words)',
                      style: textTheme.displayMedium,
                    ),
                    subtitle: ProgressWidget(0, 11),
                    trailing: myKeys.contains('Apple')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              developer.log('test');
                            },
                          )
                        : ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              elevation: 0,
                              minimumSize: Size.zero, // Set this
                              padding: const EdgeInsets.all(6),
                              shape: const RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.all(Radius.circular(50))),
                            ),
                            child: const Text('36'),
                            onPressed: () {
                              developer.log('test');
                            },
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  thickness: 1,
                  height: 3,
                ),
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: ListTile(
                    onTap: () {},
                    leading: CircleAvatar(
                      foregroundColor: Colors.white,
                      backgroundColor: Colors.grey.shade400,
                      child: const Icon(Icons.local_library),
                      // backgroundColor: Color(0xFFA0A0A0),
                    ),
                    title: Text(
                      'Simple English (800 words)',
                      style: textTheme.displayMedium,
                    ),
                    subtitle: ProgressWidget(15, 0),
                    trailing: myKeys.contains('Apple')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              developer.log('test');
                            },
                          )
                        : ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              elevation: 0,
                              minimumSize: Size.zero, // Set this
                              padding: const EdgeInsets.all(6),
                              shape: const RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.all(Radius.circular(50))),
                            ),
                            child: const Text('134'),
                            onPressed: () {},
                          ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: ListTile(
                    onTap: () {},
                    leading: CircleAvatar(
                      foregroundColor: Colors.white,
                      backgroundColor: Colors.grey.shade400,
                      child: const Icon(Icons.local_library),
                    ),
                    title: Text(
                      'Basic English (1200 words)',
                      style: textTheme.displayMedium,
                    ),
                    subtitle: ProgressWidget(15, 3),
                    trailing: myKeys.contains('Apple')
                        ? IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () {
                              developer.log('test');
                            },
                          )
                        : ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              elevation: 0,
                              minimumSize: Size.zero, // Set this
                              padding: const EdgeInsets.all(6),
                              shape: const RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.all(Radius.circular(50))),
                            ),
                            child: const Text('36'),
                            onPressed: () {
                              developer.log('test');
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
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: ListTile(
                    onTap: () {},
                    leading: CircleAvatar(
                      foregroundColor: Colors.white,
                      backgroundColor: Colors.grey.shade400,
                      child: const Icon(Icons.local_library),
                    ),
                    title: Text(
                      'Intermediate English (1400 words)',
                      style: textTheme.displayMedium,
                    ),
                    subtitle: ProgressWidget(4, 14),
                    trailing: IconButton(
                      icon: const Icon(Icons.chevron_right),
                      onPressed: () {},
                    ),
                  ),
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: ListTile(
                    onTap: () {},
                    leading: CircleAvatar(
                      foregroundColor: Colors.white,
                      backgroundColor: Colors.grey.shade400,
                      child: const Icon(Icons.local_library),
                    ),
                    title: Text(
                      'Advanced English (2400 words)',
                      style: textTheme.displayMedium,
                    ),
                    subtitle: ProgressWidget(0, 14),
                    trailing: IconButton(
                      icon: const Icon(Icons.chevron_right),
                      onPressed: () {
                        developer.log('test');
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
