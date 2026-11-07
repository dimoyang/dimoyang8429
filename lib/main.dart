import 'package:flutter/material.dart';
import 'package:meditour_app/app/app.dart';
import 'package:meditour_app/core/services/storage_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final savedLanguageCode = await StorageService.getLanguageCode();
  runApp(MeditourApp(initialLanguageCode: savedLanguageCode));
}
