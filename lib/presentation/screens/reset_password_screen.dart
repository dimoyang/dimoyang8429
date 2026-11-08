import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:meditour_app/business/providers/auth_provider.dart';
import 'package:meditour_app/core/constants/colors.dart';
import 'package:meditour_app/core/network/api_exception.dart';
import 'package:meditour_app/core/utils/route_location.dart';
import 'package:meditour_app/l10n/app_localizations.dart';
import 'package:meditour_app/presentation/widgets/app_toast.dart';
import 'package:meditour_app/presentation/widgets/form_field.dart';
import 'package:provider/provider.dart';

/// 用邮件里的一次性令牌设置新密码。
///
/// 成功后会清空本地会话（后端已让所有旧令牌失效），并引导用新密码重新登录。
class ResetPasswordScreen extends StatefulWidget {
  final String? token;
  final String? redirect;

  const ResetPasswordScreen({super.key, this.token, this.redirect});

  @override
  State<ResetPasswordScreen> createState() => _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends State<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _tokenController;
  final _passwordController = TextEditingController();
  final _confirmController = TextEditingController();
  bool _submitting = false;

  String? get _safeRedirect {
    final redirect = widget.redirect;
    return (redirect != null && redirect.startsWith('/')) ? redirect : null;
  }

  @override
  void initState() {
    super.initState();
    _tokenController = TextEditingController(text: widget.token ?? '');
  }

  @override
  void dispose() {
    _tokenController.dispose();
    _passwordController.dispose();
    _confirmController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: AppColors.pageBg,
      appBar: AppBar(title: Text(l10n.resetPasswordTitle)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          children: [
            AppFormField(
              label: l10n.resetPasswordTokenLabel,
              controller: _tokenController,
              validator: (v) => (v == null || v.trim().isEmpty)
                  ? l10n.resetPasswordTokenError
                  : null,
            ),
            const SizedBox(height: 14),
            AppFormField(
              label: l10n.newPasswordLabel,
              controller: _passwordController,
              obscureText: true,
              validator: (v) =>
                  (v == null || v.length < 6) ? l10n.passwordError : null,
            ),
            const SizedBox(height: 14),
            AppFormField(
              label: l10n.passwordConfirmLabel,
              controller: _confirmController,
              obscureText: true,
              validator: (v) => (v == null || v != _passwordController.text)
                  ? l10n.passwordMismatch
                  : null,
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
                      l10n.resetPasswordButton,
                      style: const TextStyle(
                          fontSize: 16, fontWeight: FontWeight.w700),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _submit() async {
    final l10n = AppLocalizations.of(context);
    if (!_formKey.currentState!.validate()) {
      return;
    }
    setState(() => _submitting = true);
    try {
      await context.read<AuthProvider>().confirmPasswordReset(
            token: _tokenController.text.trim(),
            newPassword: _passwordController.text,
          );
      if (!mounted) {
        return;
      }
      await _showReLoginDialog(l10n.resetPasswordSuccess);
    } on ApiBusinessException catch (e) {
      if (!mounted) {
        return;
      }
      // 400 表示令牌无效/过期/已使用，需要与网络失败区分提示。
      _showError(
        e.statusCode == 400
            ? l10n.resetPasswordInvalidToken
            : e.toLocalizedMessage(l10n),
      );
    } on ApiException catch (e) {
      if (!mounted) {
        return;
      }
      _showError(e.toLocalizedMessage(l10n));
    } finally {
      if (mounted) {
        setState(() => _submitting = false);
      }
    }
  }

  void _showError(String message) {
    AppToast.error(context, message);
  }

  Future<void> _showReLoginDialog(String message) async {
    final l10n = AppLocalizations.of(context);
    await showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (dialogContext) => AlertDialog(
        content: Text(message),
        actions: [
          FilledButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              if (mounted) {
                context.go(loginLocation(redirect: _safeRedirect));
              }
            },
            child: Text(l10n.loginButton),
          ),
        ],
      ),
    );
  }
}
