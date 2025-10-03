import 'package:easydict/providers/dictionary_items.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import './pages/dictionary_page.dart';
import './pages/word_page.dart';
import './pages/wordlist_page.dart';

enum Options { person, password, exit }

class MainScreen extends StatefulWidget {
  static const routeName = '/main_screen';
  const MainScreen({Key? key}) : super(key: key);

  @override
  State<MainScreen> createState() => _MainScreen();
}

class _MainScreen extends State<MainScreen> {
  var appBarHeight = AppBar().preferredSize.height;

  @override
  void initState() {
    super.initState();
    SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
  }

  PopupMenuItem _buildPopupMenuItem(
      String title, IconData iconData, int position) {
    return PopupMenuItem(
      value: position,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Icon(
            iconData,
            color: Colors.black,
          ),
          const SizedBox(width: 5),
          Expanded(child: Text(title)),
        ],
      ),
    );
  }

  _onMenuItemSelected(int value) {
    setState(() {});
    if (value == Options.person.index) {
    } else if (value == Options.password.index) {
    } else {}
  }

  @override
  Widget build(BuildContext context) {
    var textTheme = Theme.of(context).textTheme;
    return ChangeNotifierProvider<DictionaryItems>(
      create: (context) => DictionaryItems(),
      child: DefaultTabController(
        length: 3,
        child: Scaffold(
          drawer: Drawer(
            shape: const RoundedRectangleBorder(
              borderRadius: BorderRadius.zero, // Removes rounded corners
            ),
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                SizedBox(
                  height: 112,
                  child: DrawerHeader(
                    decoration: const BoxDecoration(
                      color: Colors.blue,
                    ),
                    child: Text(
                      'WhatsLearn',
                      style: textTheme.displaySmall,
                    ),
                  ),
                ),
                // ListTile(
                //   minLeadingWidth: 0,
                //   leading: const Icon(Icons.search, color: Colors.blue),
                //   title: const Text(
                //     'EasyDict',
                //     style: TextStyle(color: Colors.blue, fontSize: 20),
                //   ),
                //   onTap: () {
                //     // Update the state of the app.
                //     // ...
                //   },
                // ),
                ListTile(
                  minLeadingWidth: 0,
                  leading: const Icon(Icons.person, color: Colors.blue),
                  title: const Text(
                    '個人設定',
                    style: TextStyle(color: Colors.blue, fontSize: 20),
                  ),
                  onTap: () {
                    // Update the state of the app.
                    // ...
                  },
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                ListTile(
                  minLeadingWidth: 0,
                  leading: const Icon(Icons.vpn_key, color: Colors.blue),
                  title: const Text(
                    '更改密碼',
                    style: TextStyle(color: Colors.blue, fontSize: 20),
                  ),
                  onTap: () {
                    // Update the state of the app.
                    // ...
                  },
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
                ListTile(
                  minLeadingWidth: 0,
                  leading: const Icon(Icons.exit_to_app, color: Colors.blue),
                  title: const Text(
                    '登出',
                    style: TextStyle(color: Colors.blue, fontSize: 20),
                  ),
                  onTap: () {
                    // Update the state of the app.
                    // ...
                  },
                ),
                Divider(
                  color: Colors.grey.shade300,
                  height: 3,
                  thickness: 1,
                ),
              ],
            ),
          ),
          appBar: AppBar(
            titleSpacing: 0,
            bottom: const TabBar(
              tabs: [
                Tab(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.search),
                      SizedBox(width: 5),
                      Text('字典'),
                    ],
                  ),
                ),
                Tab(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.trending_up),
                      SizedBox(width: 5),
                      Text('字詞'),
                    ],
                  ),
                ),
                Tab(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.local_library),
                      SizedBox(width: 5),
                      Text('學習'),
                    ],
                  ),
                ),
              ],
            ),
            title: const Text('EasyDict'),
            // actions: [
            //   PopupMenuButton(
            //     icon: CircleAvatar(
            //       backgroundColor: Colors.grey.shade200,
            //       child: const Icon(Icons.person),
            //     ),
            //     onSelected: (value) {
            //       _onMenuItemSelected(value as int);
            //     },
            //     offset: Offset(4.0, appBarHeight),
            //     itemBuilder: (ctx) => [
            //       _buildPopupMenuItem(
            //           '個人資料', Icons.person, Options.person.index),
            //       _buildPopupMenuItem(
            //           '更改密碼', Icons.vpn_key, Options.password.index),
            //       _buildPopupMenuItem(
            //           '登出', Icons.exit_to_app, Options.exit.index),
            //     ],
            //   )
            // ],
          ),
          body: const TabBarView(
            children: <Widget>[
              DictionaryPage(),
              WordPage(),
              WordlistPage(),
            ],
          ),
        ),
      ),
    );
  }
}
