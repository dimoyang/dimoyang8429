import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:meditour_app/app/app.dart';
import 'package:meditour_app/core/services/storage_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // 初始化 intl 日期符号：非英文语言（zh/de/fr）的 DateFormat 需要提前加载。
  await initializeDateFormatting();
  final savedLanguageCode = await StorageService.getLanguageCode();
  runApp(MeditourApp(initialLanguageCode: savedLanguageCode));
}
