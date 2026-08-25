import 'package:flutter/material.dart';
import 'package:meditour_app/business/providers/favorites_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:provider/provider.dart';

/// 目的地收藏按钮，在列表卡片和详情页之间共享。
class DestinationFavoriteButton extends StatelessWidget {
  final String destinationId;
  final Color backgroundColor;
  final Color inactiveColor;

  const DestinationFavoriteButton({
    super.key,
    required this.destinationId,
    this.backgroundColor = Colors.white,
    this.inactiveColor = AppColors.ink2,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final isFavorite = context.select<FavoritesProvider, bool>(
      (provider) => provider.isFavorite(destinationId),
    );

    return Material(
      color: backgroundColor,
      shape: const CircleBorder(),
      child: IconButton(
        tooltip: isFavorite ? l10n.removeFromFavorites : l10n.addToFavorites,
        constraints: const BoxConstraints.tightFor(width: 36, height: 36),
        padding: EdgeInsets.zero,
        onPressed: () {
          context.read<FavoritesProvider>().toggleDestination(destinationId);
        },
        icon: Icon(
          isFavorite ? Icons.favorite : Icons.favorite_border,
          color: isFavorite ? const Color(0xFFFFB703) : inactiveColor,
          size: 20,
        ),
      ),
    );
  }
}
