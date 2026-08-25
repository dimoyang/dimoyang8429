import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 远程图片组件
///
/// 图片加载失败时显示渐变占位，避免空白破图。
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
    return Image.network(
      url,
      fit: BoxFit.cover,
      width: double.infinity,
      height: double.infinity,
      errorBuilder: (context, error, stackTrace) => _fallback(),
      loadingBuilder: (context, child, progress) {
        if (progress == null) {
          return child;
        }
        return Container(
          color: AppColors.primaryBg,
          child: const Center(
            child: SizedBox(
              width: 22,
              height: 22,
              child: CircularProgressIndicator(strokeWidth: 2.5),
            ),
          ),
        );
      },
    );
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
