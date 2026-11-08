import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/services/export_saver.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/app_toast.dart';
import 'package:meditour_app/presentation/widgets/language_picker_sheet.dart';
import 'package:meditour_app/presentation/widgets/section_label.dart';
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
          SectionLabel(l10n.profileAccount),
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
                          backgroundColor: AppColors.primaryDark,
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
                  const SizedBox(height: 20),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: SectionLabel(l10n.profileAccountSecurity),
                  ),
                  const SizedBox(height: 8),
                  _SettingsTile(
                    icon: Icons.lock_outline,
                    title: l10n.profileChangePassword,
                    subtitle: l10n.profileChangePasswordSub,
                    onTap: () => context.pushNamed(
                      'changePassword',
                      queryParameters: const {'redirect': '/profile'},
                    ),
                  ),
                  const SizedBox(height: 8),
                  _SettingsTile(
                    icon: Icons.download_outlined,
                    title: l10n.profileExportData,
                    subtitle: l10n.profileExportDataSub,
                    onTap: () => unawaited(_exportData(context)),
                  ),
                  const SizedBox(height: 8),
                  _SettingsTile(
                    icon: Icons.delete_forever_outlined,
                    iconColor: AppColors.danger,
                    title: l10n.profileDeleteAccount,
                    subtitle: l10n.profileDeleteAccountSub,
                    onTap: () => context.pushNamed('deleteAccount'),
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
          SectionLabel(l10n.profilePreferences),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.translate,
            title: l10n.profileLanguage,
            subtitle: '${language.$3} ${language.$2}',
            onTap: () => showLanguagePickerSheet(context),
          ),
          const SizedBox(height: 24),
          SectionLabel(l10n.profileMoreAssistance),
          const SizedBox(height: 8),
          _SettingsTile(
            icon: Icons.health_and_safety_outlined,
            title: l10n.medicalEntryTitle,
            subtitle: l10n.medicalEntrySub,
            onTap: () => context.pushNamed('medical'),
          ),
          const SizedBox(height: 24),
          SectionLabel(l10n.profileAbout),
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

/// 导出本人数据：Web 直接下载；其他平台降级为预览 + 复制到剪贴板。
Future<void> _exportData(BuildContext context) async {
  final l10n = AppLocalizations.of(context);
  final navigator = Navigator.of(context, rootNavigator: true);
  unawaited(
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => AlertDialog(
        content: Row(
          children: [
            const SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 16),
            Expanded(child: Text(l10n.exportPreparing)),
          ],
        ),
      ),
    ),
  );

  String json;
  try {
    final data = await context.read<AuthProvider>().exportData();
    json = const JsonEncoder.withIndent('  ').convert(data);
  } catch (e) {
    if (!context.mounted) {
      return;
    }
    navigator.pop();
    AppToast.error(
      context,
      e is ApiException ? e.toLocalizedMessage(l10n) : l10n.exportFailed,
    );
    return;
  }
  if (!context.mounted) {
    return;
  }
  navigator.pop();

  final today = DateTime.now().toIso8601String().split('T').first;
  final saved = await saveExport(json, filename: 'meditour-export-$today.json');
  if (!context.mounted) {
    return;
  }
  if (saved) {
    AppToast.success(context, l10n.exportDownloaded);
    return;
  }
  await _showExportPreview(context, json);
}

Future<void> _showExportPreview(BuildContext context, String json) async {
  final l10n = AppLocalizations.of(context);
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(l10n.exportDialogTitle),
      content: SizedBox(
        width: double.maxFinite,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.exportMobileHint,
              style: const TextStyle(
                color: AppColors.ink2,
                fontSize: 12.5,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 12),
            Container(
              height: 260,
              width: double.maxFinite,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.pageBg,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.line),
              ),
              child: SingleChildScrollView(
                child: SelectableText(
                  json,
                  style: const TextStyle(
                    color: AppColors.ink2,
                    fontSize: 12,
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(),
          child: Text(l10n.close),
        ),
        FilledButton(
          onPressed: () async {
            await Clipboard.setData(ClipboardData(text: json));
            if (dialogContext.mounted) {
              Navigator.of(dialogContext).pop();
            }
            if (context.mounted) {
              AppToast.success(context, l10n.exportCopied);
            }
          },
          child: Text(l10n.exportCopy),
        ),
      ],
    ),
  );
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  final Color? iconColor;

  const _SettingsTile({
    required this.icon,
    required this.title,
    this.subtitle,
    this.onTap,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: AppColors.line),
      ),
      child: MergeSemantics(
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
            child: Icon(icon, color: iconColor ?? AppColors.primary, size: 21),
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
      ),
    );
  }
}
