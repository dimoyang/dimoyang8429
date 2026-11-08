import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/utils/validators.dart';
import 'package:meditour_app/data/models/booking.dart';
import 'package:meditour_app/data/models/medical_service.dart';
import 'package:meditour_app/data/respositories/booking_repository.dart';
import 'package:meditour_app/data/respositories/service_repository.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/app_toast.dart';
import 'package:meditour_app/presentation/widgets/error_state.dart';
import 'package:meditour_app/presentation/widgets/form_field.dart';
import 'package:meditour_app/presentation/widgets/skeleton.dart';
import 'package:provider/provider.dart';

/// 预约页面
class BookingScreen extends StatefulWidget {
  final String serviceId;

  const BookingScreen({super.key, required this.serviceId});

  @override
  State<BookingScreen> createState() => _BookingScreenState();
}

class _BookingScreenState extends State<BookingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _noteController = TextEditingController();
  DateTime? _selectedDate;
  bool _needTranslator = false;
  bool _needAccommodation = false;
  bool _needPickup = false;
  bool _submitting = false;
  bool _submitted = false;
  BookingResult? _result;
  late Future<MedicalService?> _serviceFuture;

  @override
  void initState() {
    super.initState();
    _serviceFuture = ServiceRepository.getService(widget.serviceId);
  }

  void _reloadService() {
    setState(() {
      _serviceFuture = ServiceRepository.getService(widget.serviceId);
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return FutureBuilder<MedicalService?>(
      future: _serviceFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return _buildSkeleton(l10n);
        }
        if (snapshot.hasError) {
          final error = snapshot.error;
          final message = error is ApiException
              ? error.toLocalizedMessage(l10n)
              : l10n.errorUnknown;
          return ErrorScaffold(
            appBarTitle: l10n.btnBookConsult,
            title: l10n.medicalLoadFailed,
            message: message,
            onRetry: _reloadService,
          );
        }
        final service = snapshot.data;
        if (service == null) {
          return Scaffold(
            appBar: AppBar(title: Text(l10n.serviceNotFound)),
            body: Center(child: Text(l10n.serviceNotFound)),
          );
        }
        if (_submitted) {
          return _buildSuccess(context, l10n);
        }
        return _buildForm(context, l10n, service);
      },
    );
  }

  /// 表单加载骨架：字段高度与真实 AppFormField 一致，避免回填时跳版。
  Widget _buildSkeleton(AppLocalizations l10n) {
    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.btnBookConsult)),
      body: SkeletonArea(
        label: l10n.loading,
        child: ListView(
          physics: const NeverScrollableScrollPhysics(),
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: const [
            SkeletonBox(height: 70, radius: 14),
            SizedBox(height: 18),
            _SkeletonField(),
            SizedBox(height: 14),
            _SkeletonField(),
            SizedBox(height: 14),
            _SkeletonField(),
            SizedBox(height: 14),
            _SkeletonField(),
            SizedBox(height: 18),
            SkeletonLine(widthFactor: 0.24, height: 13),
            SizedBox(height: 6),
            SkeletonBox(height: 40, radius: 8),
            SizedBox(height: 6),
            SkeletonBox(height: 40, radius: 8),
            SizedBox(height: 6),
            SkeletonBox(height: 40, radius: 8),
            SizedBox(height: 18),
            _SkeletonField(height: 78),
            SizedBox(height: 22),
            SkeletonBox(height: 52, radius: 999),
          ],
        ),
      ),
    );
  }

  Widget _buildForm(
      BuildContext context, AppLocalizations l10n, MedicalService service) {
    final langCode = Localizations.localeOf(context).languageCode;

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(
        title: Text(service.getName(langCode)),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
          children: [
            _buildServiceSummary(service, langCode),
            const SizedBox(height: 18),
            AppFormField(
              label: l10n.formName,
              controller: _nameController,
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? l10n.formNameError : null,
            ),
            const SizedBox(height: 14),
            AppFormField(
              label: l10n.formPhone,
              controller: _phoneController,
              keyboardType: TextInputType.phone,
              validator: (v) =>
                  Validators.isValidPhone(v) ? null : l10n.formPhoneError,
            ),
            const SizedBox(height: 14),
            AppFormField(
              label: l10n.formEmail,
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              validator: (v) =>
                  Validators.isValidEmail(v) ? null : l10n.formEmailError,
            ),
            const SizedBox(height: 14),
            _buildDateField(context, l10n),
            const SizedBox(height: 18),
            Text(
              l10n.extrasTitle,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            _buildExtraCheckbox(
              value: _needTranslator,
              label: l10n.needTranslator,
              onChanged: (v) => setState(() => _needTranslator = v ?? false),
            ),
            _buildExtraCheckbox(
              value: _needAccommodation,
              label: l10n.needAccommodation,
              onChanged: (v) => setState(() => _needAccommodation = v ?? false),
            ),
            _buildExtraCheckbox(
              value: _needPickup,
              label: l10n.needPickup,
              onChanged: (v) => setState(() => _needPickup = v ?? false),
            ),
            const SizedBox(height: 8),
            AppFormField(
              label: l10n.formNote,
              controller: _noteController,
              hint: l10n.formNoteHint,
              maxLines: 3,
            ),
            const SizedBox(height: 22),
            FilledButton(
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(
                      l10n.btnSubmit,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700),
                    ),
            ),
            const SizedBox(height: 14),
            Text(
              l10n.bookingNote,
              style: const TextStyle(
                  fontSize: 11.5, color: AppColors.ink3, height: 1.6),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildExtraCheckbox({
    required bool value,
    required String label,
    required ValueChanged<bool?> onChanged,
  }) {
    return CheckboxListTile(
      value: value,
      onChanged: onChanged,
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: EdgeInsets.zero,
      dense: true,
      activeColor: AppColors.primary,
      title: Text(
        label,
        style: const TextStyle(fontSize: 13.5, color: AppColors.ink),
      ),
    );
  }

  Widget _buildServiceSummary(MedicalService service, String langCode) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.primaryBg,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Center(
              child: ExcludeSemantics(
                child: Text('🏥', style: TextStyle(fontSize: 20)),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  service.getName(langCode),
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primaryDark,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  service.priceFrom,
                  style: const TextStyle(fontSize: 12, color: AppColors.ink3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDateField(BuildContext context, AppLocalizations l10n) {
    return FormField<DateTime>(
      initialValue: _selectedDate,
      autovalidateMode: AutovalidateMode.onUserInteraction,
      validator: (_) => _selectedDate == null ? l10n.formDateError : null,
      builder: (field) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.formDate,
                style:
                    const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Semantics(
              button: true,
              label: l10n.formDate,
              child: InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: () async {
                  await _pickDate(context);
                  field.didChange(_selectedDate);
                },
                child: Ink(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: field.hasError ? AppColors.danger : AppColors.line,
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.calendar_today_outlined,
                          size: 16, color: AppColors.ink3),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _selectedDate == null
                              ? l10n.formDateHint
                              : '${_selectedDate!.year}-${_selectedDate!.month.toString().padLeft(2, '0')}-${_selectedDate!.day.toString().padLeft(2, '0')}',
                          style: TextStyle(
                            fontSize: 14,
                            color: _selectedDate == null
                                ? AppColors.ink3
                                : AppColors.ink,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            if (field.hasError)
              Padding(
                padding: const EdgeInsets.only(top: 6, left: 12),
                child: Text(
                  field.errorText!,
                  style: const TextStyle(fontSize: 12, color: AppColors.danger),
                ),
              ),
          ],
        );
      },
    );
  }

  Future<void> _pickDate(BuildContext context) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now().add(const Duration(days: 7)),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked != null) {
      setState(() => _selectedDate = picked);
    }
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context);
    if (!_formKey.currentState!.validate()) {
      return;
    }
    // 日期由 FormField 内联校验，验证通过后必定有值。
    final date = _selectedDate!;

    final auth = context.read<AuthProvider>();
    if (!auth.isLoggedIn) {
      _showLoginRequiredDialog(l10n);
      return;
    }

    setState(() => _submitting = true);
    try {
      final result = await BookingRepository.create(
        serviceId: widget.serviceId,
        date: date,
        contactName: _nameController.text.trim(),
        contactPhone: _phoneController.text.trim(),
        contactEmail: _emailController.text.trim(),
        notes: _noteController.text.trim(),
        needTranslator: _needTranslator,
        needAccommodation: _needAccommodation,
        needPickup: _needPickup,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _result = result;
        _submitted = true;
      });
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      if (e is ApiBusinessException && e.statusCode == 404) {
        AppToast.error(context, l10n.bookingPackageNotFound);
      } else {
        AppToast.error(context, e.toLocalizedMessage(l10n));
      }
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _showLoginRequiredDialog(AppLocalizations l10n) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: Text(l10n.loginRequiredTitle),
          content: Text(l10n.loginRequiredBody),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primaryDark,
              ),
              onPressed: () {
                Navigator.of(dialogContext).pop();
                context.pushNamed('login');
              },
              child: Text(l10n.goLogin),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSuccess(BuildContext context, AppLocalizations l10n) {
    final result = _result;
    return Scaffold(
      backgroundColor: AppColors.pageBg,
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            return SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
              child: ConstrainedBox(
                constraints:
                    BoxConstraints(minHeight: constraints.maxHeight - 48),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      width: 80,
                      height: 80,
                      decoration: const BoxDecoration(
                        color: AppColors.primary,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.check,
                          color: Colors.white, size: 40),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      l10n.bookingSuccess,
                      style: const TextStyle(
                          fontSize: 20, fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      l10n.bookingSuccessDesc,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                          fontSize: 14, color: AppColors.ink2, height: 1.7),
                    ),
                    const SizedBox(height: 20),
                    if (result != null) ...[
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 20, vertical: 10),
                        decoration: BoxDecoration(
                          color: AppColors.primaryBg,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Column(
                          children: [
                            Text(
                              '${l10n.bookingNo} ${result.orderNo}',
                              style: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                                color: AppColors.primaryDark,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${l10n.bookingTotal} '
                              '${result.currency} ${result.totalPrice.toStringAsFixed(0)}',
                              style: const TextStyle(
                                fontSize: 12.5,
                                color: AppColors.ink2,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 32),
                    FilledButton(
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(52),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(999),
                        ),
                      ),
                      onPressed: () => context.go('/'),
                      child: Text(
                        l10n.btnBackHome,
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

/// 表单字段占位：标签行 + 输入框。
class _SkeletonField extends StatelessWidget {
  final double height;

  const _SkeletonField({this.height = 46});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SkeletonLine(widthFactor: 0.22, height: 12),
        const SizedBox(height: 6),
        SkeletonBox(height: height, radius: 12),
      ],
    );
  }
}
