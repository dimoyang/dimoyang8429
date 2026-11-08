import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/data/models/booking.dart';
import 'package:meditour_app/data/respositories/booking_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';
import 'package:provider/provider.dart';

/// 我的预约订单列表页。
///
/// 未登录时不发起请求，直接展示登录引导；登录后加载当前账号的订单。
class BookingsScreen extends StatefulWidget {
  const BookingsScreen({super.key});

  @override
  State<BookingsScreen> createState() => _BookingsScreenState();
}

class _BookingsScreenState extends State<BookingsScreen> {
  Future<List<BookingOrder>>? _future;

  Future<void> _refresh() async {
    setState(() {
      _future = BookingRepository.list();
    });
    try {
      await _future;
    } catch (_) {
      // 错误由 FutureBuilder 以错误态呈现。
    }
  }

  /// 待确认订单取消：二次确认后调用后端，成功刷新列表。
  ///
  /// 后端 404（不存在或越权）与 409（状态已变化）需要给出不同提示，
  /// 并刷新列表让用户看到最新状态；其余错误按通用文案提示。
  Future<void> _cancel(BookingOrder order) async {
    final l10n = AppLocalizations.of(context);
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.bookingsCancelTitle),
        content: Text(l10n.bookingsCancelBody),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: Text(l10n.bookingsCancelDismiss),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: Text(l10n.bookingsCancelConfirm),
          ),
        ],
      ),
    );
    if (confirmed != true) {
      return;
    }

    try {
      await BookingRepository.cancel(order.id);
      if (!mounted) {
        return;
      }
      _showSnackBar(l10n.bookingsCancelSuccess);
      await _refresh();
    } on ApiException catch (error) {
      if (!mounted) {
        return;
      }
      final message = switch (error) {
        ApiBusinessException(statusCode: 404) => l10n.bookingsCancelNotFound,
        ApiBusinessException(statusCode: 409) => l10n.bookingsCancelConflict,
        _ => error.toLocalizedMessage(l10n),
      };
      _showSnackBar(message);
      if (error is ApiBusinessException &&
          (error.statusCode == 404 || error.statusCode == 409)) {
        await _refresh();
      }
    }
  }

  void _showSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(l10n.profileBookings),
        centerTitle: false,
      ),
      body: _buildBody(context, l10n, auth),
    );
  }

  Widget _buildBody(
    BuildContext context,
    AppLocalizations l10n,
    AuthProvider auth,
  ) {
    if (!auth.isInitialized) {
      return _buildSkeleton(l10n);
    }
    if (!auth.isLoggedIn) {
      return _buildLoginGuide(context, l10n);
    }

    _future ??= BookingRepository.list();

    return FutureBuilder<List<BookingOrder>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return _buildSkeleton(l10n);
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          if (error is UnauthorizedException) {
            return _buildLoginGuide(context, l10n);
          }
          return ErrorState(
            title: l10n.bookingsLoadFailed,
            message: error is ApiException
                ? error.toLocalizedMessage(l10n)
                : l10n.errorUnknown,
            onRetry: _refresh,
          );
        }

        final orders = snapshot.data ?? const <BookingOrder>[];
        if (orders.isEmpty) {
          return _buildEmptyState(l10n);
        }

        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
            itemCount: orders.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) => _BookingCard(
              order: orders[index],
              l10n: l10n,
              onCancel:
                  orders[index].isPending ? () => _cancel(orders[index]) : null,
            ),
          ),
        );
      },
    );
  }

  /// 加载骨架：与订单卡片同宽同高，避免数据到达时跳版。
  Widget _buildSkeleton(AppLocalizations l10n) {
    return SkeletonArea(
      label: l10n.loading,
      child: ListView.separated(
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        itemCount: 3,
        separatorBuilder: (_, __) => const SizedBox(height: 12),
        itemBuilder: (_, __) => const _SkeletonBookingCard(),
      ),
    );
  }

  Widget _buildLoginGuide(BuildContext context, AppLocalizations l10n) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.lock_outline,
                size: 46,
                color: AppColors.ink3,
              ),
              const SizedBox(height: 14),
              Text(
                l10n.loginRequiredTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppColors.ink,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n.bookingsLoginBody,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.5,
                  color: AppColors.ink2,
                ),
              ),
              const SizedBox(height: 20),
              FilledButton(
                onPressed: () => context.pushNamed(
                  'login',
                  queryParameters: {'redirect': '/bookings'},
                ),
                child: Text(l10n.goLogin),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState(AppLocalizations l10n) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(28),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.receipt_long_outlined,
                size: 46,
                color: AppColors.ink3,
              ),
              const SizedBox(height: 14),
              Text(
                l10n.bookingsEmptyTitle,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppColors.ink,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                l10n.bookingsEmptyBody,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 13,
                  height: 1.5,
                  color: AppColors.ink2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 单条订单卡片。
class _BookingCard extends StatelessWidget {
  final BookingOrder order;
  final AppLocalizations l10n;

  /// 仅待确认订单传入取消回调。
  final VoidCallback? onCancel;

  const _BookingCard({
    required this.order,
    required this.l10n,
    this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    // 日期按当前语言格式化（应用启动时已初始化 intl 日期符号）。
    final dateFormat =
        DateFormat.yMMMd(AppLocalizations.of(context).localeName);
    final appointment = order.appointmentDate;
    final createdAt = order.createdAt;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  order.orderNo,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: AppColors.ink,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              _StatusChip(status: order.status, l10n: l10n),
            ],
          ),
          if (appointment != null) ...[
            const SizedBox(height: 10),
            _InfoRow(
              icon: Icons.event_outlined,
              text: '${l10n.bookingsAppointmentDate}: '
                  '${dateFormat.format(appointment)}',
            ),
          ],
          if (createdAt != null) ...[
            const SizedBox(height: 10),
            _InfoRow(
              icon: Icons.schedule_outlined,
              text: '${l10n.bookingsCreatedAt}: '
                  '${dateFormat.format(createdAt)}',
            ),
          ],
          const SizedBox(height: 10),
          _InfoRow(
            icon: Icons.payments_outlined,
            text: '${l10n.bookingTotal}: '
                '${order.currency} ${order.totalPrice.toStringAsFixed(0)}',
          ),
          if (onCancel != null) ...[
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: onCancel,
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.danger,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  minimumSize: const Size(0, 36),
                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
                child: Text(
                  l10n.bookingsCancel,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// 与订单卡片同尺寸的静态占位卡。
///
/// 卡高按"标题行 + 三条信息 + 取消按钮"估算，数据到达时版式基本不跳。
class _SkeletonBookingCard extends StatelessWidget {
  const _SkeletonBookingCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: SkeletonLine(widthFactor: 0.5, height: 15)),
              SizedBox(width: 8),
              SkeletonBox(width: 56, height: 21, radius: 999),
            ],
          ),
          SizedBox(height: 10),
          SkeletonLine(widthFactor: 0.62, height: 12),
          SizedBox(height: 10),
          SkeletonLine(widthFactor: 0.55, height: 12),
          SizedBox(height: 10),
          SkeletonLine(widthFactor: 0.4, height: 12),
          SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: SkeletonBox(width: 64, height: 22, radius: 6),
          ),
        ],
      ),
    );
  }
}

