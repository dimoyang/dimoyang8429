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
      return const Center(child: CircularProgressIndicator());
    }
    if (!auth.isLoggedIn) {
      return _buildLoginGuide(context, l10n);
    }

    _future ??= BookingRepository.list();

    return FutureBuilder<List<BookingOrder>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
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
            ),
          ),
        );
      },
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

  const _BookingCard({required this.order, required this.l10n});

  @override
  Widget build(BuildContext context) {
    final appointment = order.appointmentDate;

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
                  '${DateFormat.yMMMd(l10n.localeName).format(appointment)}',
            ),
          ],
          const SizedBox(height: 10),
          _InfoRow(
            icon: Icons.payments_outlined,
            text: '${l10n.bookingTotal}: '
                '${order.currency} ${order.totalPrice.toStringAsFixed(0)}',
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
          AppColors.ink2,
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
        // 未知状态直接展示后端原值，避免吞掉信息。
        return (rawStatus, AppColors.ink2, const Color(0xFFEEF2F6));
    }
  }
}
