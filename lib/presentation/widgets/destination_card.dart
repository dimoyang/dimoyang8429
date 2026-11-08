import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/data/models/destination.dart';
import 'package:meditour_app/presentation/widgets/destination_favorite_button.dart';
import 'package:meditour_app/presentation/widgets/remote_image.dart';

/// 目的地宫格宽高比：大字号时卡片适当增高，避免底部文字被裁切。
double destinationCardAspectRatio(BuildContext context) {
  final textScale = MediaQuery.textScalerOf(context).scale(1).clamp(1.0, 2.0);
  return 4 / (5 * textScale);
}

/// 目的地宫格卡片
class DestinationCard extends StatelessWidget {
  final Destination destination;

  const DestinationCard({super.key, required this.destination});

  @override
  Widget build(BuildContext context) {
    final langCode = Localizations.localeOf(context).languageCode;
    final name = destination.getName(langCode);

    return Semantics(
      button: true,
      label: name,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(18),
        child: Stack(
          fit: StackFit.expand,
          children: [
            RemoteImage(
              url: destination.imageUrl,
              alt: name,
              fallbackIcon: Icons.location_city_outlined,
            ),
            // 底部渐变遮罩与文字
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    Colors.transparent,
                    Colors.black.withValues(alpha: 0.15),
                    Colors.black.withValues(alpha: 0.72),
                  ],
                  stops: const [0.4, 0.65, 1.0],
                ),
              ),
            ),
            Positioned(
              left: 13,
              right: 13,
              bottom: 12,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text.rich(
                    TextSpan(
                      text: name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                      ),
                      children: [
                        if (langCode != 'zh')
                          TextSpan(
                            text: '  ${destination.name}',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.7),
                              fontSize: 11,
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                      ],
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 3),
                  Text(
                    destination.tagline,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.88),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            // 覆盖在图片之上，点击时能看到水波纹反馈。
            Positioned.fill(
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () {
                    context.pushNamed(
                      'destinationDetail',
                      pathParameters: {'id': destination.id},
                    );
                  },
                ),
              ),
            ),
            // 收藏按钮位于最上层，避免被点击层拦截。
            Positioned(
              top: 8,
              right: 8,
              child: DestinationFavoriteButton(
                destinationId: destination.id,
                backgroundColor: Colors.black.withValues(alpha: 0.34),
                inactiveColor: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