/// 图标 + 文案信息行，窄屏与大字号下自动换行。
class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _InfoRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 17, color: AppColors.ink2),
        const SizedBox(width: 7),
        Expanded(
          child: Text(
            text,
            style: const TextStyle(
              fontSize: 12.5,
              height: 1.25,
              color: AppColors.ink2,
            ),
          ),
        ),
      ],
    );
  }
}

/// 订单状态徽标。
class _StatusChip extends StatelessWidget {
  final String status;
  final AppLocalizations l10n;

  const _StatusChip({required this.status, required this.l10n});

  @override
  Widget build(BuildContext context) {
    final (label, color, background) = _resolve(status, l10n);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          height: 1.2,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  (String, Color, Color) _resolve(
    String rawStatus,
    AppLocalizations l10n,
  ) {
    switch (rawStatus.toLowerCase()) {
      case 'pending':
        return (
          l10n.bookingsStatusPending,
          const Color(0xFF92400E),
          const Color(0xFFFEF3C7),
        );
      case 'confirmed':
        return (
          l10n.bookingsStatusConfirmed,
          AppColors.primaryDark,
          AppColors.primaryBg,
        );
      case 'completed':
        return (
          l10n.bookingsStatusCompleted,
          const Color(0xFF475569),
          const Color(0xFFEEF2F6),
        );
      case 'cancelled':
      case 'canceled':
        return (
          l10n.bookingsStatusCancelled,
          const Color(0xFFB42318),
          const Color(0xFFFDECEC),
        );
      default:
        // 后端出现未知状态时用本地化兜底，避免直接把英文变量暴露给用户。
        return (
          l10n.bookingsStatusUnknown,
          const Color(0xFF475569),
          const Color(0xFFEEF2F6)
        );
    }
  }
}
