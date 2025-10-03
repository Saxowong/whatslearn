import 'package:flutter/material.dart';
import './screens/main_screen.dart';

// void main() => runApp(MyApp());
void main() {
  runApp(const MyApp());
}

class MyApp extends StatefulWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  State<MyApp> createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'EasyDict',
      theme: ThemeData(
        colorScheme:
            ColorScheme.fromSwatch(primarySwatch: Colors.amber).copyWith(
          secondary: Colors.blue,
          primary: Colors.white,
        ),
        appBarTheme: AppBarTheme.of(context).copyWith(
          color: Colors.blue,
          foregroundColor: Colors.white,
          titleTextStyle: const TextStyle(fontSize: 22, color: Colors.white),
        ),
        textTheme: const TextTheme(
          displayLarge: TextStyle(fontSize: 36.0, color: Colors.black),
          displayMedium: TextStyle(fontSize: 17.0, color: Color(0xBF900000)),
          displaySmall: TextStyle(fontSize: 20.0, color: Colors.white),
          headlineMedium: TextStyle(fontSize: 16.0, color: Colors.black),
          titleMedium: TextStyle(fontSize: 14.0, color: Colors.black),
          bodyLarge: TextStyle(
              fontSize: 24.0, fontFamily: 'Hind', color: Colors.black),
          bodyMedium: TextStyle(
              fontSize: 15.0, fontFamily: 'Hind', color: Colors.black),
        ),
      ),
      home: MainScreen(),
      routes: {
        MainScreen.routeName: (ctx) => MainScreen(),
      },
    );
  }
}
