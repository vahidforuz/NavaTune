import 'package:flutter/material.dart';

import 'screens/main_navigation_screen.dart';

class AvaTuneApp extends StatelessWidget {
  const AvaTuneApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      title: 'NavaTune',
      debugShowCheckedModeBanner: false,
      home: MainNavigationScreen(),
    );
  }
}
