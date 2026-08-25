import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/l10n/app_localizations.dart';

/// 入境中国常用旅行指南。
class TravelToolsScreen extends StatelessWidget {
  const TravelToolsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final tools = [
      _TravelTool(
        icon: Icons.badge_outlined,
        title: l10n.toolVisaTitle,
        summary: l10n.toolVisaSummary,
        detail: l10n.toolVisaDetail,
      ),
      _TravelTool(
        icon: Icons.account_balance_wallet_outlined,
        title: l10n.toolPaymentTitle,
        summary: l10n.toolPaymentSummary,
        detail: l10n.toolPaymentDetail,
      ),
      _TravelTool(
        icon: Icons.train_outlined,
        title: l10n.toolTransportTitle,
        summary: l10n.toolTransportSummary,
        detail: l10n.toolTransportDetail,
      ),
      _TravelTool(
        icon: Icons.sim_card_outlined,
        title: l10n.toolInternetTitle,
        summary: l10n.toolInternetSummary,
        detail: l10n.toolInternetDetail,
      ),
    ];

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.travelToolsTitle),
        centerTitle: false,
      ),
      body: ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        itemCount: tools.length + 1,
        separatorBuilder: (_, __) => const SizedBox(height: 10),
        itemBuilder: (context, index) {
          if (index == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                l10n.travelToolsIntro,
                style: const TextStyle(
                  color: AppColors.ink2,
                  fontSize: 13.5,
                  height: 1.6,
                ),
              ),
            );
          }

          final tool = tools[index - 1];
          return _TravelToolTile(
            tool: tool,
            onTap: () => _showToolDetails(context, tool),
          );
        },
      ),
    );
  }

  Future<void> _showToolDetails(
    BuildContext context,
    _TravelTool tool,
  ) {
    return showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      builder: (sheetContext) {
        return SafeArea(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(24, 4, 24, 28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: AppColors.primaryBg,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Icon(tool.icon, color: AppColors.primary),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          tool.title,
                          style: const TextStyle(
                            color: AppColors.ink,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: MaterialLocalizations.of(
                          sheetContext,
                        ).closeButtonTooltip,
                        onPressed: () => Navigator.of(sheetContext).pop(),
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Text(
                    tool.detail,
                    style: const TextStyle(
                      color: AppColors.ink2,
                      fontSize: 14,
                      height: 1.7,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _TravelToolTile extends StatelessWidget {
  final _TravelTool tool;
  final VoidCallback onTap;

  const _TravelToolTile({
    required this.tool,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: AppColors.line),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: AppColors.primaryBg,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(tool.icon, color: AppColors.primary),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      tool.title,
                      style: const TextStyle(
                        color: AppColors.ink,
                        fontSize: 15,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      tool.summary,
                      style: const TextStyle(
                        color: AppColors.ink2,
                        fontSize: 12.5,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              const Icon(
                Icons.chevron_right,
                color: AppColors.ink3,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TravelTool {
  final IconData icon;
  final String title;
  final String summary;
  final String detail;

  const _TravelTool({
    required this.icon,
    required this.title,
    required this.summary,
    required this.detail,
  });
}
