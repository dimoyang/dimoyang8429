import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/utils/route_location.dart';
import 'package:meditour_app/core/utils/validators.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/form_field.dart';
import 'package:provider/provider.dart';

/// 忘记密码：请求重置邮件。
///
/// 后端对已注册与未注册邮箱返回同一响应，页面只能提示
/// "如果该邮箱已注册，我们会发送重置邮件"，不能暴露邮箱是否存在。
class ForgotPasswordScreen extends StatefulWidget {
  final String? redirect;

  const ForgotPasswordScreen({super.key, this.redirect});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  bool _submitting = false;
  bool _sent = false;

  /// 只接受站内路径，避免把任意 URL 带到登录页。
  String? get _safeRedirect {
    final redirect = widget.redirect;
    return (redirect != null && redirect.startsWith('/')) ? redirect : null;
  }

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.forgotPasswordTitle)),
      body: _sent ? _buildSent(l10n) : _buildForm(l10n),
    );
  }

  Widget _buildForm(AppLocalizations l10n) {
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        children: [
          Text(
            l10n.forgotPasswordIntro,
            style: const TextStyle(
              color: AppColors.ink2,
              fontSize: 13,
              height: 1.5,
            ),
          ),
          const SizedBox(height: 18),
          AppFormField(
            label: l10n.emailLabel,
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            validator: (v) =>
                Validators.isValidEmail(v) ? null : l10n.emailError,
          ),
          const SizedBox(height: 24),
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
                    l10n.forgotPasswordSend,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w700),
                  ),
          ),
          const SizedBox(height: 10),
          Center(
            child: TextButton(
              onPressed: _submitting ? null : _openReset,
              child: Text(
                l10n.forgotPasswordHaveToken,
                style: const TextStyle(
                  fontSize: 13.5,
                  color: AppColors.primaryDark,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSent(AppLocalizations l10n) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 32, 20, 28),
      children: [
        const Icon(
          Icons.mark_email_read_outlined,
          size: 52,
          color: AppColors.primary,
        ),
        const SizedBox(height: 16),
        // 结果页整体替换，读屏需要主动播报"邮件已发送"。
        Semantics(
          liveRegion: true,
          child: Text(
            l10n.forgotPasswordSentTitle,
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: AppColors.ink,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          l10n.forgotPasswordSentBody,
          textAlign: TextAlign.center,
          style: const TextStyle(
            color: AppColors.ink2,
            fontSize: 13,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 26),
        FilledButton(
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(999),
            ),
          ),
          onPressed: _openReset,
          child: Text(
            l10n.forgotPasswordHaveToken,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700),
          ),
        ),
        const SizedBox(height: 8),
        Center(
          child: TextButton(
            onPressed: () => context.go(loginLocation(redirect: _safeRedirect)),
            child: Text(
              l10n.loginButton,
              style: const TextStyle(
                fontSize: 13.5,
                color: AppColors.primaryDark,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context);
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() => _submitting = true);
    try {
      await context
          .read<AuthProvider>()
          .requestPasswordReset(_emailController.text.trim());
      if (!mounted) {
        return;
      }
      setState(() => _sent = true);
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toLocalizedMessage(l10n)),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _openReset() {
    final redirect = _safeRedirect;
    context.pushNamed(
      'resetPassword',
      queryParameters: {if (redirect != null) 'redirect': redirect},
    );
  }
}
