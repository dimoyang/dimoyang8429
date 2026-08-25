import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart';
import 'package:meditour_app/app/router.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/business/providers/itinerary_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/app_constant.dart';
import 'package:meditour_app/presentation/themes/app_theme.dart';

/// 应用根组件
class MeditourApp extends StatelessWidget {
  const MeditourApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => LanguageProvider()),
        ChangeNotifierProvider(
          create: (_) => FavoritesProvider()..load(),
        ),
        ChangeNotifierProvider(
          create: (_) => ItineraryProvider()..load(),
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
