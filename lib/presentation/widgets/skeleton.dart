import 'package:flutter/material.dart';
import 'package:meditour_app/core/constants/colors.dart';

/// 骨架占位块。
///
/// 刻意使用静态色块、不做循环动画：动画会让 widget 测试里的
/// `pumpAndSettle` 永远等不到稳定状态，也会分散低端设备性能。
class SkeletonBox extends StatelessWidget {
  final double? width;
  final double? height;
  final double radius;

  const SkeletonBox({super.key, this.width, this.height, this.radius = 8});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.line,
        borderRadius: BorderRadius.circular(radius),
      ),
    );
  }
}

/// 文字行占位；[widthFactor] 相对父宽。
class SkeletonLine extends StatelessWidget {
  final double widthFactor;
  final double height;

  const SkeletonLine({super.key, this.widthFactor = 1, this.height = 12});

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      alignment: Alignment.centerLeft,
      child: SkeletonBox(height: height, radius: 6),
    );
  }
}

/// 骨架区域：读屏只播报"加载中"，内部占位块不产生多余语义节点。
class SkeletonArea extends StatelessWidget {
  final String label;
  final Widget child;

  const SkeletonArea({super.key, required this.label, required this.child});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      container: true,
      label: label,
      child: ExcludeSemantics(child: child),
    );
  }
}

/// 目的地卡片骨架：图区与底部文案比例贴合 DestinationCard。
class SkeletonDestinationCard extends StatelessWidget {
  const SkeletonDestinationCard({super.key});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(18),
      child: Container(
        color: Colors.white,
        child: Column(
          children: const [
            Expanded(flex: 4, child: SkeletonBox(radius: 0)),
            Expanded(
              flex: 1,
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(widthFactor: 0.55, height: 15),
                    SizedBox(height: 6),
                    SkeletonLine(widthFactor: 0.7, height: 10),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
