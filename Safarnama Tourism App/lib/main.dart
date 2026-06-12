import 'package:flutter/material.dart';

import 'screens/chat_screen.dart';
import 'services/api_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await ApiService.instance.loadPrefs();
  runApp(const SafarnamaApp());
}

class SafarnamaApp extends StatelessWidget {
  const SafarnamaApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'SafarnāmaGPT',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF01411C), // Pakistan green
          ),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF01411C),
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
        ),
        themeMode: ThemeMode.system,
        home: const ChatScreen(),
      );
}
