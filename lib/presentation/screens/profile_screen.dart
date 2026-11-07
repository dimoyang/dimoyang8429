import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/language_picker_sheet.dart';
import 'package:provider/provider.dart';

/// 偏好设置与非核心协助入口。
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final provider = context.watch<LanguageProvider>();
    final language = LanguageProvider.languageOptions.firstWhere(
      (option) => option.$1 == provider.currentLocale.languageCode,
      orElse: () => LanguageProvider.languageOptions.first,
    );

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.profileTitle),
        centerTitle: false,
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          _SectionLabel(l10n.profileAccount),
          const SizedBox(height: 8),
          Consumer<AuthProvider>(
            builder: (context, auth, _) {
              if (!auth.isInitialized) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 18),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (!auth.isLoggedIn) {
                return _SettingsTile(
                  icon: Icons.person_outline,
                  title: l10n.loginButton,
                  subtitle: l10n.loginEntrySub,
                  onTap: () => context.pushNamed('login'),
                );
              }
              final user = auth.user!;
              return Column(
                children: [
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.line),
                    ),
                    child: Row(
                      children: [
                        CircleAvatar(
                          radius: 21,
                          backgroundColor: AppColors.primary,
                          child: Text(
                            user.displayName.isNotEmpty
                                ? user.displayName[0].toUpperCase()
                                : '?',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                user.displayName,
                                style: const TextStyle(
                                  color: AppColors.ink,
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                user.email,
                                style: const TextStyle(
                                  color: AppColors.ink2,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 8),
                  _SettingsTile(
                    icon: Icons.logout,
                    title: l10n.logout,
                    onTap: () => auth.logout(),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.receipt_long_outlined,
            title: l10n.profileBookings,
            subtitle: l10n.profileBookingsSub,
            onTap: () => context.pushNamed('bookings'),
          ),
          const SizedBox(height: 24),
          _SectionLabel(l10n.profilePreferences),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.translate,
            title: l10n.profileLanguage,
            subtitle: '${language.$3} ${language.$2}',
            onTap: () => showLanguagePickerSheet(context),
          ),
          const SizedBox(height: 24),
          _SectionLabel(l10n.profileMoreAssistance),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.health_and_safety_outlined,
            title: l10n.medicalEntryTitle,
            subtitle: l10n.medicalEntrySub,
            onTap: () => context.pushNamed('medical'),
          ),
          const SizedBox(height: 24),
          _SectionLabel(l10n.profileAbout),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.info_outline,
            title: l10n.profileAppVersion,
            subtitle: '1.0.0',
          ),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.description_outlined,
            title: l10n.profileLicenses,
            onTap: () => showLicensePage(
              context: context,
              applicationName: l10n.appTitle,
              applicationVersion: '1.0.0',
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;

  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppColors.ink2,
        fontSize: 12,
        fontWeight: FontWeight.w700,
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;

  const _SettingsTile({
    required this.icon,
    required this.title,
    this.subtitle,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: AppColors.line),
      ),
      child: ListTile(
        onTap: onTap,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        leading: Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: AppColors.primaryBg,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: AppColors.primary, size: 21),
        ),
        title: Text(
          title,
          style: const TextStyle(
            color: AppColors.ink,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        subtitle: subtitle == null
            ? null
            : Text(
                subtitle!,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: AppColors.ink2,
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
        trailing: onTap == null
            ? null
            : const Icon(
                Icons.chevron_right,
                color: AppColors.ink3,
                size: 20,
              ),
      ),
    );
  }
}
