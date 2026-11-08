import 'package:flutter/material.dart';
import 'package:meditour_app/business/providers/language_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:provider/provider.dart';

/// 显示应用统一的语言选择面板。
Future<void> showLanguagePickerSheet(BuildContext context) {
  final provider = context.read<LanguageProvider>();
  final currentCode = provider.currentLocale.languageCode;

  return showModalBottomSheet<void>(
    context: context,
    backgroundColor: Colors.white,
    showDragHandle: true,
    builder: (sheetContext) {
      return SafeArea(
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.only(bottom: 8),
          children: LanguageProvider.languageOptions.map((option) {
            final (code, name, flag) = option;
            final selected = code == currentCode;

            return ListTile(
              leading: Text(flag, style: const TextStyle(fontSize: 22)),
              title: Text(
                name,
                style: TextStyle(
                  color: selected ? AppColors.primaryDark : AppColors.ink,
                  fontSize: 15,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
                ),
              ),
              trailing: selected
                  ? const Icon(
                      Icons.check_circle,
                      color: AppColors.primaryDark,
                      size: 20,
                    )
                  : null,
              onTap: () {
                provider.setLanguage(code);
                Navigator.of(sheetContext).pop();
              },
            );
          }).toList(),
        ),
      );
    },
  );
}
