import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 远程图片组件
///
/// 基于 [CachedNetworkImage]：磁盘缓存避免滑动时重复下载，
/// `memCacheWidth` 按控件实际宽度（物理像素）解码，避免原图整张解码占用内存。
/// 加载失败时显示渐变占位，避免空白破图。
class RemoteImage extends StatelessWidget {
  final String url;
  final String alt;
  final IconData fallbackIcon;

  const RemoteImage({
    super.key,
    required this.url,
    required this.alt,
    this.fallbackIcon = Icons.image_outlined,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        // 控件的逻辑宽度：无界时（如被 ScrollView 包裹）回退到 800。
        final logicalWidth =
            constraints.maxWidth.isFinite && constraints.maxWidth > 0
                ? constraints.maxWidth
                : 800.0;
        final devicePixelRatio = MediaQuery.devicePixelRatioOf(context);
        // 上限 1600px，避免超大屏上把整图按原始尺寸解码。
        final decodeWidth =
            (logicalWidth * devicePixelRatio).round().clamp(1, 1600);

        return Semantics(
          image: true,
          label: alt,
          child: CachedNetworkImage(
            imageUrl: url,
            fit: BoxFit.cover,
            width: double.infinity,
            height: double.infinity,
            memCacheWidth: decodeWidth,
            fadeInDuration: const Duration(milliseconds: 200),
            placeholder: (context, url) => _placeholder(),
            errorWidget: (context, url, error) => _fallback(),
          ),
        );
      },
    );
  }

  /// 加载中占位：静态色块，不做无限动画，避免长列表持续重建。
  Widget _placeholder() {
    return Container(color: AppColors.primaryBg);
  }

  Widget _fallback() {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.primaryLight, Color(0xFFE2F6F3)],
        ),
      ),
      child: Center(
        child: Icon(fallbackIcon, size: 42, color: AppColors.primary),
      ),
    );
  }
}
