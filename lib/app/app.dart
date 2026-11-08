import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart';
import 'package:meditour_app/app/router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/business/providers/destination_provider.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/presentation/themes/app_theme.dart';

/// 应用根组件
class MeditourApp extends StatelessWidget {
  final String? initialLanguageCode;

  const MeditourApp({super.key, this.initialLanguageCode});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(
          create: (_) => LanguageProvider(initialCode: initialLanguageCode),
        ),
        ChangeNotifierProvider(
          create: (_) => FavoritesProvider()..load(),
        ),
        ChangeNotifierProvider(
          create: (_) => ItineraryProvider()..load(),
        ),
        ChangeNotifierProvider(
          create: (_) => AuthProvider()..init(),
        ),
        ChangeNotifierProxyProvider<LanguageProvider, DestinationProvider>(
          create: (_) => DestinationProvider(),
          update: (_, language, destination) {
            final provider = destination ?? DestinationProvider();
            // 语言切换后按新语言重新拉取；同名语言不会重复请求。
            unawaited(provider.syncLanguage(
              language.currentLocale.languageCode,
            ));
            return provider;
          },
        ),
      ],
      child: Consumer<LanguageProvider>(
        builder: (context, languageProvider, _) {
          return MaterialApp.router(
            title: AppConstants.appName,
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light(),
            locale: languageProvider.currentLocale,
            supportedLocales: AppConstants.supportedLocales,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            routerConfig: AppRouter.router,
          );
        },
      ),
    );
  }
}
